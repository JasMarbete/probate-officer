"""The read-only agent loop: the model calls tools until it submits a diagnosis.

The loop runs the scope guard first, then asks the model for a turn at a time.
Each tool call is run and logged, and its result goes back to the model. The loop
ends when the model calls submit_diagnosis, or when it hits the turn cap. Every
step is written to the audit trail under one run_id.
"""

import json
import secrets

from pydantic import ValidationError

import config
from officer import audit, llm, prompts, store, tools
from officer.gate import Gate
from officer.models import Diagnosis

NUDGE = "Use the tools. Finish by calling submit_diagnosis."


def _escalation(case_id, reason):
    # The safe fallback for any run that does not finish cleanly.
    return Diagnosis(
        case_id=case_id,
        summary=f"The agent did not finish this case, so a person should review it. Reason: {reason}",
        stop_reasons=[],
        rules_cited=[],
        next_action="escalate",
        confidence="low",
    )


def _submit(block, case_id):
    """Validate the submit_diagnosis input. Returns (diagnosis, None) or (None, problem)."""
    try:
        diagnosis = Diagnosis.model_validate({**block.input, "case_id": case_id})
    except (ValidationError, TypeError) as error:
        return None, f"submit_diagnosis did not validate: {error.__class__.__name__}. Fix it and call submit_diagnosis again."
    if diagnosis.next_action == "refuse_out_of_scope":
        return None, "Only the code may refuse a case. Choose stop_case, route_to_examiner or escalate."
    return diagnosis, None


def run_case(case_id, allow_write=False, llm_only=False):
    """Run the agent on one case. Returns (diagnosis, gate). The gate is None when writes are not allowed.

    `llm_only` is the ablation: no run_rule_checks tool, and the rules YAML is pasted into the prompt,
    so the model must apply the rules itself.
    """
    run_id = secrets.token_hex(4)
    audit.log(run_id, case_id, "run_start")
    gate = Gate(case_id, run_id) if allow_write else None

    # Scope guard: runs before the model is called at all.
    case = store.load_case(case_id)
    if case.state not in config.IN_SCOPE_STATES:
        audit.log(run_id, case_id, "refused", state=case.state)
        return Diagnosis(
            case_id=case_id,
            summary=f"This case is in state '{case.state}', which is outside the scope of this tool. It was refused without a model call.",
            stop_reasons=[],
            rules_cited=[],
            next_action="refuse_out_of_scope",
            confidence="high",
        ), None

    offered = [s for s in tools.schemas(allow_write) if not (llm_only and s["name"] == "run_rule_checks")]
    intro = f"Process case {case_id}."
    if llm_only:
        intro += ("\n<rules>\n" + config.RULES_PATH.read_text(encoding="utf-8") + "\n</rules>\n"
                  "No rule-check tool is available. Apply these rules yourself.")
    messages = [{"role": "user", "content": intro}]
    nudged = False
    for _ in range(config.MAX_TURNS):
        response = llm.call(prompts.AGENT_SYSTEM, messages, tools=offered)
        audit.log(
            run_id, case_id, "model_turn",
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            stop_reason=response.stop_reason,
        )
        messages.append({"role": "assistant", "content": response.content})

        tool_uses = [block for block in response.content if block.type == "tool_use"]
        if not tool_uses:
            # The model answered in text. Nudge it once. A second text-only turn ends the run.
            if nudged:
                audit.log(run_id, case_id, "error", reason="model stopped without calling a tool twice")
                return _escalation(case_id, "the model stopped without calling a tool."), gate
            nudged = True
            messages.append({"role": "user", "content": NUDGE})
            continue

        results = []
        for block in tool_uses:
            if block.name == "submit_diagnosis":
                diagnosis, problem = _submit(block, case_id)
                if diagnosis:
                    audit.log(run_id, case_id, "diagnosis", **diagnosis.model_dump(exclude={"case_id"}))
                    return diagnosis, gate
                # Send the problem back to the model as an error, so it can try again.
                results.append({"type": "tool_result", "tool_use_id": block.id, "content": problem, "is_error": True})
                continue
            output = tools.execute(block.name, block.input, gate)
            audit.log(run_id, case_id, "tool_call", name=block.name, args=block.input, output=output)
            results.append({"type": "tool_result", "tool_use_id": block.id, "content": json.dumps(output, default=str)})
        messages.append({"role": "user", "content": results})

    audit.log(run_id, case_id, "max_turns", limit=config.MAX_TURNS)
    return _escalation(case_id, f"the turn limit of {config.MAX_TURNS} was reached."), gate
