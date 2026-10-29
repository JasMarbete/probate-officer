"""Tests for officer/gate.py and the write path: a proposal changes nothing, only approval applies, and every decision is logged."""

import json
from types import SimpleNamespace

import pytest

import config
from officer import agent, gate as gate_module, store
from officer.gate import Gate


def _gate(case_id="PRB-0002"):
    return Gate(case_id, run_id="test0001")


def _case_text(case_id):
    return config.CASES_DIR.joinpath(f"{case_id}.json").read_text()


def test_a_proposal_changes_nothing(tmp_data):
    before = _case_text("PRB-0002")
    gate = _gate()
    gate.propose("stop_case", {"case_id": "PRB-0002", "stop_reasons": ["DEATH_CERT_MISSING"], "note": "Please send it."})
    assert _case_text("PRB-0002") == before
    assert gate.proposals[0]["status"] == "pending"


def test_approval_changes_the_state_and_adds_the_note(tmp_data):
    gate = _gate()
    gate.propose("stop_case", {"case_id": "PRB-0002", "stop_reasons": ["DEATH_CERT_MISSING"], "note": "Please send it."})
    gate.decide(0, approved=True)
    case = store.load_case("PRB-0002")
    assert case.state == "stopped"
    assert case.notes[-1].startswith("Please send it.")
    assert "DEATH_CERT_MISSING" in case.notes[-1]


def test_rejection_changes_nothing(tmp_data):
    before = _case_text("PRB-0002")
    gate = _gate()
    gate.propose("stop_case", {"case_id": "PRB-0002", "stop_reasons": ["DEATH_CERT_MISSING"], "note": "x"})
    gate.decide(0, approved=False)
    assert _case_text("PRB-0002") == before
    assert gate.proposals[0]["status"] == "rejected"


def test_an_illegal_transition_raises_and_changes_nothing(tmp_data):
    case = store.load_case("PRB-0002")
    store.save_case(case.model_copy(update={"state": "escalated"}))
    before = _case_text("PRB-0002")
    gate = _gate()
    gate.propose("stop_case", {"case_id": "PRB-0002", "stop_reasons": [], "note": "x"})
    with pytest.raises(ValueError, match="cannot move case PRB-0002 from escalated to stopped"):
        gate.decide(0, approved=True)
    assert _case_text("PRB-0002") == before


def test_every_decision_writes_a_preference_line(tmp_data):
    gate = _gate()
    gate.propose("stop_case", {"case_id": "PRB-0002", "stop_reasons": [], "note": "x"})
    gate.decide(0, approved=False, note="too early")
    line = json.loads(config.PREFS_PATH.read_text().strip().splitlines()[-1])
    assert line["case_id"] == "PRB-0002" and line["approved"] is False and line["note"] == "too early"


def test_a_proposal_can_be_decided_only_once(tmp_data):
    gate = _gate()
    gate.propose("stop_case", {"case_id": "PRB-0002", "stop_reasons": [], "note": "x"})
    gate.decide(0, approved=False)
    with pytest.raises(ValueError, match="already rejected"):
        gate.decide(0, approved=True)


def test_an_approved_request_document_writes_the_letter_to_the_outbox(tmp_data):
    gate = _gate()
    gate.propose("request_document", {"case_id": "PRB-0002", "template_id": "req_death_certificate", "letter_text": "Please send the certificate."})
    gate.decide(0, approved=True)
    letter = config.OUTBOX_DIR / "PRB-0002_0.txt"
    assert letter.read_text() == "Please send the certificate."
    assert store.load_case("PRB-0002").state == "issued"  # a letter does not change the state


def test_add_case_note_is_applied_without_a_state_change(tmp_data):
    gate = _gate()
    gate.propose("add_case_note", {"case_id": "PRB-0002", "note": "Applicant called."})
    gate.decide(0, approved=True)
    case = store.load_case("PRB-0002")
    assert case.notes == ["Applicant called."] and case.state == "issued"


def test_route_to_examiner_moves_the_state(tmp_data):
    gate = _gate("PRB-0001")
    gate.propose("route_to_examiner", {"case_id": "PRB-0001", "note": "Clean."})
    gate.decide(0, approved=True)
    assert store.load_case("PRB-0001").state == "ready_for_examiner"


def test_agent_with_writes_allowed_proposes_and_leaves_the_case_alone(tmp_data, fake_llm):
    before = _case_text("PRB-0002")
    fake_llm.queue(
        SimpleNamespace(content=[SimpleNamespace(type="tool_use", name="stop_case", id="w1",
                                                 input={"case_id": "PRB-0002", "stop_reasons": ["DEATH_CERT_MISSING"], "note": "Send it."})],
                        stop_reason="tool_use", usage=SimpleNamespace(input_tokens=1, output_tokens=1)),
        SimpleNamespace(content=[SimpleNamespace(type="tool_use", name="submit_diagnosis", id="s1",
                                                 input={"summary": "Stop.", "stop_reasons": ["DEATH_CERT_MISSING"],
                                                        "rules_cited": ["R-DOC-01"], "next_action": "stop_case", "confidence": "high"})],
                        stop_reason="tool_use", usage=SimpleNamespace(input_tokens=1, output_tokens=1)),
    )
    diagnosis, gate = agent.run_case("PRB-0002", allow_write=True)
    assert diagnosis.next_action == "stop_case"
    assert [p["action"] for p in gate.proposals] == ["stop_case"]
    assert _case_text("PRB-0002") == before


def test_agent_without_writes_cannot_run_a_write_tool(tmp_data, fake_llm):
    fake_llm.queue(
        SimpleNamespace(content=[SimpleNamespace(type="tool_use", name="stop_case", id="w1",
                                                 input={"case_id": "PRB-0002", "stop_reasons": [], "note": "x"})],
                        stop_reason="tool_use", usage=SimpleNamespace(input_tokens=1, output_tokens=1)),
        SimpleNamespace(content=[SimpleNamespace(type="tool_use", name="submit_diagnosis", id="s1",
                                                 input={"summary": "Stop.", "stop_reasons": [], "rules_cited": [],
                                                        "next_action": "escalate", "confidence": "low"})],
                        stop_reason="tool_use", usage=SimpleNamespace(input_tokens=1, output_tokens=1)),
    )
    _, gate = agent.run_case("PRB-0002")
    assert gate is None
    assert "needs an approval gate" in fake_llm.calls[1]["messages"][-1]["content"][0]["content"]
