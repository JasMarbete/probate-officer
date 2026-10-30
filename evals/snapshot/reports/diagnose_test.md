# Eval report: diagnose on test

## Settings
- Variant: diagnose
- Split: test
- k: 3
- Model: claude-haiku-5-5
- Prompt version: v4
- Date: 2026-10-30T02:50:36
- Cases: 24, runs: 72

## Metrics (95% bootstrap CIs, resampled by case)
| Metric | Value | 95% CI |
|---|---|---|
| Next-action accuracy | 1.000 | [1.000, 1.000] |
| Stop-reason micro precision | 1.000 | [1.000, 1.000] |
| Stop-reason micro recall | 1.000 | [1.000, 1.000] |
| Stop-reason micro F1 | 1.000 | [1.000, 1.000] |
| Off-list citation rate (real rule, did not fail) | 0.000 | [0.000, 0.000] |
| Non-existent rule rate (hallucinated ID) | 0.000 | [0.000, 0.000] |
| Unsafe-action rate | 0.000 | [0.000, 0.000] |
| Escalation recall | 1.000 | [1.000, 1.000] |
| Consistency across runs | 1.000 | [1.000, 1.000] |
| Completion rate (agent) | n/a | n/a |
| Tool error rate (agent) | n/a | n/a |

With 24 cases, differences inside overlapping CIs are not meaningful.

## Per-bucket accuracy
| Bucket | Runs | Next-action accuracy |
|---|---|---|
| clean | 18 | 1.000 |
| single_fault | 21 | 1.000 |
| multi_fault | 15 | 1.000 |
| escalation | 6 | 1.000 |
| out_of_scope | 6 | 1.000 |
| injection | 6 | 1.000 |

## Per-stop-reason recall
| Stop reason | Recall |
|---|---|
| APPLICANT_ADDRESS_MISSING | 1.000 |
| CODICIL_QUERY | 1.000 |
| DATE_OF_DEATH_INVALID | 1.000 |
| DEATH_CERT_MISSING | 1.000 |
| IHT_ROUTE_MISSING | 1.000 |
| ORIGINAL_WILL_MISSING | 1.000 |
| WILL_EXECUTION_QUERY | 1.000 |

## Failures
| Case | Run | Expected | Got | Category |
|---|---|---|---|---|
| none | | | | |

## Cost and latency
- Total cost: $0.024369
- Mean cost per case: $0.001015
- Calls: 66, input tokens: 135933, output tokens: 21551
- Latency p50 1.81s, p95 3.31s
