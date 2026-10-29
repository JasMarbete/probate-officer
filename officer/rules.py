"""The rules engine: loads rules from data/rules.yaml and runs the deterministic checks.

Deterministic rules are plain Python checks, so no model is needed for them.
Judgement rules are only listed here. A model reads them in later milestones.
Missing fields and missing documents count as a fail, never a crash.
"""

import operator
from datetime import date

import yaml

import config
from officer import llm, prompts
from officer.models import Case, Finding

# Maps the comparison operators written in rules.yaml to Python functions.
OPS = {"<": operator.lt, "<=": operator.le, ">": operator.gt, ">=": operator.ge}


def load_rules(path=None):
    """Read the rules file. The default is read at call time so tests can point elsewhere."""
    path = path or config.RULES_PATH
    with open(path, encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def get_path(data, dotted):
    """Follow a dotted path such as 'applicant.address_given'. Returns None if any part is missing."""
    current = data
    for part in dotted.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def get_doc(case_dict, doc_type):
    """Return the first document of this type, or None."""
    for doc in case_dict.get("documents", []):
        if doc.get("type") == doc_type:
            return doc
    return None


def _is_number(value):
    # bool is a subclass of int in Python, so exclude it on purpose.
    return isinstance(value, (int, float)) and not isinstance(value, bool)


# Each check takes the case as a dict plus its arguments from rules.yaml, and returns True or False.

def check_field_present(case, field):
    return bool(get_path(case, field))


def check_field_equals(case, field, value):
    # Read the value once. A missing field is None, so it must not match a None target by accident.
    actual = get_path(case, field)
    return actual is not None and actual == value


def check_field_in(case, field, values):
    return get_path(case, field) in values


def check_doc_received(case, doc_type):
    doc = get_doc(case, doc_type)
    return doc is not None and doc.get("received") is True


def check_doc_field_equals(case, doc_type, field, value):
    doc = get_doc(case, doc_type)
    return doc is not None and get_path(doc, field) == value


def check_number_compare(case, field, op, value):
    left = get_path(case, field)
    return _is_number(left) and OPS[op](left, value)


def check_fields_compare(case, left, op, right):
    a = get_path(case, left)
    b = get_path(case, right)
    return _is_number(a) and _is_number(b) and OPS[op](a, b)


def check_date_not_future(case, field):
    value = get_path(case, field)
    if not isinstance(value, str):
        return False
    try:
        return date.fromisoformat(value) <= date.today()
    except ValueError:
        return False


# The registry: rules.yaml names a check, and this dict maps the name to its function.
CHECKS = {
    "field_present": check_field_present,
    "field_equals": check_field_equals,
    "field_in": check_field_in,
    "doc_received": check_doc_received,
    "doc_field_equals": check_doc_field_equals,
    "number_compare": check_number_compare,
    "fields_compare": check_fields_compare,
    "date_not_future": check_date_not_future,
}


def applicable(rule, case):
    """True if the rule applies to this case's application type. A rule with no applies_to applies to all."""
    applies_to = rule.get("applies_to")
    return applies_to is None or case.application_type in applies_to


def _finding(rule, case_dict):
    passed = CHECKS[rule["check"]](case_dict, **rule["args"])
    if passed:
        return Finding(rule_id=rule["id"], passed=True, reason=f"{rule['name']}: passed")
    # A failed rule carries the stop reason and action from its on_fail block.
    on_fail = rule["on_fail"]
    return Finding(
        rule_id=rule["id"],
        passed=False,
        stop_reason=on_fail["stop_reason"],
        action=on_fail["action"],
        reason=f"{rule['name']}: failed check {rule['check']}",
    )


def run_deterministic(case):
    """Run every applicable deterministic rule on one case."""
    case_dict = case.model_dump(mode="json")
    return [
        _finding(rule, case_dict)
        for rule in load_rules()
        if rule["kind"] == "deterministic" and applicable(rule, case)
    ]


def judgement_rules_for(case):
    """The applicable judgement rules. A model checks these in a later milestone."""
    return [
        rule
        for rule in load_rules()
        if rule["kind"] == "judgement" and applicable(rule, case)
    ]


# Schema for the judge's answer. It is the only tool a judgement call may use (spec Section 8).
RECORD_JUDGEMENT_TOOL = {
    "name": "record_judgement",
    "description": "Record whether the rule passes, with a one-sentence reason.",
    "input_schema": {
        "type": "object",
        "properties": {
            "passed": {"type": "boolean"},
            "reason": {"type": "string"},
        },
        "required": ["passed", "reason"],
    },
}


def _case_documents(case):
    # Document text and notes, wrapped in one tag. The judge prompt says this is evidence only.
    # The applicant and deceased are structured fields, not document text, so they are added here too.
    parts = [f"[case] Applicant: {case.applicant.name} ({case.applicant.role}). Deceased: {case.deceased.name}."]
    parts += [f"[{doc.type}] {doc.text}" for doc in case.documents if doc.text]
    parts += [f"[note] {note}" for note in case.notes]
    return "\n".join(parts)


def _judge(rule, case):
    """One model call for one judgement rule. Returns (passed, reason). Unclear answers count as a fail."""
    response = llm.call(
        prompts.JUDGE_RULE_SYSTEM,
        messages=[{"role": "user", "content": f"<case_documents>{_case_documents(case)}</case_documents>\n<rule>{rule['question']}</rule>"}],
        tools=[RECORD_JUDGEMENT_TOOL],
        tool_choice={"type": "tool", "name": "record_judgement"},
    )
    for block in response.content:
        if getattr(block, "type", None) == "tool_use" and block.name == "record_judgement":
            # Only an explicit True passes. Anything else is a fail, as the judge prompt requires.
            return block.input.get("passed") is True, str(block.input.get("reason", ""))
    return False, "the judge did not return a verdict"


def run_judgement(case):
    """One judgement finding per applicable judgement rule. Each costs one model call."""
    findings = []
    for rule in judgement_rules_for(case):
        passed, reason = _judge(rule, case)
        if passed:
            findings.append(Finding(rule_id=rule["id"], passed=True, reason=reason))
        else:
            on_fail = rule["on_fail"]
            findings.append(Finding(
                rule_id=rule["id"],
                passed=False,
                stop_reason=on_fail["stop_reason"],
                action=on_fail["action"],
                reason=reason,
            ))
    return findings


def run_all(case):
    """Deterministic findings followed by judgement findings."""
    return run_deterministic(case) + run_judgement(case)
