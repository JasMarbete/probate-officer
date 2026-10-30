# Component 4: Judgement checks

**The step in the officer's job:** Read the will: is it witnessed, is the applicant the executor, is a codicil missing, do the names match?

Gives each applicable judgement rule one model call that must answer through the `record_judgement` tool. The evidence is wrapped in `<case_documents>` tags and is never treated as instructions. Only an explicit `true` passes; an unclear answer fails.

## Contract

| Call | Does |
|---|---|
| `judge_rules.run_judgement(case) -> list[Finding]` | one finding per judgement rule, one model call each |
| `judge_rules.run_all(case) -> list[Finding]` | deterministic findings (component 3) then judgement findings |

- **Depends on:** `officer.checks`, `officer.llm`, `officer.prompts`, `officer.models`
- **Used by:** `officer.decision` (the `run_rule_checks` tool), `evals/component.py`
- **Tested by:** `tests/test_judgement.py` (fake model); live: `python -m evals.run_evals --component --split dev`

## Building it alone

The component eval scores each judgement rule on its own, so a change here is measured without the agent in the way. It has scored 24 of 24 per rule on the test split.
