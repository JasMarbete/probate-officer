"""Tests for officer/tools.py: READ tool results, errors as data, the registry and the write-gate rule."""

from officer import tools

PASS = {"passed": True, "reason": "evidence found"}


def test_get_case_returns_the_case_as_a_dict(tmp_data):
    result = tools.execute("get_case", {"case_id": "PRB-0001"})
    assert result["case_id"] == "PRB-0001"


def test_get_case_missing_returns_an_error_not_an_exception(tmp_data):
    assert "no case PRB-9999" in tools.execute("get_case", {"case_id": "PRB-9999"})["error"]


def test_run_rule_checks_returns_failed_rules_only(tmp_data, fake_llm):
    # PRB-0002 fails one deterministic rule. Its four judgement rules are checked by the (fake) judge.
    fake_llm.queue(*[fake_llm.tool_response(PASS, name="record_judgement") for _ in range(4)])
    failed = tools.execute("run_rule_checks", {"case_id": "PRB-0002"})
    assert [f["rule_id"] for f in failed] == ["R-DOC-01"]
    assert all(f["passed"] is False for f in failed)


def test_lookup_rule_found_and_missing(tmp_data):
    assert tools.execute("lookup_rule", {"rule_id": "R-DOC-01"})["name"] == "Death certificate received"
    assert tools.execute("lookup_rule", {"rule_id": "R-FAKE-99"}) == {"error": "no rule R-FAKE-99"}


def test_get_template_is_missing_until_m6(tmp_data):
    assert tools.execute("get_template", {"template_id": "req_original_will"}) == {"error": "no template req_original_will"}


def test_bad_arguments_come_back_as_an_error(tmp_data):
    assert "error" in tools.execute("get_case", {"wrong_arg": "x"})


def test_unknown_tool_is_an_error(tmp_data):
    assert tools.execute("delete_everything", {}) == {"error": "unknown tool delete_everything"}


def test_final_tool_is_not_executed_here(tmp_data):
    assert "agent loop" in tools.execute("submit_diagnosis", {})["error"]


def test_schemas_list_the_read_tools_and_submit():
    names = [schema["name"] for schema in tools.schemas(include_write=False)]
    assert names == ["get_case", "run_rule_checks", "lookup_rule", "get_template", "submit_diagnosis"]


def test_submit_schema_does_not_offer_refusal():
    enum = tools.SUBMIT_DIAGNOSIS_TOOL["input_schema"]["properties"]["next_action"]["enum"]
    assert "refuse_out_of_scope" not in enum


def test_write_tools_are_hidden_unless_asked_for(monkeypatch):
    write = {"fn": None, "kind": "WRITE", "description": "propose", "schema": {"type": "object"}}
    monkeypatch.setitem(tools.TOOLS, "stop_case", write)
    assert "stop_case" not in [s["name"] for s in tools.schemas(include_write=False)]
    assert "stop_case" in [s["name"] for s in tools.schemas(include_write=True)]


def test_write_tool_without_a_gate_is_an_error(monkeypatch):
    monkeypatch.setitem(tools.TOOLS, "stop_case", {"fn": None, "kind": "WRITE", "description": "", "schema": {}})
    assert "needs an approval gate" in tools.execute("stop_case", {}, gate=None)["error"]


def test_write_tool_goes_only_to_the_gate(monkeypatch):
    class FakeGate:
        def __init__(self):
            self.proposed = []

        def propose(self, action, args):
            self.proposed.append((action, args))
            return {"status": "proposed"}

    monkeypatch.setitem(tools.TOOLS, "stop_case", {"fn": None, "kind": "WRITE", "description": "", "schema": {}})
    gate = FakeGate()
    assert tools.execute("stop_case", {"case_id": "PRB-0001"}, gate=gate) == {"status": "proposed"}
    assert gate.proposed == [("stop_case", {"case_id": "PRB-0001"})]
