24 held-out test cases. Model-based variants ran each case 3 times (72 runs). Rules and the baseline are deterministic, so they ran once per case. Brackets are 95% bootstrap intervals, resampled by case.

| Metric | rules | diagnose | agent | agent_write | llm_only | baseline |
|---|---|---|---|---|---|---|
| Next-action accuracy | 0.917 [0.792, 1.000] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 0.625 [0.417, 0.833] |
| Stop-reason micro precision | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 0.000 [0.000, 0.000] |
| Stop-reason micro recall | 0.905 [0.737, 1.000] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 0.984 [0.952, 1.000] | 0.984 [0.939, 1.000] | 0.000 [0.000, 0.000] |
| Stop-reason micro F1 | 0.950 [0.848, 1.000] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 0.992 [0.976, 1.000] | 0.992 [0.969, 1.000] | 0.000 [0.000, 0.000] |
| Off-list citation rate (real rule, did not fail) | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.519 [0.416, 0.577] | 0.000 [0.000, 0.000] |
| Non-existent rule rate (hallucinated ID) | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] |
| Unsafe-action rate | 0.083 [0.000, 0.208] | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.083 [0.000, 0.208] |
| Escalation recall | 0.000 [0.000, 0.000] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 0.500 [0.000, 1.000] |
| Consistency across runs | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] |
| Completion rate (agent) | n/a | n/a | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | n/a |
| Tool error rate (agent) | n/a | n/a | 0.000 [0.000, 0.000] | 0.016 [0.003, 0.031] | 0.000 [0.000, 0.000] | n/a |
| Mean cost per case | $0.000000 per case | $0.001015 per case | $0.003785 per case | $0.005875 per case | $0.002849 per case | $0.000000 per case |


**Where each column comes from**

| Variant | Run folder | Prompt version | Note |
|---|---|---|---|
| rules | `20261029-185354_rules_test` | v2 | No model, so the prompt version does not apply. |
| diagnose | `20261030-025036_diagnose_test` | v4 | Final prompt version. |
| agent | `20261030-032358_agent_test` | v4 | Final prompt version. |
| agent_write | `20261030-071251_agent_write_test` | v4 | Final prompt version. |
| llm_only | `20261030-072406_llm_only_test` | v4 | Final prompt version. |
| baseline | `20261029-195105_baseline_test` | v3 | No model, so the prompt version does not apply. |
