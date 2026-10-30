# Component 1: Intake

**The step in the officer's job:** Receive the case and check it is well-formed.

Loads a case file and validates it against the data contract, so a malformed case fails loudly at the door instead of confusing a later step. Also reads an incoming email and plans the system calls it would make, as a dry run.

## Contract

| Call | Does |
|---|---|
| `store.load_case(case_id, directory=None) -> Case` | load and validate one case; clear `FileNotFoundError` or `ValueError` |
| `store.save_case(case, directory=None)` | write a case back as JSON |
| `store.list_cases(directory=None) -> list[str]` | sorted case IDs |
| `store.reset_case(case_id)` | copy the clean golden copy over the working copy |
| `email_reader.interpret(text) -> dict` | case reference, intents, reported facts, and planned actions, none executed |

- **Depends on:** `officer.models`, `config`
- **Used by:** every other component
- **Tested by:** `tests/test_store.py`, `tests/test_intake.py`

## Building it alone

No model, no network. Change the data contract in `officer/models.py`, and these tests tell you what broke.
