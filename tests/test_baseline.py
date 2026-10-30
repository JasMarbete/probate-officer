"""Tests for the PyTorch baseline: its text features, its limits, and its use of the trained model."""

import sys
from pathlib import Path

import pytest

import config
from officer.intake import store

sys.path.insert(0, str(Path(config.ROOT / "baseline")))
import train_baseline as baseline  # noqa: E402


def test_case_text_includes_documents_notes_and_key_fields():
    case = store.load_case("PRB-0002")
    text = baseline.case_text(case)
    assert "document death_certificate received False" in text
    assert "state issued" in text and "domicile England and Wales" in text


def test_predict_gives_next_action_only():
    if not baseline.MODEL_PATH.exists():
        pytest.skip("baseline not trained")
    result = baseline.predict(store.load_case("PRB-0002"))
    assert result.next_action in baseline.ACTIONS
    assert result.stop_reasons == [] and result.rules_cited == []
    assert result.confidence == "low"


def test_load_train_reads_only_the_training_folder():
    cases, actions = baseline.load_train()
    assert len(cases) == len(actions) == 300
    assert all(case.case_id.startswith("PRB-T") for case in cases)
