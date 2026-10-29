"""Tests for officer/diagnose.py: the scope guard, parsing, safe fallbacks and the rules-only baseline.

No test calls the API. The fake LLM supplies every model response.
"""

from officer import diagnose, llm, store

VALID_OUTPUT = {
    "summary": "The death certificate is missing. The applicant must supply it.",
    "stop_reasons": ["DEATH_CERT_MISSING"],
    "rules_cited": ["R-DOC-01"],
    "next_action": "stop_case",
    "confidence": "high",
}


def _set_state(case_id, state):
    # Write a case with a different state into the temporary data folder.
    case = store.load_case(case_id)
    store.save_case(case.model_copy(update={"state": state}))


def test_scope_guard_refuses_without_any_model_call(tmp_data, fake_llm):
    _set_state("PRB-0001", "granted")
    result = diagnose.diagnose("PRB-0001")
    assert result.next_action == "refuse_out_of_scope"
    assert result.confidence == "high"
    assert fake_llm.calls == []
    assert llm.USAGE["calls"] == 0


def test_valid_tool_output_becomes_a_diagnosis(tmp_data, fake_llm):
    fake_llm.queue(fake_llm.tool_response(VALID_OUTPUT))
    result = diagnose.diagnose("PRB-0002")
    assert result.case_id == "PRB-0002"
    assert result.next_action == "stop_case"
    assert result.stop_reasons == ["DEATH_CERT_MISSING"]
    assert result.rules_cited == ["R-DOC-01"]


def test_model_call_forces_the_submit_tool_and_sends_case_as_tagged_evidence(tmp_data, fake_llm):
    fake_llm.queue(fake_llm.tool_response(VALID_OUTPUT))
    diagnose.diagnose("PRB-0002")
    sent = fake_llm.calls[0]
    assert sent["tool_choice"] == {"type": "tool", "name": "submit_diagnosis"}
    assert sent["tools"][0]["name"] == "submit_diagnosis"
    content = sent["messages"][0]["content"]
    assert "<case>" in content and "<failed_rules>" in content and "<judgement_rules>" in content
    assert "R-DOC-01" in content


def test_bad_tool_output_becomes_a_safe_escalation(tmp_data, fake_llm):
    bad = dict(VALID_OUTPUT, next_action="frozen")  # not an allowed action
    fake_llm.queue(fake_llm.tool_response(bad))
    result = diagnose.diagnose("PRB-0002")
    assert result.next_action == "escalate"
    assert result.confidence == "low"
    assert "did not validate" in result.summary


def test_missing_tool_call_becomes_a_safe_escalation(tmp_data, fake_llm):
    fake_llm.queue(fake_llm.text_response("I think the case should be stopped."))
    result = diagnose.diagnose("PRB-0002")
    assert result.next_action == "escalate"
    assert result.confidence == "low"
    assert "did not call submit_diagnosis" in result.summary


def test_model_cannot_produce_a_refusal(tmp_data, fake_llm):
    # The schema hides this value, but the code must still reject it if it arrives.
    fake_llm.queue(fake_llm.tool_response(dict(VALID_OUTPUT, next_action="refuse_out_of_scope")))
    result = diagnose.diagnose("PRB-0002")
    assert result.next_action == "escalate"
    assert "only the code may do" in result.summary


def test_rules_only_routes_a_clean_case_to_examiner(tmp_data):
    result = diagnose.rules_only("PRB-0001")
    assert result.next_action == "route_to_examiner"
    assert result.rules_cited == []


def test_rules_only_stops_a_case_with_a_missing_document(tmp_data):
    result = diagnose.rules_only("PRB-0002")
    assert result.next_action == "stop_case"
    assert result.stop_reasons == ["DEATH_CERT_MISSING"]
    assert result.rules_cited == ["R-DOC-01"]


def test_rules_only_escalates_when_a_failed_rule_says_escalate(tmp_data):
    # Domicile outside England and Wales has action "escalate", which must win over stop_case.
    case = store.load_case("PRB-0002")
    deceased = case.deceased.model_copy(update={"domicile": "Scotland"})
    store.save_case(case.model_copy(update={"deceased": deceased}))
    result = diagnose.rules_only("PRB-0002")
    assert result.next_action == "escalate"
    assert "DOMICILE_NOT_ENGLAND_WALES" in result.stop_reasons


def test_rules_only_makes_no_model_call(tmp_data, fake_llm):
    diagnose.rules_only("PRB-0002")
    assert fake_llm.calls == []
    assert llm.USAGE["calls"] == 0


def test_rules_only_refuses_out_of_scope(tmp_data):
    _set_state("PRB-0001", "examining")
    assert diagnose.rules_only("PRB-0001").next_action == "refuse_out_of_scope"
