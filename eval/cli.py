"""CLI entry point for the agent evaluation platform.

Subcommands:
    run      — run an eval task against an agent
    results  — display results from a results.jsonl file

Usage:
    python -m eval.cli run tasks/your-task/task.json agent-v1 --harness-dir ../custom-harness
    python -m eval.cli results
    python -m eval.cli results results.jsonl
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
    parser = argparse.ArgumentParser(description="Agent evaluation platform.")
    sub = parser.add_subparsers(dest="command", required=True)

    # ------------------------------------------------------------------
    # run
    # ------------------------------------------------------------------
    run_parser = sub.add_parser("run", help="Run an eval task against an agent.")
    run_parser.add_argument("task", type=Path, help="Path to task.json")
    run_parser.add_argument("agent_id", help="Name or version label (e.g. agent-v1)")
    run_parser.add_argument("--adapter", help="Dotted import path to adapter class (e.g. mypackage.MyAdapter)")
    run_parser.add_argument("--harness-dir", type=Path, help="Path to custom-harness repo. Required when --adapter is not set.")
    run_parser.add_argument("--results", type=Path, default=Path("results.jsonl"), help="Results file (default: results.jsonl)")
    run_parser.add_argument("--timeout", type=float, default=300.0, help="Agent timeout in seconds (default: 300)")
    run_parser.add_argument("--port", type=int, default=8000, help="Harness server port (default: 8000)")

    # ------------------------------------------------------------------
    # results
    # ------------------------------------------------------------------
    results_parser = sub.add_parser("results", help="Display results from a results file.")
    results_parser.add_argument("file", type=Path, nargs="?", default=Path("results.jsonl"), help="Path to results file (default: results.jsonl)")

    # ------------------------------------------------------------------
    # serve
    # ------------------------------------------------------------------
    serve_parser = sub.add_parser("serve", help="Start the web UI server.")
    serve_parser.add_argument("--results", type=Path, default=Path("results.jsonl"), help="Path to results file (default: results.jsonl)")
    serve_parser.add_argument("--port", type=int, default=7000, help="Port to serve on (default: 7000)")

    args = parser.parse_args()

    if args.command == "run":
        _cmd_run(args)
    elif args.command == "results":
        _cmd_results(args)
    elif args.command == "serve":
        _cmd_serve(args)


# ------------------------------------------------------------------
# run command
# ------------------------------------------------------------------

def _cmd_run(args: argparse.Namespace) -> None:
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

    _print_run_result(record)
    sys.exit(0 if record.eval_passed else 1)


# ------------------------------------------------------------------
# results command
# ------------------------------------------------------------------

def _cmd_results(args: argparse.Namespace) -> None:
    path = args.file
    if not path.exists():
        print(f"no results file found at {path}", file=sys.stderr)
        sys.exit(1)

    records = ResultsStore(path).load_all()
    if not records:
        print("no results yet.")
        return

    # Column widths
    w_task   = max(len("TASK"),   max(len(r.task_id)  for r in records))
    w_agent  = max(len("AGENT"),  max(len(r.agent_id) for r in records))
    w_status = max(len("STATUS"), max(len(r.run_status) for r in records))

    header = (
        f"{'TASK':<{w_task}}  "
        f"{'AGENT':<{w_agent}}  "
        f"{'STATUS':<{w_status}}  "
        f"{'RESULT':<6}  "
        f"{'TURNS':>5}  "
        f"{'TOKENS IN':>10}  "
        f"{'TOKENS OUT':>10}  "
        f"{'TIME':>7}"
    )
    separator = "-" * len(header)

    print()
    print(header)
    print(separator)

    for r in records:
        result = "PASS" if r.eval_passed else "FAIL"
        tokens_in = f"{r.total_input_tokens:,}"
        tokens_out = f"{r.total_output_tokens:,}"
        time = f"{r.run_duration:.1f}s"
        print(
            f"{r.task_id:<{w_task}}  "
            f"{r.agent_id:<{w_agent}}  "
            f"{r.run_status:<{w_status}}  "
            f"{result:<6}  "
            f"{r.total_turns:>5}  "
            f"{tokens_in:>10}  "
            f"{tokens_out:>10}  "
            f"{time:>7}"
        )

    print(separator)
    total = len(records)
    passed = sum(1 for r in records if r.eval_passed)
    print(f"\n{passed}/{total} passed  ({100 * passed // total}%)")
    print()


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _cmd_serve(args: argparse.Namespace) -> None:
    import uvicorn
    from eval.server import create_app
    print(f"starting UI server at http://localhost:{args.port}")
    print(f"reading results from {args.results}")
    app = create_app(args.results.resolve())
    uvicorn.run(app, host="127.0.0.1", port=args.port)


def _build_adapter(args: argparse.Namespace):
    if args.adapter:
        return _import_adapter(args.adapter)

    if not args.harness_dir:
        print("error: --harness-dir is required when --adapter is not set.", file=sys.stderr)
        sys.exit(1)

    harness_dir = args.harness_dir.resolve()
    if not harness_dir.exists():
        print(f"error: harness directory not found: {harness_dir}", file=sys.stderr)
        sys.exit(1)

    from eval.adapters.custom_harness import CustomHarnessAdapter, HarnessConfig
    print(f"starting harness server on port {args.port}...")
    return CustomHarnessAdapter(HarnessConfig(harness_dir=harness_dir, port=args.port))


def _import_adapter(import_path: str):
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


def _print_run_result(record: RunRecord) -> None:
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
            if not cmd["passed"]:
                output = (cmd.get("stdout") or "") + (cmd.get("stderr") or "")
                if output.strip():
                    for line in output.strip().splitlines()[-20:]:
                        print(f"         {line}")


if __name__ == "__main__":
    main()
