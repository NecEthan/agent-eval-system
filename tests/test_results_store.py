"""Tests for ResultsStore and RunRecord."""

import pytest
from pathlib import Path

from eval.evaluator import EvalResult, CommandResult
from eval.results_store import ResultsStore, RunRecord
from eval.run_result import RunResult


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def store(tmp_path):
    return ResultsStore(tmp_path / "results.jsonl")


def make_run_result(status="completed", duration=1.0, error=None):
    return RunResult(status=status, duration=duration, logs=[], error=error)


def make_eval_result(passed=True):
    cmd = CommandResult(
        command="python -m pytest",
        exit_code=0 if passed else 1,
        stdout="",
        stderr="",
        duration=0.5,
    )
    return EvalResult(passed=passed, command_results=[cmd])


# ---------------------------------------------------------------------------
# RunRecord.create
# ---------------------------------------------------------------------------

def test_record_create_fields():
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
    assert record.timestamp  # non-empty


def test_record_captures_failure():
    record = RunRecord.create(
        task_id="fix-off-by-one",
        agent_id="custom-harness-v1",
        run_result=make_run_result(status="failed", error="agent crashed"),
        eval_result=make_eval_result(passed=False),
    )
    assert record.run_status == "failed"
    assert record.run_error == "agent crashed"
    assert record.eval_passed is False


def test_record_command_results_summarised():
    record = RunRecord.create(
        task_id="t1",
        agent_id="a1",
        run_result=make_run_result(),
        eval_result=make_eval_result(passed=True),
    )
    assert len(record.eval_commands) == 1
    assert record.eval_commands[0]["command"] == "python -m pytest"
    assert record.eval_commands[0]["passed"] is True


# ---------------------------------------------------------------------------
# ResultsStore
# ---------------------------------------------------------------------------

def test_load_all_returns_empty_when_file_missing(tmp_path):
    store = ResultsStore(tmp_path / "nonexistent.jsonl")
    assert store.load_all() == []


def test_save_and_load_single_record(store):
    record = RunRecord.create(
        task_id="t1",
        agent_id="a1",
        run_result=make_run_result(),
        eval_result=make_eval_result(),
    )
    store.save(record)
    loaded = store.load_all()
    assert len(loaded) == 1
    assert loaded[0].task_id == "t1"
    assert loaded[0].agent_id == "a1"
    assert loaded[0].eval_passed is True


def test_save_multiple_records_in_order(store):
    for i in range(3):
        store.save(RunRecord.create(
            task_id=f"task-{i}",
            agent_id="a1",
            run_result=make_run_result(),
            eval_result=make_eval_result(),
        ))
    records = store.load_all()
    assert len(records) == 3
    assert [r.task_id for r in records] == ["task-0", "task-1", "task-2"]


def test_saves_are_appended_across_instances(tmp_path):
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
