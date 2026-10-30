# PROGRESS

Milestone log for ProbateOfficer. Each milestone gets a dated entry.

## Done

### M0: Scaffold (2026-10-29)
- Created the [v1] folder layout from BUILD_SPEC.md Section 4: `officer/`, `scripts/`, `tests/`, `evals/results/`, `data/shelf/`.
- Added `requirements.txt` (pinned: anthropic, pydantic, pyyaml, python-dotenv, pytest), `.gitignore`, `.env.example` and `config.py`.
- Added empty package file `officer/__init__.py`.
- Added `scripts/ping.py`, which sends "Reply with OK" to Haiku and prints the reply and usage.
- Added this file, a `WALKTHROUGH.md` skeleton and a placeholder `README.md`.

**Check output summary:**
- `pip install -r requirements.txt`: succeeded in `.venv` (Python 3.14.3).
- `pytest`: runs, collects 0 tests, exit code 5 (pytest's "no tests collected"). The spec allows 0 tests for M0.
- `python scripts/ping.py`: passed against the live API on 2026-10-29. Output: `Reply: OK`, `Model: claude-haiku-5-5`, 14 input tokens, 4 output tokens. Without a key, it exits 1 with "No ANTHROPIC_API_KEY found", as designed.
- `config.py` and `officer` import cleanly.

### M1: Models and store (2026-10-29)
- Added `officer/models.py`: `Document`, `Applicant`, `Deceased`, `Estate`, `Case`, `Finding`, `Diagnosis`, and the `State` and `NextAction` literal types, as in spec Section 5.
- Added `officer/store.py`: `load_case`, `save_case`, `list_cases` and `reset_case`.
- Added three hand-written cases in `data/cases/`: `PRB-0001` (clean), `PRB-0002` (death certificate missing), `PRB-0003` (copy will, not the original). All use fictional names.
- Added `tests/test_store.py` (7 tests) and `pytest.ini`.

**Check output summary:**
- `pytest -v`: 7 passed, exit code 0.
- Loading `PRB-0001`, `PRB-0002` and `PRB-0003` succeeds. `list_cases()` returns all three.
- A malformed case (state `frozen`) raises `ValueError: case PRB-9002 is invalid: ... Input should be 'issued', ...`.
- `reset_case` copies a golden case over a drifted working copy (tested in a temp folder).

### M2: Rules engine, no AI (2026-10-29)
- Owner approved the EXAMPLE set. `data/shelf/` is empty, and the probate source pack has not yet been turned into rules.
- Added `data/rules.yaml` with the 11 EXAMPLE rules from spec Section 5.2. Each has `source: "EXAMPLE"` and the top comment `# EXAMPLE RULES — replace with shelf data`. Rules: 7 deterministic, 4 judgement.
- Added `officer/rules.py`: `load_rules`, `get_path`, `get_doc`, the 8 check functions, `CHECKS`, `applicable`, `run_deterministic` and `judgement_rules_for`.
- Added `tests/test_rules.py` (27 tests in total with M1). Each check type has pass and fail tests, plus missing-field and missing-document tests.

**Check output summary:**
- `pytest`: 27 passed.
- Findings on the three M1 cases:
  - `PRB-0001`: all 7 deterministic rules pass. Judgement rules listed for later: R-WILL-05, R-WILL-06, R-WILL-07, R-NAME-01.
  - `PRB-0002`: R-DOC-01 fails (`DEATH_CERT_MISSING`, `request_document`). All others pass.
  - `PRB-0003`: R-WILL-01 fails (`ORIGINAL_WILL_MISSING`, `request_document`). All others pass.

### M3: Single-call diagnoser (2026-10-29)
- Added `officer/llm.py`: the only module that calls the SDK. Lazy client, retry on 429 and 529, `USAGE`, `reset_usage()` and `cost_usd()`.
- Added `officer/prompts.py` with `PROMPT_VERSION = "v1"` and `DIAGNOSE_SYSTEM`, copied verbatim from spec Section 7.
- Added `officer/diagnose.py`: `diagnose` (one forced-tool call), `rules_only` (baseline, no call), and `SUBMIT_DIAGNOSIS_TOOL`.
- Added `cli.py`: `python cli.py <case_id> [--mode diagnose|rules]`. Prints the diagnosis and the usage and cost.
- Switched `scripts/ping.py` to `llm.call`, which removes the M0 deviation.
- Added `tests/conftest.py` (`fake_llm` and `tmp_data` fixtures) and `tests/test_diagnose.py` (11 tests). All 38 tests in the suite pass.

**Check output summary:**
- `env -u ANTHROPIC_API_KEY pytest`: 38 passed. The suite needs no key.
- `python cli.py PRB-0002` (live, one call): `Next action: stop_case`, `Stop reasons: DEATH_CERT_MISSING`, `Rules cited: R-DOC-01, R-WILL-05, R-WILL-06, R-WILL-07, R-NAME-01`. Usage: 1 call, 1987 input tokens, 338 output tokens. Cost showed $0.000000 because the prices were still 0 at the time. They were set in M6.
- Out-of-scope check, using a temp copy with `PRB-0001` set to `granted`: `next_action: refuse_out_of_scope`, `API calls: 0`.

**Deviations:**
- **`SUBMIT_DIAGNOSIS_TOOL` lives in `diagnose.py`.** Spec Section 4 puts tool schemas in `tools.py`, which is an M5 file. It moves there in M5.
- **Retry count is an interpretation.** Spec says "3 attempts at 2s, 4s, 8s". This implementation makes 3 attempts in total, with waits of 2s and 4s between them. Owner to confirm.
- **The retry path is not tested.** The suite tests the diagnoser with a fake LLM, so `llm.call` retries are untested. Add a test in M5 or later.
- **`cli.py` loads `.env` itself.** The first live run showed the key would not load without it.

### M4: Golden set, evals v1, README v1 (2026-10-29)
- Added `scripts/make_cases.py --golden`: 20 synthetic cases (`PRB-G001` to `PRB-G020`) and `data/golden/expected.jsonl`. Mix: clean 5, single_fault 7, multi_fault 4, escalation 2, out_of_scope 1, injection 1. Split: 8 dev, 12 test.
- Labels are derived from the fault list and from the action each stop reason carries in `rules.yaml`. The script checks the deterministic labels against the real rules engine and stops on any mismatch.
- Added `evals/metrics.py` (all the spec metrics, plus bootstrap helpers) and `tests/test_metrics.py`.
- Added `evals/run_evals.py` (variants `diagnose` and `rules`, the cost guard, and per-run rows) and `evals/report.py` (report.md).
- Added `tests/test_golden.py` (split and bucket counts, and label checks against the rules) and `tests/test_report.py` (failure categories and the cost guard).
- Wrote `README.md` v1 with the results table. Each number matches the report files.
- Moved `.env` loading into `officer/llm.py`, so every entry point gets the key. `cli.py` and `ping.py` had their own copies, and `run_evals` was missing it.
- The price warning prints once per run, not once per case.

**Check output summary:**
- `pytest`: 66 passed.
- Dev split, diagnose, k=1 (8 calls): all metrics 1.000, 0 failures.
- Test split, rules, k=1 (12 runs): next-action accuracy 0.917. One failure: `PRB-G018` (escalation case) routed to the examiner, which is unsafe. Escalation recall 0.000.
- Test split, diagnose, k=3 (36 runs, `--yes`): all metrics 1.000, 0 failures. The actual call count was 33, because the 3 out-of-scope runs made no calls. The guard estimate counts all 36.

**Honesty notes:**
- Both test runs came after the dev run. No prompt was changed, so `PROMPT_VERSION` stays `v1`. No test failures were seen, so there was nothing to retune.
- The diagnose result of 1.000 on 12 synthetic cases shows little. The intervals collapse to [1.000, 1.000]. The golden set is generated from the same rules as the checks, so it is easy by design. Treat the number as a sanity check, not evidence of real-world quality.
- Golden labels are not yet reviewed by the owner (spec Section 14: spot-check 1 in 3). That review is needed before results are trusted.

**Deviations:**
- **`evals/report.py` is a separate file.** It keeps `run_evals.py` under about 200 lines. The spec's layout does not list it.
- **`scripts/make_cases.py` is 222 lines**, over the spec's 200-line guide. Proposed split, not yet done: move the fault functions and `FAULTS` into a separate `scripts/faults.py`. The owner decides.
- **`tests/test_golden.py` and `tests/test_report.py` are extra test files.** The spec's Section 4 layout does not list them, but they cover the golden labels and the report logic.
- **`--k` defaults to `config.EVAL_K` (3).** `rules` always runs k=1, as the spec says.
- **The cost estimate uses fixed token counts** (2,000 in, 350 out per call). It is rough. Prices were still 0 at the time; they were set in M6.

### M5: Read-only agent loop and audit trail (2026-10-29)
- Added `officer/audit.py`: `log` writes one JSON line per event to `logs/trace.jsonl`. `read_run` and `last_run_id` read it back.
- Added `officer/tools.py`: the READ tools (`get_case`, `run_rule_checks`, `lookup_rule`, `get_template`), the `TOOLS` registry, `schemas()` and `execute()`. Also the `submit_diagnosis` schema, moved here from `diagnose.py`.
- Added to `officer/rules.py`: `run_judgement` (one forced `record_judgement` call per applicable judgement rule), `run_all`, and the `record_judgement` schema.
- Added `AGENT_SYSTEM` and `JUDGE_RULE_SYSTEM` to `officer/prompts.py`, verbatim from spec Section 7.
- Added `officer/agent.py`: `run_case(case_id, allow_write=False)`. It runs the scope guard, then the loop, with one nudge, a turn cap, validation errors fed back, and an audit event for each step. It returns `(diagnosis, None)` until M6 adds the gate.
- Added agent mode to `cli.py`. It prints the trace from the audit log.
- Added the `agent` variant to `evals/run_evals.py`, plus completion rate and tool error rate in `evals/metrics.py` and `evals/report.py`.
- Added `tests/test_tools.py`, `tests/test_judgement.py` and `tests/test_agent.py`. The suite has 95 tests, and all pass.

**Prompt v2 (changed in M5, after I saw a failure):**
- **Found:** `cli.py PRB-G003 --mode agent` escalated a clean case. The judge gave three false failures. Three causes:
  1. R-WILL-07 was inverted. Its question asked whether a codicil is mentioned, so a clean "no" failed the rule.
  2. R-NAME-01 could never pass with one document. The judge called it ambiguous, and an unclear answer fails under the spec.
  3. The judge never saw the applicant's name, which is a structured field, so R-WILL-06 failed with "applicant not identified".
- **Changed:** R-WILL-07 and R-NAME-01 are reworded in `data/rules.yaml`. `_case_documents` now includes the applicant and deceased names. `PROMPT_VERSION` is now `v2`. A second wording fix was needed for R-NAME-01 after `PRB-G001` was judged ambiguous.
- **Disclosure:** `PRB-G003` is in the test split. I read a test-split failure before fixing it. The fixes are defects in my wording and input, not answers tuned to the labels. The spec's rule that test runs happen once per version is kept: the v2 test run is the single test run for v2.
- **Rerun:** the diagnose test split was rerun once on v2 (`20261029-182146_diagnose_test`). It gives the same numbers as v1 (`20261029-082904_diagnose_test`). The README now points to the v2 run. The rules baseline did not change, since it does not use judgement wording.

**Check output summary:**
- `pytest`: 95 passed.
- `cli.py PRB-G003 --mode agent` (before the v2 fix): escalated a clean case. The trace shows the three judge failures above.
- `cli.py PRB-G001 --mode agent` (after v2): `route_to_examiner`, correct.
- Agent, dev split, k=1 (`20261029-182012_agent_dev`): next-action accuracy 0.375 [0.125, 0.750]. Stop-reason micro F1 1.000. Completion 1.000. Tool error rate 0.000. Failures: 5 of 8 cases are `wrong_action`. `PRB-G002` is refused as "at or after examination". `PRB-G006`, `PRB-G007`, `PRB-G008` and `PRB-G013` get the right stop reasons but `escalate` where `stop_case` is expected.
- Diagnose, dev, v2 (`20261029-182040_diagnose_dev`, k=1): 1.000, no failures.

**Open for the owner (decide before M6):**
- **The agent escalates instead of stopping.** In a read-only run, `AGENT_SYSTEM` tells the agent to propose `stop_case` and `request_document` through write tools, and those tools do not exist yet. The model falls back to `escalate` for every missing-item case. M6's write tools may fix this. The prompt is verbatim from the spec, so I have not changed it.
- **The agent refuses `issued` cases as "at or after examination"** (`PRB-G002`). The sentence "You cannot grant, issue, or act on anything at or after examination" is being read as covering the issued state. Either reword the prompt (a spec change) or accept it.
- **The rule wording in `rules.yaml` is my edit.** R-WILL-07 and R-NAME-01 were reworded to make them pass or fail correctly. Confirm the new wording is what you want.

**Deviations:**
- **`get_template` is in the READ tools now**, as the spec's Section 8 table lists it under M5. It reports the template as missing until M6 adds templates.
- **`SUBMIT_DIAGNOSIS_TOOL` moved from `diagnose.py` to `tools.py`.** This resolves the M3 deviation. `diagnose.py` imports it.
- **`RECORD_JUDGEMENT_TOOL` lives in `rules.py`**, not `tools.py`. `rules.py` needs it, and `tools.py` imports `rules`, so putting it in `tools.py` would create an import cycle.
- **`officer/rules.py` is now 209 lines**, over the spec's 200-line guide. Splitting the judgement checks into their own file is the obvious option. Not done; owner's call.
- **Agent mode in `cli.py` does not apply the cost guard.** It makes one run of up to about 6 to 8 calls, and the guard in `run_evals.py` covers the eval runs. Spec Rule 8 applies to any script that makes more than 10 calls, so this may need adding.
- **The agent estimate in the cost guard is rough** (`ESTIMATE_AGENT_CALLS = 6`, per run). The observed agent dev run used 48 calls, which matches the estimate.

### Extension: email intake, dry run (2026-10-29)
- Added `officer/intake/email_reader.py` and `scripts/interpret_email.py`. They read one incoming email and find the case reference, the intents (status enquiry, document submitted, reported fact) and any reported fact. They then plan the CCD calls the system would make, each with its input and expected output. Nothing is executed or sent, and every write is a proposal.
- Plain pattern matching, with no model call. Tests: `tests/test_intake.py`, including an email that tries to approve actions.

### M6: Write actions and the approval gate (2026-10-29)
- Added `officer/gate.py`: `ALLOWED_TRANSITIONS`, and `Gate` with `propose`, `decide` and `_apply`. Nothing changes until `decide(..., approved=True)`. Each proposal can be decided once. Each decision is logged to the audit trail and to `data/preferences.jsonl`.
- Added five WRITE tools to `officer/tools.py`: `stop_case`, `request_document`, `add_case_note`, `route_to_examiner`, `escalate`. The `execute` function routes them only to `gate.propose`.
- Added templates `data/templates/req_death_certificate.txt` and `req_original_will.txt`. `get_template` now returns them.
- `agent.run_case(..., allow_write=True)` now creates a gate and returns it. Without writes, a WRITE call returns an error to the model.
- CLI agent mode allows writes, lists each proposal, and asks `approve? [y/n/skip]`. No terminal means everything stays pending.
- Added the `agent_write` eval variant. It records proposals and never approves them.
- Added `tests/test_gate.py` (11 tests). The suite has 119 tests, all passing.

**Check output summary:**
- Acceptance run: `printf 'y\n...' | cli.py PRB-0002 --mode agent`. The agent proposed `escalate`, which was approved. The case went from `issued` to `escalated`, and one preference line was written. The proposal was `escalate`, not `stop_case`, because of the `issued` misreading seen before. The gate tests cover `stop_case` and `request_document` directly.
- After the run, the case file was restored from git and the test preference line was deleted.

**Deviations:**
- `execute` passes the gate to WRITE tools, and `run_case` returns the gate, which the spec implies but does not show.
- `ALLOWED_TRANSITIONS` also allows `stopped` to `stopped`, because the spec lists `issued` or `stopped` as the source states.

### M7: Full evals (2026-10-29)
- Golden set grows to 40 cases (16 dev, 24 test) with the spec's v2 mix. `make_plan(20)` reproduces the v1 set exactly. The generator is split into `scripts/case_factory.py` and `scripts/make_cases.py`.
- New variants: `llm_only` (no rule-check tool, rules pasted into the prompt), `agent_write` (proposals recorded, never approved), `baseline` (M8).
- `evals/judge.py`: LLM letter judge, hand-score export (`--export`) and calibration (`--calibrate`). `evals/component.py`: each judgement rule alone. `evals/compare.py`: ablation table and failure analysis.
- `python -m evals.report <folder>` rebuilds a report from saved rows.

**Eval fixes found during M7 (all logged in `evals/snapshot/prompt_story.md`):**
- Bootstrap intervals now resample whole cases, since the k runs of a case are not independent.
- A scope-guard refusal counts as a completed run (completion had been 0.917, all of it refusals).
- The spec's invented-citation metric is now two numbers: off-list citations (a real rule that did not fail) and non-existent rule IDs (hallucination). llm-only's 0.514 was all over-citing, with 0 hallucinated IDs.
- The letter judge now grades all of a run's letters together. Graded one letter at a time, it failed 6 correct letters from a case with two missing documents.

**Prompt v3 (agent prompt only):** the spec's sentence "You cannot grant, issue, or act on anything at or after examination" made the agent escalate in-scope `issued` cases. Test accuracy 0.417 (`20261029-191112_agent_test`). v3 states the scope and uses the diagnoser's outcome definitions. Dev 16 of 16, then test 1.000 (`20261029-193154_agent_test`).

**Prompt v4 (rule R-WILL-05 only):** the hand-written showcase matched 6 of 8. The judge failed naturally worded wills for "no actual signatures, only typed names." The rule question now says how a signature appears in a transcription. Showcase 8 of 8, dev component 16 of 16 per rule. Every variant that reads the judgement rules was rerun once on test. The v4 numbers are in the README and `evals/snapshot/ablation.md`.

**Owner input still needed:** 15 hand-scored letter sets in `evals/human_scores.jsonl`. Run `python -m evals.judge --export --run <agent_write folder>` to get them in readable form.

### M8: PyTorch baseline (2026-10-29)
- `make_cases.py --train 300` writes templated training cases with a different seed to `baseline/train_cases/`.
- `baseline/train_baseline.py`: TF-IDF (fit on training data only) and `torch.nn.Linear`, Adam, 200 epochs. Loss 0.92 → 0.65. Predicts the next action only, with no stop reasons.
- Test split: next-action accuracy 0.625 [0.417, 0.833], unsafe-action rate 0.083.

### M9: Demo and write-up (2026-10-29)
- `app.py` (Streamlit): showcase mode with 8 hand-written scenarios, rules-only beside the agent, an expected-outcome check, approve and reject, the trace and the cost. The Evals tab shows the committed snapshot in `evals/snapshot/`.
- `scripts/make_showcase.py`, `scripts/showcase.py` (terminal backup), `scripts/watch_trace.py` (live view of the audit log).
- `README.md` rewritten. `DESIGN.md`, `DEMO.md` and the WALKTHROUGH entries are added.

**Deviations:**
- `evals/results/` stays git-ignored, as the spec says. A snapshot of the final reports is committed in `evals/snapshot/`, so the demo works on a fresh clone.
- `officer/rules.py` is 211 lines, over the guide. Splitting the judgement checks into their own file is proposed, along with the seven-component layout. Owner's call.

### Restructure into seven components (2026-10-30)
- `officer/` is now one package per step in the job: `intake` (store, email reader), `scope` (new `guard.py`), `checks` (deterministic rules), `judgement` (new `judge_rules.py`, split from `rules.py`), `decision` (agent, diagnose, tools), `gate` (approval) and `audit` (trail). `models.py`, `llm.py` and `prompts.py` stay shared.
- The scope guard was copied in the diagnoser and the agent. It is now one module, used by both.
- Each component has a `README.md` contract. Added `tests/test_scope.py` and `tests/test_audit.py`. 148 tests pass.
- Every file in `officer/` is now under 200 lines. `rules.py` (211) became `checks/rules.py` (147) and `judgement/judge_rules.py` (76).

**Behaviour unchanged, checked four ways:** the 141 existing tests pass. Rules-only output is identical on all 51 cases before and after. Regenerated golden, training and showcase data are byte-identical. The live showcase matches 8 of 8.

**Deviation:** the spec's Section 4 layout lists flat files in `officer/` (such as `officer/rules.py`). The paths changed, but the spec's rules hold: `officer/llm.py` is still the only module that imports `anthropic`, and tests still mock `officer.llm.call`. Older entries below keep the old paths as history.

## Open questions (current, 2026-10-30)

- **Judge calibration:** needs 15 hand-scored letter sets in `evals/human_scores.jsonl`. Export them with `python -m evals.judge --export --run evals/results/<agent_write folder>`. Until then, judge agreement is unreported.
- **Golden-label review:** the owner should spot-check at least 1 in 3 golden labels (spec Section 14).
- **Rules:** all 11 rules are EXAMPLE rules. The probate source pack in `data/shelf/` (git-ignored) is not yet paraphrased into rules.
- **Rule wording:** R-WILL-05, R-WILL-07 and R-NAME-01 were reworded during the build so they pass and fail correctly. The owner should confirm the wording.

**Resolved:**
- **Prices:** set in M6 from https://claude.com/pricing: $0.10 input and $0.50 output per million tokens, for prompts up to 100K tokens.
- **Python version:** the README says Python 3.11 or newer, and uses `python3.12` in its commands.
- **Retry count:** 3 attempts with 2s and 4s waits, as implemented. Not re-raised.

## Shelf ambiguities
- The shelf is empty. Every rule uses `source: "EXAMPLE"`.
- The probate source pack (`data/shelf/probate_process_source_pack.md`) is not converted into rules yet. The owner's review comes first.
- Fee and timescale conflicts from the source pack are not reflected in any rule.

## Deviations

- **`scripts/ping.py` imports `anthropic` directly.** Section 6 says `officer/llm.py` is the only module that imports it, but `llm.py` is an M3 file. M0's task is to ping Haiku, so the script calls the SDK itself. Once `llm.py` exists in M3, `ping.py` can switch to it.
- **`tests/` has no test files yet.** Section 4 places `conftest.py` and the first tests in M1 and M3. `pytest` therefore collects 0 tests, which the spec allows for M0.
- **`data/golden/` is not created.** It belongs to M4. `data/rules.yaml` now exists (M2). The M2 acceptance check was run on the three M1 cases only.
- **`load_rules(path=None)` reads its default at call time.** This matches the store, and the spec shows a fixed default.
- **`run_judgement` and `run_all` are not written.** They are M5 items. M2 only lists judgement rules.
- **`pytest.ini` added in M1.** Spec Section 4 does not list it. It sets `pythonpath = .` so tests can import `officer` without a `conftest.py`. `conftest.py` arrives in M3.
- **Store default directories are read at call time.** `load_case`, `save_case` and `list_cases` take `directory=None` and fall back to `config.CASES_DIR` when called. The spec shows the default as a fixed value. Reading it at call time lets tests redirect the store, so tests never write to real files.
- **`test_three_hand_written_cases_load` reads the real `data/cases/`.** It is read-only and matches the M1 acceptance criteria. All other store tests use a temp folder.

- **`WALKTHROUGH.md` is kept private.** Spec Section 13's file-by-file guide is the owner's study notes, so it is git-ignored rather than committed. It covers every file.

## Next

- **A harder test set.** 24 templated cases are small and easy. Add near-miss cases (one witness, a codicil that was lodged, misspelt names), varied natural wording, and injection hidden in the will text itself. The showcase already showed natural prose exposing a rule the test set called perfect.
- **Reliability metrics.** Report pass^k (all k runs right) beside accuracy, and how large a difference the test set can detect.
- **Judge calibration**, once the hand scores are in.
- **Learn from the preference log.** Each approve or reject is a labelled example. Enough of them could train a reward model to rank proposals.
