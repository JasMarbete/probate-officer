"""Shared test fixtures: a fake model and a temporary copy of the data folder.

Tests never call the real API. The `fake_llm` fixture replaces `officer.llm.call`
with a function that returns scripted responses in order. `tmp_data` points every
config path at a temporary copy, so tests never write to real files.
"""

import shutil
from types import SimpleNamespace

import pytest

import config
from officer import llm


class FakeLLM:
    """Stands in for officer.llm.call. Responses are queued, then returned in order."""

    def __init__(self):
        self.responses = []
        self.calls = []

    def queue(self, *responses):
        self.responses.extend(responses)

    @staticmethod
    def tool_response(tool_input, name="submit_diagnosis"):
        # One assistant turn that calls a tool. The shape matches the SDK response fields we read.
        block = SimpleNamespace(type="tool_use", name=name, input=tool_input, id="toolu_test")
        return SimpleNamespace(
            content=[block],
            stop_reason="tool_use",
            usage=SimpleNamespace(input_tokens=10, output_tokens=5),
        )

    @staticmethod
    def text_response(text):
        # One assistant turn that is plain text, with no tool call.
        return SimpleNamespace(
            content=[SimpleNamespace(type="text", text=text)],
            stop_reason="end_turn",
            usage=SimpleNamespace(input_tokens=10, output_tokens=5),
        )

    def __call__(self, system, messages, tools=None, tool_choice=None):
        # Record every call, so tests can check what was sent.
        self.calls.append({"system": system, "messages": messages, "tools": tools, "tool_choice": tool_choice})
        if not self.responses:
            raise AssertionError("fake LLM has no scripted response left")
        return self.responses.pop(0)


@pytest.fixture
def fake_llm(monkeypatch):
    fake = FakeLLM()
    monkeypatch.setattr(llm, "call", fake)
    llm.reset_usage()
    return fake


@pytest.fixture
def tmp_data(tmp_path, monkeypatch):
    """A temporary copy of data/ with every config path pointed into it."""
    root = tmp_path / "data"
    # Copy the rules, cases and golden set. Skip the owner's shelf material and the runtime output.
    shutil.copytree(
        config.DATA_DIR,
        root,
        ignore=shutil.ignore_patterns("shelf", "outbox", "*.jsonl", ".DS_Store"),
    )
    monkeypatch.setattr(config, "DATA_DIR", root)
    monkeypatch.setattr(config, "CASES_DIR", root / "cases")
    monkeypatch.setattr(config, "GOLDEN_DIR", root / "golden")
    monkeypatch.setattr(config, "RULES_PATH", root / "rules.yaml")
    monkeypatch.setattr(config, "TEMPLATES_DIR", root / "templates")
    monkeypatch.setattr(config, "OUTBOX_DIR", root / "outbox")
    monkeypatch.setattr(config, "PREFS_PATH", root / "preferences.jsonl")
    monkeypatch.setattr(config, "LOG_PATH", tmp_path / "logs" / "trace.jsonl")
    monkeypatch.setattr(config, "RESULTS_DIR", tmp_path / "results")
    llm.reset_usage()
    return root
