"""Runner — orchestrates one evaluation run end to end.

Wires together: Environment → AgentAdapter → Evaluator → ResultsStore.
Knows the sequence. Knows nothing about harness internals, eval commands,
or how results are stored.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from eval.adapter import AgentAdapter
from eval.environment import Environment
from eval.evaluator import EvalResult, Evaluator
from eval.results_store import ResultsStore, RunRecord
from eval.task_spec import TaskSpec


@dataclass
class RunnerConfig:
    timeout: float = 300.0        # wall-clock seconds per agent run
    command_timeout: float = 60.0  # seconds per evaluation command


class Runner:
    """Runs one task against one agent and saves the result.

    Usage:
        runner = Runner(adapter, store)
        record = runner.run(task_spec, agent_id="custom-harness-v1")
    """

    def __init__(
        self,
        adapter: AgentAdapter,
        store: ResultsStore,
        config: RunnerConfig | None = None,
    ) -> None:
        self._adapter = adapter
        self._store = store
        self._config = config or RunnerConfig()
        self._evaluator = Evaluator(command_timeout=self._config.command_timeout)

    def run(
        self,
        task_spec: TaskSpec,
        agent_id: str,
        task_dir: Path | None = None,
    ) -> RunRecord:
        """Run one evaluation task and return the saved record.

        Args:
            task_spec: The task to evaluate.
            agent_id:  Name or version of the agent being evaluated.
                       Used to group and compare results across runs.
            task_dir:  Directory containing the task definition. Used to
                       resolve relative source_path values in task_spec.
                       If None, source_path is resolved against cwd.
        """
        source = _resolve_source(task_spec.source_path, task_dir)

        with Environment(source) as working_dir:
            run_result = self._adapter.run(
                task=task_spec.description,
                working_dir=working_dir,
                timeout=self._config.timeout,
            )

            if run_result.status == "completed":
                eval_result = self._evaluator.check(working_dir, task_spec.evaluation)
            else:
                # Agent did not finish — skip evaluation, mark as not passed.
                # run_result.status explains why (failed or timeout).
                eval_result = EvalResult(passed=False, command_results=[])

        record = RunRecord.create(
            task_id=task_spec.id,
            agent_id=agent_id,
            run_result=run_result,
            eval_result=eval_result,
        )
        self._store.save(record)
        return record


def _resolve_source(source_path: Path, task_dir: Path | None) -> Path:
    if source_path.is_absolute():
        return source_path
    if task_dir is not None:
        return (task_dir / source_path).resolve()
    return source_path.resolve()
