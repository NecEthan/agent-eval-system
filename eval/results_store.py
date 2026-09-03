"""ResultsStore — append-only record of every eval run.

Persists one RunRecord per run as a JSON line. Each record contains
a summary of the run and eval results. Raw agent logs are excluded
to keep records lean — they are available from the adapter during the run.

Format: JSON Lines (.jsonl) — one JSON object per line, human-readable,
queryable with standard tools (jq, Python, etc.).
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from eval.evaluator import EvalResult
from eval.run_result import RunResult


@dataclass
class RunRecord:
    """Summary of one evaluation run. Stored as one line in the results file."""

    task_id: str
    agent_id: str       # name/version of the agent being evaluated
    timestamp: str      # ISO 8601 UTC
    run_status: str     # "completed" | "failed" | "timeout"
    run_duration: float # wall-clock seconds
    run_error: str | None
    eval_passed: bool
    eval_commands: list[dict]  # {command, exit_code, passed, duration}

    @classmethod
    def create(
        cls,
        task_id: str,
        agent_id: str,
        run_result: RunResult,
        eval_result: EvalResult,
    ) -> RunRecord:
        return cls(
            task_id=task_id,
            agent_id=agent_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            run_status=run_result.status,
            run_duration=run_result.duration,
            run_error=run_result.error,
            eval_passed=eval_result.passed,
            eval_commands=[
                {
                    "command": r.command,
                    "exit_code": r.exit_code,
                    "passed": r.passed,
                    "duration": r.duration,
                }
                for r in eval_result.command_results
            ],
        )

    @classmethod
    def from_dict(cls, data: dict) -> RunRecord:
        return cls(**data)


class ResultsStore:
    """Append-only JSON Lines store for eval run records.

    Each line is one JSON-serialized RunRecord.
    The file is created on first save if it does not exist.
    """

    def __init__(self, path: Path) -> None:
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def save(self, record: RunRecord) -> None:
        """Append one record to the store."""
        with self._path.open("a") as f:
            f.write(json.dumps(asdict(record)) + "\n")

    def load_all(self) -> list[RunRecord]:
        """Return all records in insertion order."""
        if not self._path.exists():
            return []
        records = []
        for line in self._path.read_text().splitlines():
            line = line.strip()
            if line:
                records.append(RunRecord.from_dict(json.loads(line)))
        return records
