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
- `python scripts/ping.py`: not run against the live API, because no key is set. It exits 1 with the message "No ANTHROPIC_API_KEY found", as designed. The owner needs to add a key to `.env` and rerun it.
- `config.py` and `officer` import cleanly.

## Open questions

- **Shelf data:** `data/shelf/` is empty, so M2 will use the EXAMPLE rules unless shelf content is added first.
- **Prices:** `PRICE_IN_PER_M` and `PRICE_OUT_PER_M` in `config.py` are still 0.0. The owner fills them from Anthropic's pricing page.
- **Live API check:** `scripts/ping.py` needs the owner's `ANTHROPIC_API_KEY` in `.env`. It has not been run against the live API yet.
- **Python version:** the spec asks for 3.11+. The project venv uses Python 3.14 (`/opt/homebrew/bin/python3.14`). The system `python3` is 3.9, which is too old.

## Deviations

- **`scripts/ping.py` imports `anthropic` directly.** Section 6 says `officer/llm.py` is the only module that imports it, but `llm.py` is an M3 file. M0's task is to ping Haiku, so the script calls the SDK itself. Once `llm.py` exists in M3, `ping.py` can switch to it.
- **`tests/` has no test files yet.** Section 4 places `conftest.py` and the first tests in M1 and M3. `pytest` therefore collects 0 tests, which the spec allows for M0.
- **`data/rules.yaml`, `data/cases/` and `data/golden/` are not created.** They belong to M1, M2 and M4.

## Next

- **M1:** `officer/models.py`, `officer/store.py`, three hand-written cases in `data/cases/`, and `tests/test_store.py`.
- Before M1, the owner should check the `.env` key with `python scripts/ping.py`, and add shelf data to `data/shelf/` if they have it.
