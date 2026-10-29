"""Run every showcase scenario through rules-only and the agent, and print one table.

A one-command demo, and the backup if the live app misbehaves. Each scenario starts
from its clean copy. Proposals are listed but never approved. The table is saved to
evals/snapshot/showcase.md, which the app's Evals tab shows.

Usage: python scripts/showcase.py [--yes]
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
from evals import run_evals
from officer import agent, diagnose, llm, store

SNAPSHOT = config.ROOT / "evals" / "snapshot"


def _match(expected, diagnosis):
    return diagnosis.next_action == expected["next_action"] and set(diagnosis.stop_reasons) == set(expected["stop_reasons"])


def main(argv=None):
    parser = argparse.ArgumentParser(description="Run the showcase scenarios.")
    parser.add_argument("--yes", action="store_true", help="skip the cost-guard question")
    args = parser.parse_args(argv)

    scenarios = json.loads((config.DATA_DIR / "showcase.json").read_text(encoding="utf-8"))
    if not run_evals.confirm(len(scenarios) * run_evals.ESTIMATE_AGENT_CALLS, args.yes):
        print("Not run.")
        return 1

    lines = [
        f"Run on {datetime.now():%Y-%m-%d %H:%M}, model {config.MODEL}. Proposals are listed, never approved.",
        "",
        "| Scenario | Expected | Rules only | Agent | Agent proposals | Match | Calls | Cost |",
        "|---|---|---|---|---|---|---|---|",
    ]
    total_cost = 0.0
    matches = 0
    for scenario in scenarios:
        case_id = scenario["case_id"]
        store.reset_case(case_id)
        rules_result = diagnose.rules_only(case_id)
        llm.reset_usage()
        agent_result, gate = agent.run_case(case_id, allow_write=True)
        cost = llm.cost_usd()
        total_cost += cost
        ok = _match(scenario["expected"], agent_result)
        matches += ok
        proposals = ", ".join(p["action"] for p in gate.proposals) if gate else "none (refused in code)"
        lines.append(
            f"| {scenario['title']} | {scenario['expected']['next_action']} | {rules_result.next_action} | "
            f"{agent_result.next_action} ({', '.join(agent_result.stop_reasons) or 'none'}) | {proposals or 'none'} | "
            f"{'yes' if ok else 'NO'} | {llm.USAGE['calls']} | ${cost:.4f} |"
        )
        print(lines[-1])
    lines += ["", f"Agent matched {matches} of {len(scenarios)} scenarios. Total cost ${total_cost:.4f}."]

    SNAPSHOT.mkdir(parents=True, exist_ok=True)
    (SNAPSHOT / "showcase.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(lines[-1])
    print(f"Saved {(SNAPSHOT / 'showcase.md').relative_to(config.ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
