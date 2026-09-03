"""ResultsStore — append-only record of every eval run.

Each record contains the full agent event log plus extracted metrics
(tokens, turns, tool calls) so every run is fully inspectable.

Format: JSON Lines (.jsonl) — one JSON object per line.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from eval.evaluator import EvalResult
from eval.run_result import RunResult


@dataclass
class RunRecord:
    """Complete record of one evaluation run."""

    task_id: str
    agent_id: str
    timestamp: str           # ISO 8601 UTC
    run_status: str          # "completed" | "failed" | "timeout"
    run_duration: float      # wall-clock seconds
    run_error: str | None

    # Agent metrics — extracted from event stream
    total_input_tokens: int
    total_output_tokens: int
    total_turns: int
    tool_calls: list[dict]   # [{name, input, output, is_error, duration}]

    # Eval results
    eval_passed: bool
    eval_commands: list[dict]  # [{command, exit_code, passed, duration}]

    # Full event stream for deep inspection
    logs: list[dict[str, Any]]

    @classmethod
    def create(
        cls,
        task_id: str,
        agent_id: str,
        run_result: RunResult,
        eval_result: EvalResult,
    ) -> RunRecord:
        metrics = _extract_metrics(run_result.logs)
        return cls(
            task_id=task_id,
            agent_id=agent_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            run_status=run_result.status,
            run_duration=run_result.duration,
            run_error=run_result.error,
            total_input_tokens=metrics["total_input_tokens"],
            total_output_tokens=metrics["total_output_tokens"],
            total_turns=metrics["total_turns"],
            tool_calls=metrics["tool_calls"],
            eval_passed=eval_result.passed,
            eval_commands=[
                {
                    "command": r.command,
                    "exit_code": r.exit_code,
                    "passed": r.passed,
                    "duration": r.duration,
                    "stdout": r.stdout,
                    "stderr": r.stderr,
                }
                for r in eval_result.command_results
            ],
            logs=run_result.logs,
        )

    @classmethod
    def from_dict(cls, data: dict) -> RunRecord:
        return cls(**data)


class ResultsStore:
    """Append-only JSON Lines store for eval run records."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def save(self, record: RunRecord) -> None:
        with self._path.open("a") as f:
            f.write(json.dumps(asdict(record)) + "\n")

    def load_all(self) -> list[RunRecord]:
        if not self._path.exists():
            return []
        records = []
        for line in self._path.read_text().splitlines():
            line = line.strip()
            if line:
                records.append(RunRecord.from_dict(json.loads(line)))
        return records


def _extract_metrics(events: list[dict]) -> dict:
    """Pull token counts, turn count, and tool call details from the event stream."""
    total_input_tokens = 0
    total_output_tokens = 0
    total_turns = 0
    tool_calls = []
    pending: dict[str, dict] = {}  # tool_use_id → ToolCalled event

    for event in events:
        t = event.get("type")

        if t == "ModelResponded":
            total_input_tokens += event.get("input_tokens", 0)
            total_output_tokens += event.get("output_tokens", 0)

        elif t == "AgentFinished":
            total_turns = event.get("total_turns", 0)

        elif t == "ToolCalled":
            pending[event["tool_use_id"]] = event

        elif t == "ToolResulted":
            call = pending.pop(event.get("tool_use_id", ""), {})
            tool_calls.append({
                "name": event.get("name"),
                "input": call.get("input", {}),
                "output": event.get("output", ""),
                "is_error": event.get("is_error", False),
                "duration": event.get("duration"),
            })

    return {
        "total_input_tokens": total_input_tokens,
        "total_output_tokens": total_output_tokens,
        "total_turns": total_turns,
        "tool_calls": tool_calls,
    }
