"""Component 2, scope guard: decides in code whether a case may reach the model at all.

Only cases in config.IN_SCOPE_STATES (issued, stopped) are processed. Anything else is
refused here, before any model call, so no prompt can talk the system past it. Both the
single-call diagnoser and the agent call this first.
"""

import config
from officer.models import Diagnosis


def in_scope(case):
    """True if the case's state is one this system may process."""
    return case.state in config.IN_SCOPE_STATES


def refusal(case_id, state):
    """The diagnosis for an out-of-scope case. Only code produces refuse_out_of_scope."""
    return Diagnosis(
        case_id=case_id,
        summary=f"This case is in state '{state}', which is outside the scope of this tool. It was refused without a model call.",
        stop_reasons=[],
        rules_cited=[],
        next_action="refuse_out_of_scope",
        confidence="high",
    )
