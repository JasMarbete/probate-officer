"""Command-line entry point: diagnose one case and print the result and its cost.

Usage: python cli.py <case_id> [--mode diagnose|rules|agent]

`diagnose` (the default) makes one model call. `rules` makes none. `agent`
runs the tool-calling loop and prints its trace from the audit log.
"""

import argparse
import json
import sys

from officer import agent, audit, diagnose, llm


def _print_trace(run_id):
    # One line per audit event, so the owner can follow what the agent did.
    for record in audit.read_run(run_id):
        detail = ""
        if record["event"] == "tool_call":
            detail = f"{record['name']} {json.dumps(record['args'])} -> {json.dumps(record['output'], default=str)[:120]}"
        elif record["event"] == "model_turn":
            detail = f"stop_reason={record['stop_reason']} tokens={record['input_tokens']}/{record['output_tokens']}"
        print(f"  [{record['event']}] {detail}".rstrip())
    print()


def _print_diagnosis(diagnosis):
    print(f"Case:        {diagnosis.case_id}")
    print(f"Next action: {diagnosis.next_action}")
    print(f"Confidence:  {diagnosis.confidence}")
    print(f"Stop reasons: {', '.join(diagnosis.stop_reasons) or 'none'}")
    print(f"Rules cited:  {', '.join(diagnosis.rules_cited) or 'none'}")
    print(f"Summary:     {diagnosis.summary}")


def _print_cost():
    print(
        f"Usage: {llm.USAGE['calls']} call(s), "
        f"{llm.USAGE['input_tokens']} input tokens, {llm.USAGE['output_tokens']} output tokens, "
        f"cost ${llm.cost_usd():.6f}"
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description="Diagnose one probate case.")
    parser.add_argument("case_id")
    parser.add_argument("--mode", choices=["diagnose", "rules", "agent"], default="diagnose")
    args = parser.parse_args(argv)

    llm.reset_usage()
    try:
        if args.mode == "agent":
            diagnosis, _ = agent.run_case(args.case_id)
        elif args.mode == "diagnose":
            diagnosis = diagnose.diagnose(args.case_id)
        else:
            diagnosis = diagnose.rules_only(args.case_id)
    except (FileNotFoundError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    if args.mode == "agent":
        _print_trace(audit.last_run_id())
    _print_diagnosis(diagnosis)
    _print_cost()
    return 0


if __name__ == "__main__":
    sys.exit(main())
