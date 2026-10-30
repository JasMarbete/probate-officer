# Component 3: Deterministic checks

**The step in the officer's job:** Are the documents and fields there?

Runs every rule that plain Python can check, from `data/rules.yaml`: death certificate received, original will lodged, address given, date of death valid, domicile, IHT route, net not above gross. A missing field or document is a fail, never a crash.

## Contract

| Call | Does |
|---|---|
| `rules.load_rules(path=None) -> list[dict]` | the rules file |
| `rules.run_deterministic(case) -> list[Finding]` | one finding per applicable deterministic rule |
| `rules.judgement_rules_for(case) -> list[dict]` | the judgement rules that apply (component 4 reads them) |
| `rules.CHECKS` | the eight check types, by name |

- **Depends on:** `officer.models`, `config`, `data/rules.yaml`
- **Used by:** `officer.judgement`, `officer.decision`, the evals and the case generator
- **Tested by:** `tests/test_rules.py`, `tests/test_golden.py`, `tests/test_showcase.py`

## Building it alone

No model. A new rule that uses an existing check type is a YAML entry only; the golden-set tests catch any label it breaks.
