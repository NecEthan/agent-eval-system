"""Tests for Evaluator."""

import pytest
from pathlib import Path

from eval.evaluator import Evaluator, EvalResult, CommandResult
from eval.task_spec import EvaluationCriteria


@pytest.fixture
def evaluator():
    return Evaluator(command_timeout=10.0)


@pytest.fixture
def work_dir(tmp_path):
    return tmp_path


# ---------------------------------------------------------------------------
# CommandResult
# ---------------------------------------------------------------------------

def test_command_result_passed_on_exit_zero():
    result = CommandResult(command="echo hi", exit_code=0, stdout="hi\n", stderr="", duration=0.1)
    assert result.passed is True


def test_command_result_failed_on_nonzero_exit():
    result = CommandResult(command="exit 1", exit_code=1, stdout="", stderr="", duration=0.1)
    assert result.passed is False


# ---------------------------------------------------------------------------
# Evaluator.check
# ---------------------------------------------------------------------------

def test_passing_command(evaluator, work_dir):
    criteria = EvaluationCriteria(commands=["python3 -c 'exit(0)'"])
    result = evaluator.check(work_dir, criteria)
    assert result.passed is True


def test_failing_command(evaluator, work_dir):
    criteria = EvaluationCriteria(commands=["python3 -c 'exit(1)'"])
    result = evaluator.check(work_dir, criteria)
    assert result.passed is False


def test_all_commands_run_even_if_one_fails(evaluator, work_dir):
    criteria = EvaluationCriteria(commands=[
        "python3 -c 'exit(1)'",
        "python3 -c 'exit(0)'",
    ])
    result = evaluator.check(work_dir, criteria)
    assert len(result.command_results) == 2
    assert result.command_results[0].passed is False
    assert result.command_results[1].passed is True


def test_passes_only_when_all_commands_pass(evaluator, work_dir):
    criteria = EvaluationCriteria(commands=[
        "python3 -c 'exit(0)'",
        "python3 -c 'exit(0)'",
    ])
    result = evaluator.check(work_dir, criteria)
    assert result.passed is True


def test_fails_when_any_command_fails(evaluator, work_dir):
    criteria = EvaluationCriteria(commands=[
        "python3 -c 'exit(0)'",
        "python3 -c 'exit(1)'",
    ])
    result = evaluator.check(work_dir, criteria)
    assert result.passed is False


def test_captures_stdout(evaluator, work_dir):
    criteria = EvaluationCriteria(commands=["echo hello"])
    result = evaluator.check(work_dir, criteria)
    assert "hello" in result.command_results[0].stdout


def test_captures_exit_code(evaluator, work_dir):
    criteria = EvaluationCriteria(commands=["python3 -c 'exit(42)'"])
    result = evaluator.check(work_dir, criteria)
    assert result.command_results[0].exit_code == 42


def test_command_runs_in_working_dir(evaluator, work_dir):
    (work_dir / "marker.txt").write_text("present")
    criteria = EvaluationCriteria(commands=["python3 -c \"import os; exit(0 if 'marker.txt' in os.listdir() else 1)\""])
    result = evaluator.check(work_dir, criteria)
    assert result.passed is True


def test_timeout_returns_failed_result(work_dir):
    evaluator = Evaluator(command_timeout=0.1)
    criteria = EvaluationCriteria(commands=["python3 -c 'import time; time.sleep(5)'"])
    result = evaluator.check(work_dir, criteria)
    assert result.passed is False
    assert result.command_results[0].exit_code == -1
    assert "timed out" in result.command_results[0].stderr
