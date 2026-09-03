"""CLI entry point for the agent evaluation platform.

Usage:
    python -m eval.cli <task.json> <agent-id> --harness-dir <path>

Example:
    python -m eval.cli tasks/fix-off-by-one/task.json custom-harness-v1 \
        --harness-dir ../custom-harness
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from eval.adapters.custom_harness import CustomHarnessAdapter, HarnessConfig
from eval.results_store import ResultsStore, RunRecord
from eval.runner import Runner, RunnerConfig
from eval.task_spec import TaskSpec


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run a coding eval task against an agent.",
    )
    parser.add_argument(
        "task",
        type=Path,
        help="Path to task.json",
    )
    parser.add_argument(
        "agent_id",
        help="Name or version label for this agent run (e.g. custom-harness-v1)",
    )
    parser.add_argument(
        "--harness-dir",
        type=Path,
        required=True,
        help="Path to the custom-harness repo on disk",
    )
    parser.add_argument(
        "--results",
        type=Path,
        default=Path("results.jsonl"),
        help="Path to results file (default: results.jsonl)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=300.0,
        help="Agent timeout in seconds (default: 300)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Harness server port (default: 8000)",
    )
    args = parser.parse_args()

    task_path = args.task.resolve()
    if not task_path.exists():
        print(f"error: task file not found: {task_path}", file=sys.stderr)
        sys.exit(1)

    harness_dir = args.harness_dir.resolve()
    if not harness_dir.exists():
        print(f"error: harness directory not found: {harness_dir}", file=sys.stderr)
        sys.exit(1)

    task_spec = TaskSpec.from_json(task_path)
    task_dir = task_path.parent

    print(f"task:   {task_spec.id}")
    print(f"agent:  {args.agent_id}")
    print(f"starting harness server on port {args.port}...")

    harness_config = HarnessConfig(harness_dir=harness_dir, port=args.port)
    store = ResultsStore(args.results)
    runner_config = RunnerConfig(timeout=args.timeout)

    with CustomHarnessAdapter(harness_config) as adapter:
        record = Runner(adapter, store, runner_config).run(
            task_spec,
            agent_id=args.agent_id,
            task_dir=task_dir,
        )

    _print_result(record)
    sys.exit(0 if record.eval_passed else 1)


def _print_result(record: RunRecord) -> None:
    print()
    print(f"status: {record.run_status}")
    print(f"result: {'PASS' if record.eval_passed else 'FAIL'}")
    print(f"time:   {record.run_duration:.1f}s")

    if record.run_error:
        print(f"error:  {record.run_error}")

    if record.eval_commands:
        print()
        print("commands:")
        for cmd in record.eval_commands:
            mark = "pass" if cmd["passed"] else "FAIL"
            print(f"  [{mark}] {cmd['command']}  (exit {cmd['exit_code']}, {cmd['duration']:.1f}s)")


if __name__ == "__main__":
    main()
