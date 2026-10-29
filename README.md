# ProbateOfficer

An AI employee that diagnoses HMCTS probate cases. Version 1 is diagnosis only: it reads a case, runs deterministic rule checks in Python, makes one Haiku call for the judgement calls, and returns a structured diagnosis. It never changes a case.

All data is synthetic. Not connected to any HMCTS system.

## How to run

Requirements: Python 3.11 or later.

```bash
python3.14 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env   # then put your ANTHROPIC_API_KEY in .env
```

Run the tests (no API key needed):

```bash
.venv/bin/pytest
```

Diagnose one case (one model call):

```bash
.venv/bin/python cli.py PRB-0002
```

Run the evals. The `diagnose` variant makes model calls and the `rules` variant makes none:

```bash
.venv/bin/python -m evals.run_evals --variant diagnose --split test --k 3
.venv/bin/python -m evals.run_evals --variant rules --split test
```

Runs over 10 model calls ask first, and `--yes` skips the question. Each run writes `evals/results/<timestamp>_<variant>_<split>/` with `rows.jsonl` and `report.md`.

Regenerate the golden set:

```bash
.venv/bin/python scripts/make_cases.py --golden
```

## Results (v1, test split, 12 cases)

Both rows come from the reports in `evals/results/`: diagnose from `20261029-082904_diagnose_test` (k=3, 36 runs), and rules from `20261029-082750_rules_test` (k=1, 12 runs).

| Metric | Diagnose (Haiku) | Rules only |
|---|---|---|
| Next-action accuracy | 1.000 [1.000, 1.000] | 0.917 [0.750, 1.000] |
| Stop-reason micro precision | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] |
| Stop-reason micro recall | 1.000 [1.000, 1.000] | 0.900 [0.625, 1.000] |
| Stop-reason micro F1 | 1.000 [1.000, 1.000] | 0.947 [0.769, 1.000] |
| Invented-citation rate | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] |
| Unsafe-action rate | 0.000 [0.000, 0.000] | 0.083 [0.000, 0.250] |
| Escalation recall | 1.000 [1.000, 1.000] | 0.000 [0.000, 0.000] |
| Consistency across runs | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] |

Brackets are 95% bootstrap intervals. With 12 cases, differences inside overlapping intervals are not meaningful.

The rules-only baseline misses the judgement-based escalation case (PRB-G018, a codicil not in the document list). It routes that case to the examiner, which the unsafe-action rate counts.

## Limitations

- **Synthetic data.** Every case is generated or hand-written with fictional names. Nothing here is measured on real cases.
- **Small test set.** 12 cases give intervals that are too wide to separate the variants reliably. The diagnose intervals collapse to [1.000, 1.000] because every run was correct.
- **Golden labels are not yet reviewed.** The owner should spot-check at least one label in three before the results are trusted.
- **Rules are EXAMPLE rules.** The shelf data is empty, so every rule in `data/rules.yaml` is a stand-in, not a probate rule.
- **Judgement rules are only checked by the model.** The generator cannot verify them, so judgement labels rest on the generator's fault list.
- **Cost is shown as $0.** The prices in `config.py` are not yet filled in.

## What's next

- Owner review of the golden labels, and of the probate source pack.
- Version 2: a tool-using agent loop with proposals, a human approval gate, and the full ablation (see `BUILD_SPEC.md`).
