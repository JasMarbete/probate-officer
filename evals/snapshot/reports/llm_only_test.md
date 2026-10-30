# Eval report: llm_only on test

## Settings
- Variant: llm_only
- Split: test
- k: 3
- Model: claude-haiku-5-5
- Prompt version: v4
- Date: 2026-10-30T07:24:06
- Cases: 24, runs: 72

## Metrics (95% bootstrap CIs, resampled by case)
| Metric | Value | 95% CI |
|---|---|---|
| Next-action accuracy | 1.000 | [1.000, 1.000] |
| Stop-reason micro precision | 1.000 | [1.000, 1.000] |
| Stop-reason micro recall | 0.984 | [0.939, 1.000] |
| Stop-reason micro F1 | 0.992 | [0.969, 1.000] |
| Off-list citation rate (real rule, did not fail) | 0.519 | [0.416, 0.577] |
| Non-existent rule rate (hallucinated ID) | 0.000 | [0.000, 0.000] |
| Unsafe-action rate | 0.000 | [0.000, 0.000] |
| Escalation recall | 1.000 | [1.000, 1.000] |
| Consistency across runs | 1.000 | [1.000, 1.000] |
| Completion rate (agent) | 1.000 | [1.000, 1.000] |
| Tool error rate (agent) | 0.000 | [0.000, 0.000] |

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
| WILL_EXECUTION_QUERY | 0.667 |

## Failures
| Case | Run | Expected | Got | Category |
|---|---|---|---|---|
| PRB-G033 | 2 | escalate (WILL_EXECUTION_QUERY) | escalate (none) | missed_fault |

## Cost and latency
- Total cost: $0.068384
- Mean cost per case: $0.002849
- Calls: 135, input tokens: 409666, output tokens: 54834
- Latency p50 4.77s, p95 7.07s
