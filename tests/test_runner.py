"""Tests for Runner.

Uses a StubAdapter so no real agent or harness is needed.
"""

import pytest
from pathlib import Path

from eval.results_store import ResultsStore
from eval.run_result import RunResult
from eval.runner import Runner, RunnerConfig
from eval.task_spec import EvaluationCriteria, TaskSpec


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class StubAdapter:
    """Returns a fixed RunResult without invoking any real agent."""

    def __init__(self, result: RunResult) -> None:
        self._result = result

    def run(self, task: str, working_dir: Path, timeout: float) -> RunResult:
        return self._result


def make_task_spec(tmp_path: Path, commands: list[str]) -> tuple[TaskSpec, Path]:
    """Create a minimal TaskSpec with a real source directory."""
    source = tmp_path / "repo"
    source.mkdir()
    (source / "placeholder.txt").write_text("starting state")

    task_dir = tmp_path
    spec = TaskSpec(
        id="test-task",
        description="Fix the bug.",
        source_path=Path("repo"),   # relative — runner resolves via task_dir
        evaluation=EvaluationCriteria(commands=commands),
    )
    return spec, task_dir


@pytest.fixture
def store(tmp_path):
    return ResultsStore(tmp_path / "results.jsonl")


# ---------------------------------------------------------------------------
# Completed + passed
# ---------------------------------------------------------------------------

def test_completed_and_passed(tmp_path, store):
    spec, task_dir = make_task_spec(tmp_path, commands=["python3 -c 'exit(0)'"])
    adapter = StubAdapter(RunResult(status="completed", duration=1.0, logs=[], error=None))

    runner = Runner(adapter, store)
    record = runner.run(spec, agent_id="stub-v1", task_dir=task_dir)

    assert record.run_status == "completed"
    assert record.eval_passed is True
    assert record.task_id == "test-task"
    assert record.agent_id == "stub-v1"


# ---------------------------------------------------------------------------
# Completed + failed eval
# ---------------------------------------------------------------------------

def test_completed_but_eval_fails(tmp_path, store):
    spec, task_dir = make_task_spec(tmp_path, commands=["python3 -c 'exit(1)'"])
    adapter = StubAdapter(RunResult(status="completed", duration=1.0, logs=[], error=None))

    runner = Runner(adapter, store)
    record = runner.run(spec, agent_id="stub-v1", task_dir=task_dir)

    assert record.run_status == "completed"
    assert record.eval_passed is False


# ---------------------------------------------------------------------------
# Timeout — eval skipped
# ---------------------------------------------------------------------------

def test_timeout_skips_eval(tmp_path, store):
    spec, task_dir = make_task_spec(tmp_path, commands=["python3 -c 'exit(0)'"])
    adapter = StubAdapter(RunResult(status="timeout", duration=300.0, logs=[], error=None))

    runner = Runner(adapter, store)
    record = runner.run(spec, agent_id="stub-v1", task_dir=task_dir)

    assert record.run_status == "timeout"
    assert record.eval_passed is False
    assert record.eval_commands == []


# ---------------------------------------------------------------------------
# Failed run — eval skipped
# ---------------------------------------------------------------------------

def test_failed_run_skips_eval(tmp_path, store):
    spec, task_dir = make_task_spec(tmp_path, commands=["python3 -c 'exit(0)'"])
    adapter = StubAdapter(RunResult(status="failed", duration=0.5, logs=[], error="agent crashed"))

    runner = Runner(adapter, store)
    record = runner.run(spec, agent_id="stub-v1", task_dir=task_dir)

    assert record.run_status == "failed"
    assert record.run_error == "agent crashed"
    assert record.eval_passed is False
    assert record.eval_commands == []


# ---------------------------------------------------------------------------
# Record is persisted
# ---------------------------------------------------------------------------

def test_record_saved_to_store(tmp_path, store):
    spec, task_dir = make_task_spec(tmp_path, commands=["python3 -c 'exit(0)'"])
    adapter = StubAdapter(RunResult(status="completed", duration=1.0, logs=[], error=None))

    Runner(adapter, store).run(spec, agent_id="stub-v1", task_dir=task_dir)

    records = store.load_all()
    assert len(records) == 1
    assert records[0].task_id == "test-task"


# ---------------------------------------------------------------------------
# Environment cleanup
# ---------------------------------------------------------------------------

def test_working_dir_cleaned_up_after_run(tmp_path, store):
    captured: dict = {}

    class CapturingAdapter:
        def run(self, task: str, working_dir: Path, timeout: float) -> RunResult:
            captured["working_dir"] = working_dir
            return RunResult(status="completed", duration=0.1, logs=[], error=None)

    spec, task_dir = make_task_spec(tmp_path, commands=["python3 -c 'exit(0)'"])
    Runner(CapturingAdapter(), store).run(spec, agent_id="stub-v1", task_dir=task_dir)

    assert not captured["working_dir"].exists()
