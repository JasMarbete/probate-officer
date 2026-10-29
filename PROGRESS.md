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
- `python cli.py PRB-0002` (live, one call): `Next action: stop_case`, `Stop reasons: DEATH_CERT_MISSING`, `Rules cited: R-DOC-01, R-WILL-05, R-WILL-06, R-WILL-07, R-NAME-01`. Usage: 1 call, 1987 input tokens, 338 output tokens. Cost shows $0.000000 because the prices are still 0.
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
- **The cost estimate uses fixed token counts** (2,000 in, 350 out per call). It is rough. Prices are still 0, so the cost shows $0.

## Open questions (added in M3)
- **Prices:** `PRICE_IN_PER_M` and `PRICE_OUT_PER_M` are still 0. The owner fills them in from Anthropic's pricing page. Until then, costs are reported as $0.

## Shelf ambiguities
- The shelf is empty. Every rule uses `source: "EXAMPLE"`.
- The probate source pack (`data/shelf/probate_process_source_pack.md`) is not converted into rules yet. The owner's review comes first.
- Fee and timescale conflicts from the source pack are not reflected in any rule.

## Open questions

- **Shelf data:** `data/shelf/` is empty, so M2 will use the EXAMPLE rules unless shelf content is added first.
- **Prices:** `PRICE_IN_PER_M` and `PRICE_OUT_PER_M` in `config.py` are still 0.0. The owner fills them from Anthropic's pricing page.
- **Python version:** the spec asks for 3.11+. The project venv uses Python 3.14 (`/opt/homebrew/bin/python3.14`). The system `python3` is 3.9, which is too old.

## Deviations

- **`scripts/ping.py` imports `anthropic` directly.** Section 6 says `officer/llm.py` is the only module that imports it, but `llm.py` is an M3 file. M0's task is to ping Haiku, so the script calls the SDK itself. Once `llm.py` exists in M3, `ping.py` can switch to it.
- **`tests/` has no test files yet.** Section 4 places `conftest.py` and the first tests in M1 and M3. `pytest` therefore collects 0 tests, which the spec allows for M0.
- **`data/golden/` is not created.** It belongs to M4. `data/rules.yaml` now exists (M2). The M2 acceptance check was run on the three M1 cases only.
- **`load_rules(path=None)` reads its default at call time.** This matches the store, and the spec shows a fixed default.
- **`run_judgement` and `run_all` are not written.** They are M5 items. M2 only lists judgement rules.
- **`pytest.ini` added in M1.** Spec Section 4 does not list it. It sets `pythonpath = .` so tests can import `officer` without a `conftest.py`. `conftest.py` arrives in M3.
- **Store default directories are read at call time.** `load_case`, `save_case` and `list_cases` take `directory=None` and fall back to `config.CASES_DIR` when called. The spec shows the default as a fixed value. Reading it at call time lets tests redirect the store, so tests never write to real files.
- **`test_three_hand_written_cases_load` reads the real `data/cases/`.** It is read-only and matches the M1 acceptance criteria. All other store tests use a temp folder.

## Next

- **M1:** `officer/models.py`, `officer/store.py`, three hand-written cases in `data/cases/`, and `tests/test_store.py`.
- Before M1, the owner should check the `.env` key with `python scripts/ping.py`, and add shelf data to `data/shelf/` if they have it.
