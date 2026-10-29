"""The tools the agent can call.

READ tools return data. WRITE tools (added in M6) never run directly: they only
become proposals for a human to approve. FINAL is `submit_diagnosis`, which ends the run.

`TOOLS` is the registry. Each entry holds the function, its kind, a description
and its input schema. `schemas()` turns the registry into the list the API expects.
"""

import config
from officer import rules, store

# The schema for submit_diagnosis. It is also used by the single-call diagnoser, so it lives here.
# "refuse_out_of_scope" is left out on purpose: only the code can produce a refusal.
SUBMIT_DIAGNOSIS_TOOL = {
    "name": "submit_diagnosis",
    "description": "Record the final diagnosis for this probate case.",
    "input_schema": {
        "type": "object",
        "properties": {
            "summary": {"type": "string", "description": "2 to 3 plain-English sentences"},
            "stop_reasons": {"type": "array", "items": {"type": "string"}},
            "rules_cited": {"type": "array", "items": {"type": "string"}},
            "next_action": {"type": "string", "enum": ["stop_case", "route_to_examiner", "escalate"]},
            "confidence": {"type": "string", "enum": ["low", "medium", "high"]},
        },
        "required": ["summary", "stop_reasons", "rules_cited", "next_action", "confidence"],
    },
}


def get_case(case_id):
    try:
        return store.load_case(case_id).model_dump(mode="json")
    except (FileNotFoundError, ValueError) as error:
        return {"error": str(error)}


def run_rule_checks(case_id):
    """Failed rules only, deterministic and judgement. Passing rules are not returned."""
    try:
        case = store.load_case(case_id)
    except (FileNotFoundError, ValueError) as error:
        return {"error": str(error)}
    return [finding.model_dump() for finding in rules.run_all(case) if not finding.passed]


def lookup_rule(rule_id):
    for rule in rules.load_rules():
        if rule["id"] == rule_id:
            return rule
    return {"error": f"no rule {rule_id}"}


def get_template(template_id):
    # Templates arrive in M6. Until then, every lookup reports the template as missing.
    path = config.TEMPLATES_DIR / f"{template_id}.txt"
    if not path.exists():
        return {"error": f"no template {template_id}"}
    return {"template_id": template_id, "text": path.read_text(encoding="utf-8")}


TOOLS = {
    "get_case": {
        "fn": get_case,
        "kind": "READ",
        "description": "Fetch the full case record.",
        "schema": {"type": "object", "properties": {"case_id": {"type": "string"}}, "required": ["case_id"]},
    },
    "run_rule_checks": {
        "fn": run_rule_checks,
        "kind": "READ",
        "description": "Run all rule checks on a case. Returns failed rules only.",
        "schema": {"type": "object", "properties": {"case_id": {"type": "string"}}, "required": ["case_id"]},
    },
    "lookup_rule": {
        "fn": lookup_rule,
        "kind": "READ",
        "description": "Get a rule's full details.",
        "schema": {"type": "object", "properties": {"rule_id": {"type": "string"}}, "required": ["rule_id"]},
    },
    "get_template": {
        "fn": get_template,
        "kind": "READ",
        "description": "Get a letter template.",
        "schema": {"type": "object", "properties": {"template_id": {"type": "string"}}, "required": ["template_id"]},
    },
    "submit_diagnosis": {
        "fn": None,
        "kind": "FINAL",
        "description": SUBMIT_DIAGNOSIS_TOOL["description"],
        "schema": SUBMIT_DIAGNOSIS_TOOL["input_schema"],
    },
}


def schemas(include_write):
    """The tool definitions to send to the API. WRITE tools are left out unless `include_write` is set."""
    result = []
    for name, spec in TOOLS.items():
        if spec["kind"] == "WRITE" and not include_write:
            continue
        result.append({"name": name, "description": spec["description"], "input_schema": spec["schema"]})
    return result


def execute(name, args, gate=None):
    """Run one tool. Errors come back as {"error": ...}, never as an exception."""
    if name not in TOOLS:
        return {"error": f"unknown tool {name}"}
    spec = TOOLS[name]
    if spec["kind"] == "FINAL":
        return {"error": "submit_diagnosis is handled by the agent loop, not executed here"}
    if spec["kind"] == "WRITE":
        # Writes are never run here. They become proposals that a human approves in the gate (M6).
        if gate is None:
            return {"error": f"{name} needs an approval gate, which this run does not have"}
        return gate.propose(name, args)
    try:
        return spec["fn"](**args)
    except Exception as error:  # a bad argument from the model must not crash the run
        return {"error": str(error)}
