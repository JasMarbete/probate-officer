# Component 7: Audit trail

**The step in the officer's job:** Record what happened, so every decision can be explained.

Appends one JSON line per event to `logs/trace.jsonl`: run start, refusal, model turn (with token counts), tool call (with arguments and output), proposal, human decision, diagnosis, turn cap, error. Every event carries the run's `run_id`.

## Contract

| Call | Does |
|---|---|
| `log(run_id, case_id, event, **data)` | append one event |
| `read_run(run_id) -> list[dict]` | every event for one run, in order |
| `last_run_id() -> str | None` | the most recent run |

- **Depends on:** `config`
- **Used by:** `officer.decision`, `officer.gate`, `scripts/watch_trace.py`, the evals (completion and tool-error rates come from the trail)
- **Tested by:** `tests/test_audit.py`, plus the trace tests in `tests/test_agent.py`

## Building it alone

No model. `python scripts/watch_trace.py` prints the trail live in plain English.
