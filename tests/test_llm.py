"""Tests for officer/llm.py that need no network: the missing-key message and the cost maths."""

import pytest

import config
from officer import llm


def test_missing_key_gives_a_clear_message(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr(llm, "_client", None)
    with pytest.raises(RuntimeError, match="No ANTHROPIC_API_KEY is set"):
        llm._get_client()


def test_cost_uses_the_configured_prices(monkeypatch):
    monkeypatch.setattr(config, "PRICE_IN_PER_M", 0.10)
    monkeypatch.setattr(config, "PRICE_OUT_PER_M", 0.50)
    usage = {"input_tokens": 1_000_000, "output_tokens": 2_000_000, "calls": 1}
    assert llm.cost_usd(usage) == pytest.approx(0.10 + 1.00)
