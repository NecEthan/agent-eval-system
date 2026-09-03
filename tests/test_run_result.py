"""Tests for RunResult."""

import pytest
from eval.run_result import RunResult


def test_completed_status():
    result = RunResult(status="completed", duration=1.5, logs=[], error=None)
    assert result.status == "completed"
    assert result.error is None


def test_failed_status_has_error():
    result = RunResult(status="failed", duration=2.0, logs=[], error="agent crashed")
    assert result.status == "failed"
    assert result.error == "agent crashed"


def test_timeout_status():
    result = RunResult(status="timeout", duration=300.0, logs=[], error=None)
    assert result.status == "timeout"
    assert result.error is None


def test_logs_preserved():
    logs = [{"type": "AgentStarted", "task": "fix the bug"}]
    result = RunResult(status="completed", duration=1.0, logs=logs, error=None)
    assert result.logs == logs


def test_is_immutable():
    result = RunResult(status="completed", duration=1.0, logs=[], error=None)
    with pytest.raises(Exception):
        result.status = "failed"  # type: ignore[misc]
