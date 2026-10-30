# Component 2: Scope guard

**The step in the officer's job:** Is this case mine to handle?

Refuses any case whose state is not in `config.IN_SCOPE_STATES` (issued, stopped), before any model call. A prompt can be argued with; this cannot. It is the only source of `refuse_out_of_scope`.

## Contract

| Call | Does |
|---|---|
| `guard.in_scope(case) -> bool` | true if the case may be processed |
| `guard.refusal(case_id, state) -> Diagnosis` | the refusal, with confidence high |

- **Depends on:** `officer.models`, `config`
- **Used by:** `officer.decision` (diagnoser and agent), first thing they do
- **Tested by:** `tests/test_scope.py`, plus the refusal tests in `tests/test_diagnose.py` and `tests/test_agent.py`

## Building it alone

Pure functions, no model. Changing the in-scope states is a one-line config change, and the tests prove no model call happens for a refused case.
