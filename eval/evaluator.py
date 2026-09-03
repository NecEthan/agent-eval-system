"""Evaluator — runs evaluation commands and returns pass/fail.

Receives the working directory after the agent has finished and the
evaluation criteria from TaskSpec. Knows nothing about agents or harnesses.
"""

from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from eval.task_spec import EvaluationCriteria


@dataclass(frozen=True)
class CommandResult:
    command: str
    exit_code: int
    stdout: str
    stderr: str
    duration: float

    @property
    def passed(self) -> bool:
        return self.exit_code == 0


@dataclass(frozen=True)
class EvalResult:
    passed: bool
    command_results: list[CommandResult]


class Evaluator:
    """Runs evaluation commands in the working directory and returns EvalResult.

    All commands in EvaluationCriteria must exit 0 for the task to pass.
    Commands run in sequence; all are executed even if one fails.
    """

    def __init__(self, command_timeout: float = 60.0) -> None:
        self._command_timeout = command_timeout

    def check(self, working_dir: Path, criteria: EvaluationCriteria) -> EvalResult:
        results = [self._run(cmd, working_dir) for cmd in criteria.commands]
        return EvalResult(
            passed=all(r.passed for r in results),
            command_results=results,
        )

    def _run(self, command: str, cwd: Path) -> CommandResult:
        start = time.monotonic()
        try:
            proc = subprocess.run(
                command,
                shell=True,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=self._command_timeout,
            )
            return CommandResult(
                command=command,
                exit_code=proc.returncode,
                stdout=proc.stdout,
                stderr=proc.stderr,
                duration=time.monotonic() - start,
            )
        except subprocess.TimeoutExpired:
            return CommandResult(
                command=command,
                exit_code=-1,
                stdout="",
                stderr=f"Command timed out after {self._command_timeout}s",
                duration=self._command_timeout,
            )
