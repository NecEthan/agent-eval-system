"""RunResult — standard output every AgentAdapter must return."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal


@dataclass(frozen=True)
class RunResult:
    """Execution result returned by any AgentAdapter.

    'completed' means the agent finished running — not that the task succeeded.
    The Evaluator decides pass/fail by inspecting the working directory.
    """

    status: Literal["completed", "failed", "timeout"]
    duration: float           
    logs: list[dict[str, Any]]  
    error: str | None          
