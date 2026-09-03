

"""AgentAdapter — the contract every agent adapter must satisfy.

The eval platform only knows about this interface and RunResult.
Adapters hide all harness-specific details: how the agent is started,
how it communicates, and how it is stopped.

Lifecycle (start/stop, server management, subprocess handling) is NOT
part of this contract. Different adapters have different lifecycles;
the platform does not care.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from eval.run_result import RunResult


@runtime_checkable
class AgentAdapter(Protocol):
    """Structural protocol for agent adapters.

    Any class with a matching run() signature satisfies this contract.
    No explicit inheritance from AgentAdapter is required.
    """

    def run(self, task: str, working_dir: Path, timeout: float) -> RunResult:
        """Run the agent on the given task.

        Args:
            task:        Natural language prompt sent to the agent.
            working_dir: Absolute path to the isolated working directory
                         prepared by Environment. The agent reads and
                         writes files here.
            timeout:     Maximum wall-clock seconds. The adapter must
                         return a RunResult with status="timeout" if
                         the agent does not finish within this limit.

        Returns:
            RunResult where:
              "completed" — agent finished (task success unknown, Evaluator decides)
              "failed"    — agent could not complete its run (crash, bad config, etc.)
              "timeout"   — agent did not finish within the timeout
        """
        ...
