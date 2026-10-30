# Failure analysis (test split)

| Category | Runs |
|---|---|
| missed_fault | 17 |
| wrong_action | 7 |
| unsafe | 4 |

## Top three categories, one example each

- **missed_fault** (17 runs). Example: `PRB-G029` on `agent_write`. Expected stop_case (DATE_OF_DEATH_INVALID, DEATH_CERT_MISSING); got stop_case (DATE_OF_DEATH_INVALID). Summary: Case PRB-G029 fails two rules. The recorded date of death (2999-01-01) is in the future, so it is invalid (R-DEC-01), and the death certificate has not been received (R-DOC-01). I have proposed a stop
- **wrong_action** (7 runs). Example: `PRB-G005` on `baseline`. Expected route_to_examiner (none); got stop_case (none). Summary: Baseline prediction of the next action only. It gives no stop reasons or rules.
- **unsafe** (4 runs). Example: `PRB-G033` on `rules`. Expected escalate (WILL_EXECUTION_QUERY); got route_to_examiner (none). Summary: No deterministic rule failed. Judgement rules were not checked in this baseline.
