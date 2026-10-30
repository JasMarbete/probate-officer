# Component 5: Decision

**The step in the officer's job:** Stop the case, route it to an examiner, or escalate it?

Two ways to decide. `diagnose` makes one forced model call with the failed rules and the judgement rules. `agent.run_case` runs a tool-using loop (get_case, run_rule_checks, lookup_rule, get_template, and the write tools as proposals) with a turn cap, one nudge, and validation errors fed back. Both run the scope guard first and end in a validated `Diagnosis`; anything malformed becomes a safe escalation.

## Contract

| Call | Does |
|---|---|
| `agent.run_case(case_id, allow_write=False, llm_only=False) -> (Diagnosis, Gate | None)` | the agent loop |
| `diagnose.diagnose(case_id) -> Diagnosis` | one model call |
| `diagnose.rules_only(case_id) -> Diagnosis` | no model; the baseline |
| `tools.TOOLS, tools.schemas(include_write), tools.execute(name, args, gate)` | the tool registry; WRITE tools only reach `gate.propose` |

- **Depends on:** all of the above, plus `officer.gate`, `officer.audit`, `officer.llm`, `officer.prompts`
- **Used by:** `cli.py`, `app.py`, the evals and the showcase
- **Tested by:** `tests/test_agent.py`, `tests/test_diagnose.py`, `tests/test_tools.py`

## Building it alone

The fake model in `tests/conftest.py` scripts every turn, so each loop branch (normal finish, nudge, turn cap, validation error, refusal) is tested without the API.
