"""Run one eval variant on one split: run each golden case k times, then write the rows and a report.

Usage:
  python -m evals.run_evals --variant diagnose|rules --split dev|test --k 3 [--yes]

Only `diagnose` and `rules` exist so far. The other variants arrive in later milestones.
Every run starts from the clean golden copy, so earlier runs cannot leak into later ones.
"""

import argparse
import json
import sys
import time
from datetime import datetime

import config
from evals import report
from officer import agent, audit, diagnose, llm, prompts, rules, store

IMPLEMENTED_VARIANTS = {"diagnose", "rules", "agent"}
# Spec Rule 8: any run with more than 10 model calls must show an estimate and ask first.
COST_GUARD_CALLS = 10
# Rough token counts for one diagnose call, from the M3 live run (about 2,000 in, 350 out). Used only for the estimate.
ESTIMATE_INPUT_TOKENS = 2000
ESTIMATE_OUTPUT_TOKENS = 350
# Rough model calls for one agent run: about 4 judgement calls plus 2 turns. Used only for the estimate.
ESTIMATE_AGENT_CALLS = 6


def cost_guard_needed(calls):
    return calls > COST_GUARD_CALLS


def estimate_cost(calls):
    return calls * (ESTIMATE_INPUT_TOKENS * config.PRICE_IN_PER_M + ESTIMATE_OUTPUT_TOKENS * config.PRICE_OUT_PER_M) / 1_000_000


def load_expected(split):
    """The golden labels for one split, read from expected.jsonl."""
    labels = []
    with (config.GOLDEN_DIR / "expected.jsonl").open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                label = json.loads(line)
                if label["split"] == split:
                    labels.append(label)
    return labels


def confirm(calls, assume_yes):
    """Print the estimate and ask before a run that goes over the guard. Returns True if the run may go ahead."""
    if not cost_guard_needed(calls):
        return True
    print(f"Cost guard: {calls} model calls, estimated cost ${estimate_cost(calls):.4f} (rough).")
    if assume_yes:
        return True
    try:
        return input("Proceed? [y/N] ").strip().lower() == "y"
    except EOFError:
        # No terminal to answer on, so do not run.
        return False


def run_case(variant, label, run_index):
    """One run of one golden case. Returns a row with the labels, the answer and the cost."""
    store.reset_case(label["case_id"])
    case = store.load_case(label["case_id"])
    # Citations are valid only if they name a failed rule or a judgement rule for this case.
    allowed = [f.rule_id for f in rules.run_deterministic(case) if not f.passed]
    allowed += [rule["id"] for rule in rules.judgement_rules_for(case)]

    llm.reset_usage()
    start = time.perf_counter()
    if variant == "diagnose":
        result = diagnose.diagnose(label["case_id"])
    elif variant == "agent":
        result, _ = agent.run_case(label["case_id"])
    else:
        result = diagnose.rules_only(label["case_id"])
    seconds = time.perf_counter() - start

    # Agent completion and tool errors come from the audit trail of this run.
    trail = audit.read_run(audit.last_run_id()) if variant == "agent" else []
    tool_events = [event for event in trail if event["event"] == "tool_call"]

    return {
        "case_id": label["case_id"],
        "run": run_index,
        "bucket": label["bucket"],
        "expected_next_action": label["next_action"],
        "got_next_action": result.next_action,
        "expected_stop_reasons": label["stop_reasons"],
        "got_stop_reasons": result.stop_reasons,
        "must_not": label["must_not"],
        "rules_cited": result.rules_cited,
        "allowed_rules": allowed,
        # Read-only agent runs make no proposals. The gate (M6) fills this in later.
        "proposal_actions": [],
        "completed": any(event["event"] == "diagnosis" for event in trail) if variant == "agent" else None,
        "tool_calls": len(tool_events),
        "tool_errors": sum(1 for event in tool_events if isinstance(event["output"], dict) and "error" in event["output"]),
        "summary": result.summary,
        "calls": llm.USAGE["calls"],
        "input_tokens": llm.USAGE["input_tokens"],
        "output_tokens": llm.USAGE["output_tokens"],
        "cost": llm.cost_usd(),
        "seconds": seconds,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Run one eval variant on one split.")
    parser.add_argument("--variant", required=True)
    parser.add_argument("--split", required=True, choices=["dev", "test"])
    parser.add_argument("--k", type=int, default=config.EVAL_K)
    parser.add_argument("--yes", action="store_true", help="skip the cost-guard question")
    args = parser.parse_args(argv)

    if args.variant not in IMPLEMENTED_VARIANTS:
        parser.error(f"variant '{args.variant}' arrives in a later milestone; available: {sorted(IMPLEMENTED_VARIANTS)}")
    # Rules are deterministic, so one run per case is enough (spec Section 9, M4).
    k = 1 if args.variant == "rules" else args.k

    labels = load_expected(args.split)
    if not labels:
        parser.error(f"no golden cases in split '{args.split}'")
    calls = {"diagnose": 1, "agent": ESTIMATE_AGENT_CALLS}.get(args.variant, 0) * len(labels) * k
    if not confirm(calls, args.yes):
        print("Not run.")
        return 1

    rows = [run_case(args.variant, label, i) for label in labels for i in range(1, k + 1)]

    folder = config.RESULTS_DIR / f"{datetime.now():%Y%m%d-%H%M%S}_{args.variant}_{args.split}"
    folder.mkdir(parents=True, exist_ok=True)
    with (folder / "rows.jsonl").open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")

    settings = {
        "variant": args.variant,
        "split": args.split,
        "k": k,
        "model": config.MODEL,
        "prompt_version": prompts.PROMPT_VERSION,
        "date": datetime.now().isoformat(timespec="seconds"),
    }
    markdown = report.build_report(rows, settings)
    (folder / "report.md").write_text(markdown, encoding="utf-8")
    print(report.metrics_section(rows))
    print(f"\nWrote {folder / 'report.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
