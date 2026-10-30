"""Tests for component 7, the audit trail: one JSON line per event, read back by run_id."""

import json

import config
from officer import audit


def test_log_appends_one_json_line_with_the_standard_fields(tmp_data):
    audit.log("run00001", "PRB-0001", "run_start")
    record = json.loads(config.LOG_PATH.read_text().splitlines()[-1])
    assert {k: record[k] for k in ("run_id", "case_id", "event")} == {"run_id": "run00001", "case_id": "PRB-0001", "event": "run_start"}
    assert "ts" in record


def test_event_specific_fields_are_kept(tmp_data):
    audit.log("run00001", "PRB-0001", "tool_call", name="get_case", args={"case_id": "PRB-0001"}, output={"ok": True})
    record = audit.read_run("run00001")[-1]
    assert record["name"] == "get_case" and record["output"] == {"ok": True}


def test_read_run_returns_only_that_run_in_order(tmp_data):
    audit.log("aaaa0001", "PRB-0001", "run_start")
    audit.log("bbbb0002", "PRB-0002", "run_start")
    audit.log("aaaa0001", "PRB-0001", "diagnosis")
    assert [r["event"] for r in audit.read_run("aaaa0001")] == ["run_start", "diagnosis"]
    assert audit.last_run_id() == "aaaa0001"


def test_empty_log_has_no_last_run(tmp_data):
    assert audit.last_run_id() is None
