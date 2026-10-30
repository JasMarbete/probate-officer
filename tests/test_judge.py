"""Tests for evals/judge.py (scoring and calibration), evals/component.py (per-rule accuracy), and the llm-only agent."""

import json
from types import SimpleNamespace

import config
from evals import component, judge
from officer import agent


def _score_tool(score):
    block = SimpleNamespace(type="tool_use", name="record_letter_score", id="j1", input=score)
    return SimpleNamespace(content=[block], stop_reason="tool_use", usage=SimpleNamespace(input_tokens=1, output_tokens=1))


def test_judge_letter_returns_the_recorded_score(fake_llm):
    fake_llm.queue(_score_tool({"correct_documents": True, "nothing_invented": True, "plain_english": 4}))
    score = judge.judge_letter("Please send the certificate.", ["death certificate"])
    assert score == {"correct_documents": True, "nothing_invented": True, "plain_english": 4}
    assert fake_llm.calls[0]["tool_choice"] == {"type": "tool", "name": "record_letter_score"}


def test_judge_clips_the_scale_to_one_to_five(fake_llm):
    fake_llm.queue(_score_tool({"correct_documents": True, "nothing_invented": True, "plain_english": 9}))
    assert judge.judge_letter("x", [])["plain_english"] == 5


def test_judge_with_no_score_says_so(fake_llm):
    fake_llm.queue(fake_llm.text_response("looks fine"))
    assert judge.judge_letter("x", []) == {"error": "the judge did not return a score"}


def test_calibration_reports_none_without_the_owner_file(tmp_path):
    assert judge.calibrate({}, human_path=tmp_path / "missing.jsonl") is None


def test_calibration_compares_bools_exactly_and_scale_within_one(tmp_path):
    human = tmp_path / "human.jsonl"
    human.write_text("\n".join([
        json.dumps({"letter_id": "a", "correct_documents": True, "nothing_invented": True, "plain_english": 4}),
        json.dumps({"letter_id": "b", "correct_documents": True, "nothing_invented": False, "plain_english": 2}),
    ]))
    judge_scores = {
        "a": {"correct_documents": True, "nothing_invented": True, "plain_english": 5},
        "b": {"correct_documents": True, "nothing_invented": True, "plain_english": 2},
    }
    result = judge.calibrate(judge_scores, human_path=human)
    assert result["compared"] == 2
    assert result["bool_agreement"] == 0.75  # three of four bool checks agree
    assert result["scale_agreement_within_1"] == 1.0


def test_component_accuracy_counts_correct_rules(tmp_data):
    rows = [
        {"rule_id": "R-WILL-05", "correct": True},
        {"rule_id": "R-WILL-05", "correct": False},
        {"rule_id": "R-NAME-01", "correct": True},
    ]
    assert component.accuracy_by_rule(rows) == {"R-NAME-01": (1, 1), "R-WILL-05": (1, 2)}


def test_llm_only_hides_the_rule_check_tool_and_pastes_the_rules(tmp_data, fake_llm):
    fake_llm.queue(fake_llm.text_response("stop"), fake_llm.text_response("stop again"))
    agent.run_case("PRB-0002", llm_only=True)
    offered = [tool["name"] for tool in fake_llm.calls[0]["tools"]]
    assert "run_rule_checks" not in offered and "get_case" in offered
    intro = fake_llm.calls[0]["messages"][0]["content"]
    assert "<rules>" in intro and "R-DOC-01" in intro


def test_export_writes_each_runs_letters_with_the_missing_list_and_a_score_line(tmp_path):
    rows = [{"case_id": "PRB-G013", "run": 2, "letters": [{"id": "PRB-G013_0", "text": "Please send the certificate.", "missing": ["death certificate"]}]}]
    out = tmp_path / "letters.md"
    assert judge.export_letters(rows, out) == 1
    text = out.read_text()
    assert "## PRB-G013_run2" in text and "Missing documents: death certificate" in text
    assert '"letter_id": "PRB-G013_run2"' in text and '"plain_english": null' in text


def test_letters_from_one_run_are_graded_together():
    # Two missing documents, one letter each: the applicant gets both, so the judge sees both.
    rows = [{"case_id": "PRB-G027", "run": 1, "letters": [
        {"id": "PRB-G027_0", "text": "Send the death certificate.", "missing": ["death certificate", "original will"]},
        {"id": "PRB-G027_1", "text": "Send the original will.", "missing": ["death certificate", "original will"]},
    ]}]
    [(key, text, missing)] = judge.correspondence(rows)
    assert key == "PRB-G027_run1"
    assert "death certificate" in text and "original will" in text


def test_runs_of_the_same_case_get_different_keys():
    rows = [{"case_id": "PRB-G016", "run": r, "letters": [{"id": "PRB-G016_0", "text": "x", "missing": []}]} for r in (1, 2)]
    assert len({key for key, _, _ in judge.correspondence(rows)}) == 2
