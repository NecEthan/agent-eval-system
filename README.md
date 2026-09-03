# Agent Eval System

A pluggable evaluation platform for custom AI coding agents.

Run coding tasks against an agent, evaluate the result, and record metrics. Compare different agents or versions of the same agent over time.

---

## How it works

```
Task Spec → Environment → Agent Adapter → Agent → Evaluator → Results Store
```

1. **Task Spec** — defines the task: a prompt, a starting codebase, and commands to check success
2. **Environment** — copies the starting codebase into an isolated temp directory
3. **Agent Adapter** — starts your agent and gives it the task and directory to work in
4. **Agent** — reads and writes files in the working directory
5. **Evaluator** — runs the evaluation commands (e.g. `pytest`) against the result
6. **Results Store** — appends a record to `results.jsonl`

---

## Requirements

- Python 3.11+
- An agent harness to evaluate

---

## Setup

```bash
git clone https://github.com/NecEthan/agent-eval-system
cd agent-eval-system
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

---

## Adding a task

A task has two parts: a definition file and a starting codebase.

```
tasks/
└── your-task/
    ├── task.json
    └── repo/        ← your starting codebase (never committed)
```

**1. Create the task directory:**

```bash
mkdir -p tasks/your-task/repo
```

**2. Copy your codebase into `repo/`:**

```bash
cp -r /path/to/your/codebase/. tasks/your-task/repo/
```

**3. Write `task.json`:**

```json
{
  "id": "your-task",
  "description": "Fix the failing authentication tests so all tests pass.",
  "source_path": "./repo",
  "evaluation": {
    "commands": ["python -m pytest tests/"]
  }
}
```

| Field | Description |
|---|---|
| `id` | Unique task identifier. Used to group results. |
| `description` | The prompt sent to the agent. |
| `source_path` | Path to the starting codebase, relative to `task.json`. |
| `evaluation.commands` | Commands run after the agent finishes. All must exit 0 to pass. |

The `repo/` folder is gitignored — your codebase stays local.

---

## Connecting your agent

There are two ways to connect an agent.

### Option A — HTTP-compatible harness

If your harness exposes the same HTTP API as [custom-harness](https://github.com/NecEthan/custom-harness) (`POST /run`, `GET /run/state`, `GET /health`), point `--harness-dir` at your repo:

```bash
python -m eval.cli tasks/your-task/task.json agent-v1 \
    --harness-dir /path/to/your-harness
```

### Option B — Custom adapter

Write a Python class with one method:

```python
# my_adapter.py
from pathlib import Path
from eval.run_result import RunResult

class MyAdapter:
    def run(self, task: str, working_dir: Path, timeout: float) -> RunResult:
        # 1. Start your agent with the task and working_dir
        # 2. Wait until it finishes or timeout is reached
        # 3. Return a RunResult

        return RunResult(
            status="completed",  # "completed" | "failed" | "timeout"
            duration=12.4,
            logs=[],
            error=None,
        )
```

**`RunResult` fields:**

| Field | Description |
|---|---|
| `status` | `"completed"` — agent finished. `"failed"` — agent crashed. `"timeout"` — exceeded time limit. |
| `duration` | Wall-clock seconds the agent ran. |
| `logs` | Any runtime events you want to capture (can be empty). |
| `error` | Error message if `status == "failed"`, otherwise `None`. |

> `"completed"` does not mean the task succeeded — only that the agent finished running. The evaluator decides pass/fail.

Then run with your adapter:

```bash
python -m eval.cli tasks/your-task/task.json agent-v1 \
    --adapter my_adapter.MyAdapter
```

The adapter class must have a no-argument constructor. Configure it via environment variables or hardcoded defaults.

---

## Running an eval

```bash
python -m eval.cli <task.json> <agent-id> [options]
```

**Arguments:**

| Argument | Description |
|---|---|
| `task` | Path to `task.json` |
| `agent_id` | Name or version label for this run (e.g. `my-agent-v1`) |
| `--adapter` | Dotted import path to your adapter class |
| `--harness-dir` | Path to a custom-harness compatible repo (used when `--adapter` is not set) |
| `--results` | Path to results file (default: `results.jsonl`) |
| `--timeout` | Agent timeout in seconds (default: `300`) |
| `--port` | Harness server port, built-in adapter only (default: `8000`) |

**Example output:**

```
task:   your-task
agent:  my-agent-v1

status: completed
result: PASS
time:   14.2s

commands:
  [pass] python -m pytest tests/  (exit 0, 3.1s)
```

Exit code is `0` on pass, `1` on fail — works in CI.

---

## Results

Every run appends a record to `results.jsonl`:

```json
{
  "task_id": "your-task",
  "agent_id": "my-agent-v1",
  "timestamp": "2026-09-03T10:00:00+00:00",
  "run_status": "completed",
  "run_duration": 14.2,
  "run_error": null,
  "eval_passed": true,
  "eval_commands": [
    {"command": "python -m pytest tests/", "exit_code": 0, "passed": true, "duration": 3.1}
  ]
}
```

Query with `jq`:

```bash
# pass rate for an agent
jq 'select(.agent_id == "my-agent-v1") | .eval_passed' results.jsonl | grep -c true

# compare two agents on the same task
jq 'select(.task_id == "your-task") | {agent_id, eval_passed, run_duration}' results.jsonl
```

---

## Project structure

```
agent-eval-system/
├── eval/
│   ├── task_spec.py          # TaskSpec — task definition
│   ├── environment.py        # Environment — isolated working directory
│   ├── adapter.py            # AgentAdapter — protocol all adapters satisfy
│   ├── run_result.py         # RunResult — standard adapter output
│   ├── evaluator.py          # Evaluator — runs commands, returns pass/fail
│   ├── results_store.py      # ResultsStore — appends records to .jsonl
│   ├── runner.py             # Runner — orchestrates the full pipeline
│   ├── cli.py                # CLI entry point
│   └── adapters/
│       └── custom_harness.py # Built-in adapter for custom-harness
└── tasks/
    └── fix-off-by-one/       # Example task
        └── task.json
```
