"""Task specification — static definition of one coding evaluation task."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class EvaluationCriteria:
    """How to determine whether the agent completed the task.

    Run each command in the working directory after the agent finishes.
    All commands must exit 0 for the task to pass.
    """
    commands: list[str]


@dataclass(frozen=True)
class TaskSpec:
    """Immutable definition of one coding evaluation task."""

    id: str
    description: str
    source_path: Path
    evaluation: EvaluationCriteria

    @classmethod
    def from_json(cls, path: Path) -> TaskSpec:
        data = json.loads(path.read_text())
        return cls(
            id=data["id"],
            description=data["description"],
            source_path=Path(data["source_path"]),
            evaluation=EvaluationCriteria(
                commands=data["evaluation"]["commands"],
            ),
        )
