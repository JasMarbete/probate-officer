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
