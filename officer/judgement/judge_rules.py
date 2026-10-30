"""Component 4, judgement checks: one forced model call per judgement rule.

Some rules need reading, not checking: is the will witnessed, is the applicant the named
executor, is a codicil missing. Each applicable judgement rule gets one Haiku call that must
answer through the record_judgement tool. Evidence is wrapped in <case_documents> tags,
and an unclear answer counts as a fail.

`run_all` joins these findings to the deterministic ones from component 3.
"""

from officer import llm, prompts
from officer.checks.rules import judgement_rules_for, run_deterministic
from officer.models import Finding


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
