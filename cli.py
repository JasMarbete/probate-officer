"""Command-line entry point: diagnose one case and print the result and its cost.

Usage: python cli.py <case_id> [--mode diagnose|rules|agent]

`diagnose` (the default) makes one model call. `rules` makes none. `agent`
arrives in Milestone 5.
"""

import argparse
import sys

from dotenv import load_dotenv

import config
from officer import diagnose, llm

# Read ANTHROPIC_API_KEY from .env before any model call. Without this, the key is only found if exported in the shell.
load_dotenv(config.ROOT / ".env")


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

    if args.mode == "agent":
        print("Agent mode arrives in Milestone 5.")
        return 2

    llm.reset_usage()
    try:
        if args.mode == "diagnose":
            diagnosis = diagnose.diagnose(args.case_id)
        else:
            diagnosis = diagnose.rules_only(args.case_id)
    except (FileNotFoundError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    _print_diagnosis(diagnosis)
    _print_cost()
    return 0


if __name__ == "__main__":
    sys.exit(main())
