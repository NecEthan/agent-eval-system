"""Tests for ResultsStore and RunRecord."""

import pytest
from pathlib import Path

from eval.evaluator import EvalResult, CommandResult
from eval.results_store import ResultsStore, RunRecord, _extract_metrics
from eval.run_result import RunResult


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def store(tmp_path):
    return ResultsStore(tmp_path / "results.jsonl")


def make_run_result(status="completed", duration=1.0, error=None, logs=None):
    return RunResult(status=status, duration=duration, logs=logs or [], error=error)


def make_eval_result(passed=True):
    cmd = CommandResult(
        command="python -m pytest",
        exit_code=0 if passed else 1,
        stdout="",
        stderr="",
        duration=0.5,
    )
    return EvalResult(passed=passed, command_results=[cmd])


SAMPLE_EVENTS = [
    {"type": "AgentStarted", "task": "fix the bug", "timestamp": 1.0},
    {"type": "TurnStarted", "turn": 1, "timestamp": 2.0},
    {"type": "ModelResponded", "turn": 1, "input_tokens": 500, "output_tokens": 100,
     "latency": 1.2, "stop_reason": "tool_use", "timestamp": 3.0, "model": "claude"},
    {"type": "ToolCalled", "turn": 1, "tool_use_id": "abc", "name": "read_file",
     "input": {"path": "stats.py"}, "timestamp": 4.0},
    {"type": "ToolResulted", "turn": 1, "tool_use_id": "abc", "name": "read_file",
     "output": "def foo(): ...", "is_error": False, "duration": 0.01, "timestamp": 5.0},
    {"type": "ModelResponded", "turn": 2, "input_tokens": 600, "output_tokens": 80,
     "latency": 0.9, "stop_reason": "end_turn", "timestamp": 6.0, "model": "claude"},
    {"type": "AgentFinished", "total_turns": 2, "final_text": "Done.", "timestamp": 7.0},
]


# ---------------------------------------------------------------------------
# _extract_metrics
# ---------------------------------------------------------------------------

def test_extract_tokens():
    metrics = _extract_metrics(SAMPLE_EVENTS)
    assert metrics["total_input_tokens"] == 1100   # 500 + 600
    assert metrics["total_output_tokens"] == 180   # 100 + 80


def test_extract_turns():
    metrics = _extract_metrics(SAMPLE_EVENTS)
    assert metrics["total_turns"] == 2


def test_extract_tool_calls():
    metrics = _extract_metrics(SAMPLE_EVENTS)
    assert len(metrics["tool_calls"]) == 1
    call = metrics["tool_calls"][0]
    assert call["name"] == "read_file"
    assert call["input"] == {"path": "stats.py"}
    assert call["is_error"] is False


def test_extract_empty_events():
    metrics = _extract_metrics([])
    assert metrics["total_input_tokens"] == 0
    assert metrics["total_output_tokens"] == 0
    assert metrics["total_turns"] == 0
    assert metrics["tool_calls"] == []


# ---------------------------------------------------------------------------
# RunRecord.create
# ---------------------------------------------------------------------------

def test_record_create_basic_fields():
    record = RunRecord.create(
        task_id="fix-off-by-one",
        agent_id="custom-harness-v1",
        run_result=make_run_result(),
        eval_result=make_eval_result(passed=True),
    )
    assert record.task_id == "fix-off-by-one"
    assert record.agent_id == "custom-harness-v1"
    assert record.run_status == "completed"
    assert record.eval_passed is True
    assert record.run_error is None
    assert record.timestamp


def test_record_stores_metrics_from_logs():
    record = RunRecord.create(
        task_id="t1",
        agent_id="a1",
        run_result=make_run_result(logs=SAMPLE_EVENTS),
        eval_result=make_eval_result(),
    )
    assert record.total_input_tokens == 1100
    assert record.total_output_tokens == 180
    assert record.total_turns == 2
    assert len(record.tool_calls) == 1


def test_record_stores_full_logs():
    record = RunRecord.create(
        task_id="t1",
        agent_id="a1",
        run_result=make_run_result(logs=SAMPLE_EVENTS),
        eval_result=make_eval_result(),
    )
    assert record.logs == SAMPLE_EVENTS


def test_record_captures_failure():
    record = RunRecord.create(
        task_id="t1",
        agent_id="a1",
        run_result=make_run_result(status="failed", error="agent crashed"),
        eval_result=make_eval_result(passed=False),
    )
    assert record.run_status == "failed"
    assert record.run_error == "agent crashed"
    assert record.eval_passed is False


# ---------------------------------------------------------------------------
# ResultsStore
# ---------------------------------------------------------------------------

def test_load_all_returns_empty_when_file_missing(tmp_path):
    assert ResultsStore(tmp_path / "nonexistent.jsonl").load_all() == []


def test_save_and_load_single_record(store):
    record = RunRecord.create(
        task_id="t1", agent_id="a1",
        run_result=make_run_result(logs=SAMPLE_EVENTS),
        eval_result=make_eval_result(),
    )
    store.save(record)
    loaded = store.load_all()
    assert len(loaded) == 1
    assert loaded[0].task_id == "t1"
    assert loaded[0].total_input_tokens == 1100
    assert loaded[0].logs == SAMPLE_EVENTS


def test_save_multiple_records_in_order(store):
    for i in range(3):
        store.save(RunRecord.create(
            task_id=f"task-{i}", agent_id="a1",
            run_result=make_run_result(), eval_result=make_eval_result(),
        ))
    records = store.load_all()
    assert [r.task_id for r in records] == ["task-0", "task-1", "task-2"]


def test_saves_appended_across_instances(tmp_path):
    path = tmp_path / "results.jsonl"
    ResultsStore(path).save(RunRecord.create(
        task_id="t1", agent_id="a1",
        run_result=make_run_result(), eval_result=make_eval_result(),
    ))
    ResultsStore(path).save(RunRecord.create(
        task_id="t2", agent_id="a1",
        run_result=make_run_result(), eval_result=make_eval_result(),
    ))
    assert len(ResultsStore(path).load_all()) == 2


def test_creates_parent_directories(tmp_path):
    store = ResultsStore(tmp_path / "nested" / "dir" / "results.jsonl")
    store.save(RunRecord.create(
        task_id="t1", agent_id="a1",
        run_result=make_run_result(), eval_result=make_eval_result(),
    ))
    assert (tmp_path / "nested" / "dir" / "results.jsonl").exists()
