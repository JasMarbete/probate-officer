"""Command-line entry point: diagnose one case and print the result and its cost.

Usage: python cli.py <case_id> [--mode diagnose|rules|agent]

`diagnose` (the default) makes one model call. `rules` makes none. `agent`
runs the tool-calling loop and prints its trace from the audit log.
"""

import argparse
import json
import sys

from officer import audit, llm
from officer.decision import agent, diagnose


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


def _review_proposals(gate):
    """Show each proposal and ask the owner. Nothing changes until the owner says y."""
    if not gate.proposals:
        print("No proposed actions.")
        return
    print("Proposed actions:")
    for proposal in gate.proposals:
        print(f"  #{proposal['id']} {proposal['action']} {json.dumps(proposal['args'])}")
        try:
            answer = input("  approve? [y/n/skip] ").strip().lower()
        except EOFError:
            # No terminal to answer on. Leave everything pending.
            answer = "skip"
        if answer == "y":
            gate.decide(proposal["id"], True)
            print("  approved and applied")
        elif answer == "n":
            gate.decide(proposal["id"], False)
            print("  rejected")
        else:
            print("  left pending")
    print()


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
            diagnosis, gate = agent.run_case(args.case_id, allow_write=True)
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
    if args.mode == "agent" and gate is not None:
        _review_proposals(gate)
    _print_cost()
    return 0


if __name__ == "__main__":
    sys.exit(main())
