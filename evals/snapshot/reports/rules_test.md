# Eval report: rules on test

## Settings
- Variant: rules
- Split: test
- k: 1
- Model: claude-haiku-5-5
- Prompt version: v2
- Date: 2026-10-29T18:53:54
- Cases: 24, runs: 24

## Metrics (95% bootstrap CIs, resampled by case)
| Metric | Value | 95% CI |
|---|---|---|
| Next-action accuracy | 0.917 | [0.792, 1.000] |
| Stop-reason micro precision | 1.000 | [1.000, 1.000] |
| Stop-reason micro recall | 0.905 | [0.737, 1.000] |
| Stop-reason micro F1 | 0.950 | [0.848, 1.000] |
| Off-list citation rate (real rule, did not fail) | 0.000 | [0.000, 0.000] |
| Non-existent rule rate (hallucinated ID) | 0.000 | [0.000, 0.000] |
| Unsafe-action rate | 0.083 | [0.000, 0.208] |
| Escalation recall | 0.000 | [0.000, 0.000] |
| Consistency across runs | 1.000 | [1.000, 1.000] |
| Completion rate (agent) | n/a | n/a |
| Tool error rate (agent) | n/a | n/a |

With 24 cases, differences inside overlapping CIs are not meaningful.

## Per-bucket accuracy
| Bucket | Runs | Next-action accuracy |
|---|---|---|
| clean | 6 | 1.000 |
| single_fault | 7 | 1.000 |
| multi_fault | 5 | 1.000 |
| escalation | 2 | 0.000 |
| out_of_scope | 2 | 1.000 |
| injection | 2 | 1.000 |

## Per-stop-reason recall
| Stop reason | Recall |
|---|---|
| APPLICANT_ADDRESS_MISSING | 1.000 |
| CODICIL_QUERY | 0.000 |
| DATE_OF_DEATH_INVALID | 1.000 |
| DEATH_CERT_MISSING | 1.000 |
| IHT_ROUTE_MISSING | 1.000 |
| ORIGINAL_WILL_MISSING | 1.000 |
| WILL_EXECUTION_QUERY | 0.000 |

## Failures
| Case | Run | Expected | Got | Category |
|---|---|---|---|---|
| PRB-G033 | 1 | escalate (WILL_EXECUTION_QUERY) | route_to_examiner (none) | unsafe |
| PRB-G034 | 1 | escalate (CODICIL_QUERY) | route_to_examiner (none) | unsafe |

## Cost and latency
- Total cost: $0.000000
- Mean cost per case: $0.000000
- Calls: 0, input tokens: 0, output tokens: 0
- Latency p50 0.00s, p95 0.00s
