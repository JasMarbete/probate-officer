"""The audit trail: one JSON line per event, written to logs/trace.jsonl.

Every event carries a run_id, so one agent run can be read back as a whole.
Nothing here decides anything. It only records what happened.
"""

import json
from datetime import datetime

import config


def log(run_id, case_id, event, **data):
    """Append one event. `data` holds the event-specific fields."""
    path = config.LOG_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "run_id": run_id,
        "case_id": case_id,
        "event": event,
        **data,
    }
    # default=str turns anything JSON cannot hold, such as a date, into text rather than failing.
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, default=str) + "\n")


def _records():
    if not config.LOG_PATH.exists():
        return []
    with config.LOG_PATH.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def read_run(run_id):
    """Every event for one run, in the order they were written."""
    return [record for record in _records() if record["run_id"] == run_id]


def last_run_id():
    """The run ID of the most recent event, or None if the log is empty."""
    records = _records()
    return records[-1]["run_id"] if records else None
