# DESIGN

Why ProbateOfficer is built the way it is. Each point names the alternative that was rejected.

## Why a hybrid of rules and an LLM

Python checks what Python can check. The 11 example rules are plain functions over the case record: "death certificate received", "net value no more than gross", and so on. Rules are exact, cheap, repeatable and easy to test. An LLM reads free text only where a rule needs judgement, such as whether a will shows two witnesses. That split keeps the model's work small and its errors contained. The rejected alternative was an LLM that reads the whole case and decides. That is harder to test, costs more per case, and cannot be scored against a rule.

## Why seven components in one repo

The job was broken into steps first, and each step became a component with one job and a written contract. A person can be handed any one of them, and its tests and the evals show whether a change broke anything. They share one repo because they share one data contract (`officer/models.py`). Across separate repos, every change to a case or a diagnosis would need seven coordinated releases. The rejected alternative was one repo per component, which adds versioning work and no safety at this size.

## Why a hand-written loop, not an agent framework

`officer/decision/agent.py` is a plain loop: call the model, run the tool calls, feed the results back, stop at a cap. There is no LangChain, LlamaIndex, CrewAI or Autogen. The loop fits on one screen, so every line can be read and explained. The rejected alternative was a framework. It would hide the turn cap, the nudge and the validation feedback, which are the safety behaviours this project needs to show.

## Why Haiku

`claude-haiku-5-5` is the only model in the project: runtime, evals and the judge (spec Section 3). It is about a tenth of the price of the previous small model, so the eval runs stay affordable. The eval reports show its failures as well as its successes. The rejected alternative was a larger model, which would cost more per run without a clear gain on this task.

## Why the approval gate

The model proposes; a person decides. Every write tool becomes a proposal. Nothing changes a case until `Gate.decide(..., approved=True)` runs, and then only along the transitions in `ALLOWED_TRANSITIONS`. Each decision is written to `data/preferences.jsonl`, so the owner's choices can be learned from later. The rejected alternative was to let the model write directly. A wrong write would then change a case with no record of why.

## Why the golden set is generated

The 40 golden cases come from one fault list, and their labels come from the rules file. That makes the labels correct by construction, and the script checks them against the rules engine. The rejected alternative was to write expected answers by hand, which goes wrong quietly. The cost is a known limit: the generator and the checks share the same rules, so the eval measures consistency with the rules, not real-world accuracy.

## Why the evals report intervals and failures

Every rate has a 95% bootstrap interval, and every run's failures are listed, not just the score. With 24 test cases the intervals are wide, and the report says so. The rejected alternative was a single headline number, which hides both the uncertainty and the failures.

## Limits this design accepts

- The rules are EXAMPLE rules until the shelf data is in.
- All data is synthetic.
- The baseline sees only text and predicts only the next action.
- The judge needs the owner's hand scores before its agreement can be reported.
