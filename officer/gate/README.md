# Component 6: Approval gate

**The step in the officer's job:** Write the letter, add the note, change the status, but only with a person's say-so.

Every write tool call becomes a proposal. Nothing changes until `decide(id, approved=True)`. Then the action is checked against `ALLOWED_TRANSITIONS` and applied. Each proposal can be decided once, and every decision is written to the audit trail and to `data/preferences.jsonl`.

## Contract

| Call | Does |
|---|---|
| `Gate(case_id, run_id).propose(action, args) -> dict` | queue a proposal; changes nothing |
| `Gate.decide(proposal_id, approved, note='')` | approve (and apply) or reject; logs the decision |
| `ALLOWED_TRANSITIONS` | issued or stopped -> stopped, ready_for_examiner, escalated |

- **Depends on:** `officer.intake`, `officer.audit`, `config`
- **Used by:** `officer.decision` (agent with writes), `cli.py`, `app.py`
- **Tested by:** `tests/test_gate.py`

## Building it alone

No model. The tests prove a proposal changes nothing, rejection changes nothing, an illegal move raises, and a preference line is written.
