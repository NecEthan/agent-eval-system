"""Tests for the AgentAdapter protocol.

Uses a stub adapter to verify the contract shape and that any class
with the right run() signature satisfies the protocol without
inheriting from AgentAdapter.
"""

from pathlib import Path

from eval.adapter import AgentAdapter
from eval.run_result import RunResult


# ---------------------------------------------------------------------------
# Stub adapter — satisfies the protocol without inheriting from AgentAdapter
# ---------------------------------------------------------------------------

class StubAdapter:
    """Minimal concrete adapter for testing. Returns a fixed RunResult."""

    def __init__(self, result: RunResult) -> None:
        self._result = result

    def run(self, task: str, working_dir: Path, timeout: float) -> RunResult:
        return self._result


# ---------------------------------------------------------------------------
# Protocol conformance
# ---------------------------------------------------------------------------

def test_stub_satisfies_protocol():
    result = RunResult(status="completed", duration=1.0, logs=[], error=None)
    adapter = StubAdapter(result)
    assert isinstance(adapter, AgentAdapter)


def test_class_without_run_does_not_satisfy_protocol():
    class NotAnAdapter:
        pass

    assert not isinstance(NotAnAdapter(), AgentAdapter)


# ---------------------------------------------------------------------------
# Contract behaviour
# ---------------------------------------------------------------------------

def test_run_returns_completed():
    expected = RunResult(status="completed", duration=0.5, logs=[], error=None)
    adapter = StubAdapter(expected)
    result = adapter.run("fix the bug", Path("/tmp/work"), timeout=60.0)
    assert result.status == "completed"
    assert result.error is None


def test_run_returns_failed_with_error():
    expected = RunResult(status="failed", duration=1.0, logs=[], error="process exited with code 1")
    adapter = StubAdapter(expected)
    result = adapter.run("fix the bug", Path("/tmp/work"), timeout=60.0)
    assert result.status == "failed"
    assert result.error == "process exited with code 1"


def test_run_returns_timeout():
    expected = RunResult(status="timeout", duration=60.0, logs=[], error=None)
    adapter = StubAdapter(expected)
    result = adapter.run("fix the bug", Path("/tmp/work"), timeout=60.0)
    assert result.status == "timeout"
    assert result.error is None


def test_run_receives_correct_arguments():
    """Adapter receives exactly what the Runner will pass."""
    received: dict = {}

    class RecordingAdapter:
        def run(self, task: str, working_dir: Path, timeout: float) -> RunResult:
            received["task"] = task
            received["working_dir"] = working_dir
            received["timeout"] = timeout
            return RunResult(status="completed", duration=0.1, logs=[], error=None)

    adapter = RecordingAdapter()
    adapter.run("fix the bug", Path("/tmp/work"), timeout=120.0)

    assert received["task"] == "fix the bug"
    assert received["working_dir"] == Path("/tmp/work")
    assert received["timeout"] == 120.0
