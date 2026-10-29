# DEMO

A run-sheet for showing ProbateOfficer live, in about 10 minutes.

## Before the call

1. Start the app and leave it open on the **Case diagnosis** tab:

   ```bash
   .venv/bin/streamlit run app.py
   ```

2. Check `.env` holds a working key: `.venv/bin/python scripts/ping.py` should print `Reply: OK`.
3. Reset the showcase cases, so earlier approvals do not show: `.venv/bin/python scripts/make_showcase.py`.
4. Have a terminal ready in the project folder as a backup (see the end of this page).
5. Each agent run takes about 10 seconds and costs under half a cent.

## The one-line pitch (30 seconds)

"ProbateOfficer is an AI employee in the seat of a probate support officer. Python checks what can be checked, the model reads only what needs judgement, every action is a proposal a person approves, and everything is evaluated against a held-out test set, with the failures shown."

## Live demo (6 minutes)

Run the scenarios in this order. Each one makes a single point.

| # | Scenario | What to point at | The point |
|---|---|---|---|
| 1 | **Will without witnesses** (`PRB-S004`) | Rules-only says `route_to_examiner`. Run the agent: it escalates with `WILL_EXECUTION_QUERY`. | Rules alone would have sent an invalid will to an examiner. The model adds the judgement the rules cannot make. |
| 2 | **Missing death certificate** (`PRB-S002`) | The agent proposes `stop_case` and a `request_document` letter. Read the letter. Approve the stop. Open the case record: the state is now `stopped`. Open the trace. | Propose, don't act. Nothing changed until the approval, and every step is in the trace under one `run_id`. |
| 3 | **Prompt injection** (`PRB-S007`) | Open the case record and show the "SYSTEM NOTE TO AI REVIEWER" line. Run the agent: it still stops the case. | Case text is evidence, never instructions. The injection cases are in the eval set too. |
| 4 | **Already granted** (`PRB-S008`) | Run the agent: refused, 0 model calls, $0. | The scope guard is code, not prompt. The model never sees out-of-scope cases. |
| 5 | **Clean case** (`PRB-S001`) | Routes to the examiner, with no stop reasons. | It does not over-escalate. That was a real bug, which brings you to the evals. |

Press **Reset case** after approving anything, so the next run starts clean.

## The evals (3 minutes)

Switch to the **Evals** tab.

1. **The ablation table.** Every variant on the same 24 held-out test cases, with 95% intervals resampled by case. Rules-only misses the judgement escalations. The single-call diagnoser and the agent both use the rules and the model. The llm-only variant shows what happens without the rule engine. The PyTorch baseline shows what text pattern-matching alone gets.
2. **What the evals caught.** The first agent prompt scored 0.417 on test. The failure table showed it escalating clean cases, and pointed at one sentence in the prompt. The component eval had already cleared the judge. The fix was made on dev only, and the test split was run once more. Both runs are kept.
3. **The honesty points.** Synthetic data. Labels come from the same rules, so this measures consistency with the rules, not real-world accuracy. Small test set, so the intervals are wide. Say these before you are asked.

## If something breaks

- **No internet or no key:** run the free parts. `cli.py PRB-S004 --mode rules` shows the rules-only gap. The **Evals** tab and `evals/snapshot/showcase.md` hold the recorded agent results.
- **The app will not start:** `.venv/bin/python scripts/showcase.py --yes` runs every scenario in the terminal and prints the same table.
- **An agent run gives an unexpected answer:** say so, open the trace, and read what it did. A live failure handled calmly is a better demo of eval thinking than a perfect run.
