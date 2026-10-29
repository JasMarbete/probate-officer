"""Tests for the judgement checks in officer/rules.py: one forced-tool call per rule, and unclear answers fail."""

from officer import rules, store


def _verdict(fake_llm, passed, reason="one sentence"):
    return fake_llm.tool_response({"passed": passed, "reason": reason}, name="record_judgement")


def test_one_call_per_applicable_judgement_rule(tmp_data, fake_llm):
    fake_llm.queue(*[_verdict(fake_llm, True) for _ in range(4)])
    findings = rules.run_judgement(store.load_case("PRB-0001"))
    assert len(fake_llm.calls) == 4
    assert all(f.passed for f in findings)


def test_judge_call_forces_the_record_tool_and_wraps_evidence(tmp_data, fake_llm):
    fake_llm.queue(*[_verdict(fake_llm, True) for _ in range(4)])
    rules.run_judgement(store.load_case("PRB-0001"))
    first = fake_llm.calls[0]
    assert first["tool_choice"] == {"type": "tool", "name": "record_judgement"}
    content = first["messages"][0]["content"]
    assert "<case_documents>" in content and "<rule>" in content


def test_a_false_verdict_becomes_a_failed_finding_with_its_stop_reason(tmp_data, fake_llm):
    fake_llm.queue(_verdict(fake_llm, False, "No witnesses are named."), *[_verdict(fake_llm, True) for _ in range(3)])
    failed = [f for f in rules.run_judgement(store.load_case("PRB-0001")) if not f.passed]
    assert [(f.rule_id, f.stop_reason, f.action) for f in failed] == [("R-WILL-05", "WILL_EXECUTION_QUERY", "escalate")]
    assert failed[0].reason == "No witnesses are named."


def test_an_unclear_verdict_does_not_pass(tmp_data, fake_llm):
    # "yes" is not the boolean True, so it must count as a fail.
    fake_llm.queue(fake_llm.tool_response({"passed": "yes", "reason": "unsure"}, name="record_judgement"),
                   *[_verdict(fake_llm, True) for _ in range(3)])
    assert rules.run_judgement(store.load_case("PRB-0001"))[0].passed is False


def test_a_missing_verdict_does_not_pass(tmp_data, fake_llm):
    fake_llm.queue(fake_llm.text_response("probably fine"), *[_verdict(fake_llm, True) for _ in range(3)])
    first = rules.run_judgement(store.load_case("PRB-0001"))[0]
    assert first.passed is False
    assert first.reason == "the judge did not return a verdict"


def test_run_all_combines_deterministic_and_judgement(tmp_data, fake_llm):
    fake_llm.queue(*[_verdict(fake_llm, True) for _ in range(4)])
    findings = rules.run_all(store.load_case("PRB-0002"))
    assert "R-DOC-01" in [f.rule_id for f in findings if not f.passed]
    assert len(findings) == len(rules.run_deterministic(store.load_case("PRB-0002"))) + 4
