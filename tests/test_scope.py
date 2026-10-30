"""Tests for component 2, the scope guard: only issued and stopped cases get through."""

from officer.intake import store
from officer.scope import guard


def test_in_scope_states_get_through():
    case = store.load_case("PRB-0001")
    for state in ("issued", "stopped"):
        assert guard.in_scope(case.model_copy(update={"state": state})) is True


def test_every_other_state_is_refused():
    case = store.load_case("PRB-0001")
    for state in ("ready_for_examiner", "escalated", "examining", "granted"):
        assert guard.in_scope(case.model_copy(update={"state": state})) is False


def test_refusal_is_high_confidence_and_cites_nothing():
    refusal = guard.refusal("PRB-0001", "granted")
    assert refusal.next_action == "refuse_out_of_scope"
    assert refusal.confidence == "high"
    assert refusal.stop_reasons == [] and refusal.rules_cited == []
    assert "granted" in refusal.summary
