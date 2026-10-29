"""The diagnoser: decides what should happen next for one probate case.

Two versions live here:
- `diagnose` makes one Haiku call. Its output is the thing the evals score.
- `rules_only` makes no call. It is the baseline the evals compare against.

Both run the scope guard first. Out-of-scope cases are refused in code, before
any model call, so the model never sees them.
"""

import json

from pydantic import ValidationError

import config
from officer import llm, prompts, rules, store
from officer.models import Diagnosis

# The tool the model must call to answer. Its schema is BUILD_SPEC.md Section 8.
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


def _refusal(case_id, state):
    return Diagnosis(
        case_id=case_id,
        summary=f"This case is in state '{state}', which is outside the scope of this tool. It was refused without a model call.",
        stop_reasons=[],
        rules_cited=[],
        next_action="refuse_out_of_scope",
        confidence="high",
    )


def _escalation(case_id, reason):
    # The safe fallback. Any problem with the model's output sends the case to a person.
    return Diagnosis(
        case_id=case_id,
        summary=f"The diagnoser could not produce a valid diagnosis, so a person should review this case. Reason: {reason}",
        stop_reasons=[],
        rules_cited=[],
        next_action="escalate",
        confidence="low",
    )


def _user_message(case, failed, judgement):
    # Case text is wrapped in tags, and the system prompt says it is evidence only.
    return (
        f"<case>{json.dumps(case.model_dump(mode='json'), indent=2)}</case>\n"
        f"<failed_rules>{json.dumps([f.model_dump() for f in failed])}</failed_rules>\n"
        f"<judgement_rules>{json.dumps(judgement)}</judgement_rules>"
    )


def _parse(response, case_id):
    """Turn the model's tool call into a Diagnosis. Any problem becomes a safe escalation."""
    for block in response.content:
        if getattr(block, "type", None) == "tool_use" and block.name == "submit_diagnosis":
            try:
                diagnosis = Diagnosis.model_validate({**block.input, "case_id": case_id})
            except (ValidationError, TypeError) as error:
                return _escalation(case_id, f"the model's output did not validate ({error.__class__.__name__}).")
            # The schema hides this value, but the code checks it too in case the model sends it anyway.
            if diagnosis.next_action == "refuse_out_of_scope":
                return _escalation(case_id, "the model tried to refuse a case, which only the code may do.")
            return diagnosis
    return _escalation(case_id, "the model did not call submit_diagnosis.")


def diagnose(case_id):
    """Diagnose one case with one Haiku call. Out-of-scope cases get no call at all."""
    case = store.load_case(case_id)
    # Scope guard: runs before any model call.
    if case.state not in config.IN_SCOPE_STATES:
        return _refusal(case_id, case.state)

    failed = [finding for finding in rules.run_deterministic(case) if not finding.passed]
    judgement = rules.judgement_rules_for(case)
    response = llm.call(
        prompts.DIAGNOSE_SYSTEM,
        messages=[{"role": "user", "content": _user_message(case, failed, judgement)}],
        tools=[SUBMIT_DIAGNOSIS_TOOL],
        # Force the model to answer through the tool, so the output is always structured.
        tool_choice={"type": "tool", "name": "submit_diagnosis"},
    )
    return _parse(response, case_id)


def rules_only(case_id):
    """The baseline: the same decision from the deterministic rules alone, with no model call."""
    case = store.load_case(case_id)
    if case.state not in config.IN_SCOPE_STATES:
        return _refusal(case_id, case.state)

    failed = [finding for finding in rules.run_deterministic(case) if not finding.passed]
    stop_reasons = list(dict.fromkeys(f.stop_reason for f in failed))
    rules_cited = [f.rule_id for f in failed]

    if not failed:
        next_action = "route_to_examiner"
        summary = "No deterministic rule failed. Judgement rules were not checked in this baseline."
    elif any(f.action == "escalate" for f in failed):
        next_action = "escalate"
        summary = "A failed rule requires escalation to a person."
    else:
        next_action = "stop_case"
        summary = "One or more deterministic rules failed, so the applicant must supply the missing items."

    return Diagnosis(
        case_id=case_id,
        summary=summary,
        stop_reasons=stop_reasons,
        rules_cited=rules_cited,
        next_action=next_action,
        confidence="medium",
    )
