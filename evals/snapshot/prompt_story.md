Each finding below was caught by a measurement, traced to a root cause, and fixed. Fixes were tuned on dev or on the showcase, never on the test split, and the test split was rerun once after each change. The earlier runs are kept in `evals/results/` for comparison.

### 1. One sentence made the agent refuse its own work (system failure)

- **Seen:** the agent scored **0.417** next-action accuracy on test (prompt v2). The failure table showed clean and missing-document cases being escalated, with "the case is issued, which is at or after examination."
- **Cause:** the spec's agent prompt said *"You cannot grant, issue, or act on anything at or after examination."* The model read the state `issued` as covered by "issue".
- **Ruled out:** the component eval had each judgement rule at 24 of 24, so the reading was fine. The fault was in the agent's prompt.
- **Fix (v3):** state the scope plainly, and use the diagnoser's outcome definitions. Tuned on dev (16 of 16).
- **Result:** test accuracy **1.000**.

### 2. Natural wording broke a judgement rule the test set said was perfect (generalisation gap)

- **Seen:** the hand-written showcase matched only **6 of 8** scenarios. A clean will was escalated for "no actual signatures, only typed names."
- **Cause:** the rule asked whether the will "shows the testator's signature." In a transcription, a signature can only appear as a typed name. The templated test wills phrase signatures in a way the judge accepted, so the test set never exposed the ambiguity.
- **Fix (v4):** the rule question now says how a signature appears in a transcription. Showcase **8 of 8**, and dev component 16 of 16 on every rule.
- **Test rerun once on v4:** component 24 of 24 on every rule, and the agent stays at 1.000.
- **Lesson:** a perfect score on templated data did not carry over to natural prose. The test set needs harder, more varied cases.

### 3. The letter grader graded at the wrong unit (grader failure)

- **Seen:** the LLM judge failed 6 letters for "not asking for every missing document." All 6 came from one case with two missing documents.
- **Cause:** the agent correctly wrote one letter per missing document, but the judge graded each letter against the full list.
- **Fix:** grade all of a run's letters together, as the applicant receives them. Result: **27 of 27** complete, nothing invented, plain English 4.96 out of 5.

### 4. "Invented citations" were not invented (metric definition)

- **Seen:** llm-only had an invented-citation rate of **0.514**.
- **Cause:** every one of the 160 off-list citations was a real rule that had passed. With no rule engine, the model checks every rule itself and cites them all. The spec's metric counted over-citing the same as hallucination.
- **Fix:** report two numbers. **Off-list citation rate** (over-citing) and **non-existent rule rate** (hallucination). llm-only hallucinated **0** rule IDs.

### 5. The intervals were too narrow (statistics)

- **Cause:** with k=3, each case's three runs are not independent, but the bootstrap resampled runs as if they were.
- **Fix:** resample whole cases. The agent v2 interval widened from [0.31, 0.53] to [0.25, 0.58].

### 6. Correct refusals were counted as unfinished runs (metric bug)

- **Seen:** completion rate 0.917.
- **Cause:** all of the missing 0.083 was out-of-scope refusals, which the code ends correctly.
- **Fix:** a scope-guard refusal now counts as completed. Completion is 1.000.

### What this says about the eval

Four of the six findings were in the **measurement**, not the system: the grader, a metric, the statistics, and the test data. An eval that only ever reports high scores is not checking much. The next investment is a harder test set: near-miss cases, varied natural wording, and injection hidden in the documents themselves.
