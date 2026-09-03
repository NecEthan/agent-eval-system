"""CLI entry point for the agent evaluation platform.

Usage:
    # Built-in custom harness adapter:
    python -m eval.cli tasks/fix-off-by-one/task.json custom-harness-v1 \
        --harness-dir ../custom-harness

    # Any custom adapter (no-arg constructor):
    python -m eval.cli tasks/fix-off-by-one/task.json my-agent-v1 \
        --adapter mypackage.adapters.MyAdapter
"""

from __future__ import annotations

import argparse
import importlib
import sys
from pathlib import Path

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
        help="Name or version label for this agent run (e.g. my-agent-v1)",
    )
    parser.add_argument(
        "--adapter",
        help=(
            "Dotted import path to an adapter class (e.g. mypackage.MyAdapter). "
            "The class must have a no-argument constructor and satisfy AgentAdapter. "
            "If omitted, defaults to the built-in CustomHarnessAdapter."
        ),
    )
    parser.add_argument(
        "--harness-dir",
        type=Path,
        help="Path to the custom-harness repo. Required when --adapter is not set.",
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
        help="Harness server port — only used with the built-in adapter (default: 8000)",
    )
    args = parser.parse_args()

    task_path = args.task.resolve()
    if not task_path.exists():
        print(f"error: task file not found: {task_path}", file=sys.stderr)
        sys.exit(1)

    task_spec = TaskSpec.from_json(task_path)
    task_dir = task_path.parent
    store = ResultsStore(args.results)
    runner_config = RunnerConfig(timeout=args.timeout)

    print(f"task:   {task_spec.id}")
    print(f"agent:  {args.agent_id}")

    adapter = _build_adapter(args)

    with adapter:
        record = Runner(adapter, store, runner_config).run(
            task_spec,
            agent_id=args.agent_id,
            task_dir=task_dir,
        )

    _print_result(record)
    sys.exit(0 if record.eval_passed else 1)


def _build_adapter(args: argparse.Namespace):
    """Instantiate the correct adapter based on CLI args."""
    if args.adapter:
        return _import_adapter(args.adapter)

    # Default: built-in CustomHarnessAdapter
    if not args.harness_dir:
        print(
            "error: --harness-dir is required when --adapter is not set.",
            file=sys.stderr,
        )
        sys.exit(1)

    harness_dir = args.harness_dir.resolve()
    if not harness_dir.exists():
        print(f"error: harness directory not found: {harness_dir}", file=sys.stderr)
        sys.exit(1)

    from eval.adapters.custom_harness import CustomHarnessAdapter, HarnessConfig
    print(f"starting harness server on port {args.port}...")
    return CustomHarnessAdapter(HarnessConfig(harness_dir=harness_dir, port=args.port))


def _import_adapter(import_path: str):
    """Dynamically load an adapter class from a dotted import path and instantiate it.

    The class must have a no-argument constructor.
    Example: 'mypackage.adapters.MyAdapter'
    """
    try:
        module_path, class_name = import_path.rsplit(".", 1)
    except ValueError:
        print(f"error: invalid adapter path '{import_path}'. Expected 'module.ClassName'.", file=sys.stderr)
        sys.exit(1)

    try:
        module = importlib.import_module(module_path)
    except ModuleNotFoundError as e:
        print(f"error: could not import adapter module '{module_path}': {e}", file=sys.stderr)
        sys.exit(1)

    cls = getattr(module, class_name, None)
    if cls is None:
        print(f"error: class '{class_name}' not found in module '{module_path}'.", file=sys.stderr)
        sys.exit(1)

    try:
        return cls()
    except Exception as e:
        print(f"error: could not instantiate adapter '{import_path}': {e}", file=sys.stderr)
        sys.exit(1)


def _print_result(record: RunRecord) -> None:
    print()
    print(f"status: {record.run_status}")
    print(f"result: {'PASS' if record.eval_passed else 'FAIL'}")
    print(f"time:   {record.run_duration:.1f}s")

    if record.run_error:
        print(f"error:  {record.run_error}")

    if record.total_turns or record.total_input_tokens:
        print()
        print(f"turns:  {record.total_turns}")
        print(f"tokens: {record.total_input_tokens:,} in / {record.total_output_tokens:,} out")

    if record.tool_calls:
        print()
        print("tool calls:")
        for call in record.tool_calls:
            status = "error" if call["is_error"] else "ok"
            duration = f"{call['duration']:.2f}s" if call["duration"] is not None else "?"
            print(f"  [{status}] {call['name']}  ({duration})")

    if record.eval_commands:
        print()
        print("eval:")
        for cmd in record.eval_commands:
            mark = "pass" if cmd["passed"] else "FAIL"
            print(f"  [{mark}] {cmd['command']}  (exit {cmd['exit_code']}, {cmd['duration']:.1f}s)")


if __name__ == "__main__":
    main()
