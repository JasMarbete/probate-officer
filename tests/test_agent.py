"""Tests for officer/agent.py: every branch of the loop, plus the audit trail.

The fake model scripts each turn. Tool calls that run judgement checks consume
their own scripted verdicts, in the order the calls happen.
"""

from types import SimpleNamespace

import config
from officer import agent, audit

PASS = {"passed": True, "reason": "evidence found"}
VALID = {
    "summary": "The death certificate is missing.",
    "stop_reasons": ["DEATH_CERT_MISSING"],
    "rules_cited": ["R-DOC-01"],
    "next_action": "stop_case",
    "confidence": "high",
}


def _tool_turn(name, tool_input, tool_id="toolu_1"):
    block = SimpleNamespace(type="tool_use", name=name, input=tool_input, id=tool_id)
    return SimpleNamespace(content=[block], stop_reason="tool_use", usage=SimpleNamespace(input_tokens=10, output_tokens=5))


def _events(run_id):
    return [record["event"] for record in audit.read_run(run_id)]


def _run_id():
    return audit.last_run_id()


def test_normal_finish_runs_tools_then_submits(tmp_data, fake_llm):
    fake_llm.queue(
        _tool_turn("get_case", {"case_id": "PRB-0002"}, "t1"),
        _tool_turn("run_rule_checks", {"case_id": "PRB-0002"}, "t2"),
        *[fake_llm.tool_response(PASS, name="record_judgement") for _ in range(4)],
        _tool_turn("submit_diagnosis", VALID, "t3"),
    )
    diagnosis, gate = agent.run_case("PRB-0002")
    assert diagnosis.next_action == "stop_case"
    assert diagnosis.stop_reasons == ["DEATH_CERT_MISSING"]
    assert gate is None
    names = _events(_run_id())
    assert names[0] == "run_start" and names[-1] == "diagnosis"
    assert names.count("tool_call") == 2 and names.count("model_turn") == 3


def test_a_text_reply_gets_one_nudge_then_the_run_continues(tmp_data, fake_llm):
    fake_llm.queue(fake_llm.text_response("I think it is stopped."), _tool_turn("submit_diagnosis", VALID))
    diagnosis, _ = agent.run_case("PRB-0002")
    assert diagnosis.next_action == "stop_case"
    assert fake_llm.calls[1]["messages"][-1] == {"role": "user", "content": agent.NUDGE}


def test_a_second_text_reply_ends_in_an_escalation(tmp_data, fake_llm):
    fake_llm.queue(fake_llm.text_response("first"), fake_llm.text_response("second"))
    diagnosis, _ = agent.run_case("PRB-0002")
    assert diagnosis.next_action == "escalate"
    assert diagnosis.confidence == "low"
    assert "error" in _events(_run_id())


def test_max_turns_cuts_the_run_off_with_an_escalation(tmp_data, fake_llm, monkeypatch):
    monkeypatch.setattr(config, "MAX_TURNS", 2)
    fake_llm.queue(_tool_turn("get_case", {"case_id": "PRB-0002"}, "a"), _tool_turn("get_case", {"case_id": "PRB-0002"}, "b"))
    diagnosis, _ = agent.run_case("PRB-0002")
    assert diagnosis.next_action == "escalate"
    assert "max_turns" in _events(_run_id())
    assert len(fake_llm.calls) == 2


def test_a_validation_error_is_fed_back_as_a_tool_error(tmp_data, fake_llm):
    bad = dict(VALID, next_action="frozen")
    fake_llm.queue(_tool_turn("submit_diagnosis", bad, "s1"), _tool_turn("submit_diagnosis", VALID, "s2"))
    diagnosis, _ = agent.run_case("PRB-0002")
    assert diagnosis.next_action == "stop_case"
    feedback = fake_llm.calls[1]["messages"][-1]["content"][0]
    assert feedback["is_error"] is True and feedback["tool_use_id"] == "s1"


def test_a_refusal_from_the_model_is_sent_back(tmp_data, fake_llm):
    fake_llm.queue(_tool_turn("submit_diagnosis", dict(VALID, next_action="refuse_out_of_scope"), "s1"),
                   _tool_turn("submit_diagnosis", VALID, "s2"))
    assert agent.run_case("PRB-0002")[0].next_action == "stop_case"
    assert "Only the code may refuse" in fake_llm.calls[1]["messages"][-1]["content"][0]["content"]


def test_out_of_scope_case_is_refused_before_any_model_call(tmp_data, fake_llm):
    from officer import store
    store.save_case(store.load_case("PRB-0001").model_copy(update={"state": "granted"}))
    diagnosis, _ = agent.run_case("PRB-0001")
    assert diagnosis.next_action == "refuse_out_of_scope"
    assert fake_llm.calls == []
    assert _events(_run_id()) == ["run_start", "refused"]


def test_every_event_carries_one_run_id(tmp_data, fake_llm):
    fake_llm.queue(_tool_turn("submit_diagnosis", VALID))
    agent.run_case("PRB-0002")
    run_id = _run_id()
    assert len(run_id) == 8 and all(c in "0123456789abcdef" for c in run_id)
    assert all(record["run_id"] == run_id for record in audit.read_run(run_id))


def test_tool_call_event_records_name_args_and_output(tmp_data, fake_llm):
    fake_llm.queue(_tool_turn("lookup_rule", {"rule_id": "R-DOC-01"}, "l1"), _tool_turn("submit_diagnosis", VALID, "s1"))
    agent.run_case("PRB-0002")
    tool_event = next(r for r in audit.read_run(_run_id()) if r["event"] == "tool_call")
    assert tool_event["name"] == "lookup_rule"
    assert tool_event["args"] == {"rule_id": "R-DOC-01"}
    assert tool_event["output"]["id"] == "R-DOC-01"


def test_audit_log_is_one_json_line_per_event(tmp_data, fake_llm):
    fake_llm.queue(_tool_turn("submit_diagnosis", VALID))
    agent.run_case("PRB-0002")
    lines = config.LOG_PATH.read_text().strip().splitlines()
    assert len(lines) == 3  # run_start, model_turn, diagnosis
    assert all(line.startswith("{") and line.endswith("}") for line in lines)
