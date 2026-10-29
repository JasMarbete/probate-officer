"""Tests for officer/store.py: loading, saving, listing and resetting case files.

Tests write only to a temporary folder. The one test that reads the real
data/cases/ folder is read-only, and it checks the three hand-written cases.
"""

import json

import pytest

import config
from officer import store
from officer.models import Case


def _valid_case_dict(case_id="PRB-9001"):
    # A minimal valid case, built fresh each time so tests cannot share state.
    return {
        "case_id": case_id,
        "state": "issued",
        "application_type": "probate_will",
        "applicant": {"name": "Test Person A", "role": "executor", "address_given": True},
        "deceased": {"name": "Test Person B", "date_of_death": "2026-04-14", "domicile": "England and Wales"},
        "estate": {"gross_value": 1000, "net_value": 900, "iht_route": "excepted"},
        "documents": [{"type": "death_certificate", "received": True, "original": None, "text": None}],
        "notes": [],
    }


def test_three_hand_written_cases_load():
    # Read-only check on the real data: the M1 acceptance criteria.
    for case_id in ["PRB-0001", "PRB-0002", "PRB-0003"]:
        assert store.load_case(case_id).case_id == case_id


def test_malformed_case_raises_clear_error(tmp_path):
    bad = _valid_case_dict("PRB-9002")
    bad["state"] = "frozen"  # not one of the allowed states
    (tmp_path / "PRB-9002.json").write_text(json.dumps(bad))
    with pytest.raises(ValueError, match="case PRB-9002 is invalid"):
        store.load_case("PRB-9002", directory=tmp_path)


def test_missing_case_raises_file_not_found(tmp_path):
    with pytest.raises(FileNotFoundError, match="no case PRB-9999"):
        store.load_case("PRB-9999", directory=tmp_path)


def test_save_then_load_round_trip(tmp_path):
    case = Case.model_validate(_valid_case_dict("PRB-9003"))
    store.save_case(case, directory=tmp_path)
    assert store.load_case("PRB-9003", directory=tmp_path) == case


def test_list_cases_is_sorted(tmp_path):
    for case_id in ["PRB-9010", "PRB-9005", "PRB-9007"]:
        store.save_case(Case.model_validate(_valid_case_dict(case_id)), directory=tmp_path)
    assert store.list_cases(directory=tmp_path) == ["PRB-9005", "PRB-9007", "PRB-9010"]


def test_reset_case_copies_golden_over_working_copy(tmp_path, monkeypatch):
    golden = tmp_path / "golden"
    working = tmp_path / "cases"
    monkeypatch.setattr(config, "GOLDEN_DIR", golden)
    monkeypatch.setattr(config, "CASES_DIR", working)

    store.save_case(Case.model_validate(_valid_case_dict("PRB-9004")), directory=golden)
    # A working copy that has drifted from the golden version.
    store.save_case(Case.model_validate(_valid_case_dict("PRB-9004") | {"state": "stopped"}), directory=working)

    store.reset_case("PRB-9004")
    assert store.load_case("PRB-9004", directory=working).state == "issued"


def test_reset_case_missing_golden_raises(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "GOLDEN_DIR", tmp_path / "golden")
    monkeypatch.setattr(config, "CASES_DIR", tmp_path / "cases")
    with pytest.raises(FileNotFoundError, match="no case PRB-9999"):
        store.reset_case("PRB-9999")
