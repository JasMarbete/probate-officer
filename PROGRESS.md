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

## Open questions

- **Shelf data:** `data/shelf/` is empty, so M2 will use the EXAMPLE rules unless shelf content is added first.
- **Prices:** `PRICE_IN_PER_M` and `PRICE_OUT_PER_M` in `config.py` are still 0.0. The owner fills them from Anthropic's pricing page.
- **Python version:** the spec asks for 3.11+. The project venv uses Python 3.14 (`/opt/homebrew/bin/python3.14`). The system `python3` is 3.9, which is too old.

## Deviations

- **`scripts/ping.py` imports `anthropic` directly.** Section 6 says `officer/llm.py` is the only module that imports it, but `llm.py` is an M3 file. M0's task is to ping Haiku, so the script calls the SDK itself. Once `llm.py` exists in M3, `ping.py` can switch to it.
- **`tests/` has no test files yet.** Section 4 places `conftest.py` and the first tests in M1 and M3. `pytest` therefore collects 0 tests, which the spec allows for M0.
- **`data/rules.yaml` and `data/golden/` are not created.** They belong to M2 and M4. `data/cases/` now exists (M1).
- **`pytest.ini` added in M1.** Spec Section 4 does not list it. It sets `pythonpath = .` so tests can import `officer` without a `conftest.py`. `conftest.py` arrives in M3.
- **Store default directories are read at call time.** `load_case`, `save_case` and `list_cases` take `directory=None` and fall back to `config.CASES_DIR` when called. The spec shows the default as a fixed value. Reading it at call time lets tests redirect the store, so tests never write to real files.
- **`test_three_hand_written_cases_load` reads the real `data/cases/`.** It is read-only and matches the M1 acceptance criteria. All other store tests use a temp folder.

## Next

- **M1:** `officer/models.py`, `officer/store.py`, three hand-written cases in `data/cases/`, and `tests/test_store.py`.
- Before M1, the owner should check the `.env` key with `python scripts/ping.py`, and add shelf data to `data/shelf/` if they have it.
