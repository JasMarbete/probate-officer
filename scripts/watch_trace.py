"""Watch the agent live: print each audit event from logs/trace.jsonl as a readable line.

Read-only. It never writes to the log or the cases, so it is safe to run while
evals or the demo are running.

Usage:
  python scripts/watch_trace.py            follow new events as they happen (Ctrl+C to stop)
  python scripts/watch_trace.py --last 40  print the last 40 events, then follow
  python scripts/watch_trace.py --once     print the last events and exit
"""

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config


def describe(record):
    """One plain-English line for one audit event."""
    event = record["event"]
    head = f"{record['ts'][11:]}  {record['run_id']}  {record['case_id']:<9}"
    if event == "run_start":
        return f"{head}  ── run started"
    if event == "refused":
        return f"{head}  ✋ refused by the scope guard (state {record.get('state')}), no model call"
    if event == "model_turn":
        return f"{head}  🤖 model turn ({record['input_tokens']} in / {record['output_tokens']} out, {record['stop_reason']})"
    if event == "tool_call":
        output = record["output"]
        if isinstance(output, list):
            found = ", ".join(f.get("stop_reason") or f.get("rule_id") for f in output) or "nothing failed"
            result = f"failed rules: {found}"
        elif isinstance(output, dict) and "error" in output:
            result = f"error: {output['error']}"
        else:
            result = "ok"
        return f"{head}  🔧 {record['name']}({json.dumps(record['args'])[:60]}) → {result}"
    if event == "proposal":
        return f"{head}  📝 proposes {record['action']} (#{record['proposal_id']}), waiting for a person"
    if event == "human_decision":
        verdict = "approved" if record["approved"] else "rejected"
        return f"{head}  👤 person {verdict} proposal #{record['proposal_id']}"
    if event == "diagnosis":
        reasons = ", ".join(record.get("stop_reasons", [])) or "none"
        return f"{head}  ✅ diagnosis: {record['next_action']} ({reasons}), confidence {record['confidence']}"
    if event == "max_turns":
        return f"{head}  ⛔ hit the turn limit, escalated"
    if event == "error":
        return f"{head}  ⚠️  {record.get('reason', 'error')}"
    return f"{head}  {event}"


def main(argv=None):
    parser = argparse.ArgumentParser(description="Follow the agent's audit trail live.")
    parser.add_argument("--last", type=int, default=20, help="how many recent events to show first")
    parser.add_argument("--once", action="store_true", help="show the recent events and exit")
    args = parser.parse_args(argv)

    path = config.LOG_PATH
    while not path.exists():
        print("waiting for logs/trace.jsonl ...")
        time.sleep(1)

    with path.open(encoding="utf-8") as handle:
        lines = handle.readlines()
        for line in lines[-args.last:]:
            if line.strip():
                print(describe(json.loads(line)))
        if args.once:
            return 0
        # Follow the file like `tail -f`: read new lines as they are appended.
        while True:
            line = handle.readline()
            if not line:
                time.sleep(0.5)
                continue
            if line.strip():
                print(describe(json.loads(line)), flush=True)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        pass
