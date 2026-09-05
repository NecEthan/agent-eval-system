"""FastAPI server — serves results API and the React UI.

Start with:
    python -m eval.cli serve [--results results.jsonl] [--port 7001] [--harness-dir PATH]
"""

from __future__ import annotations

import dataclasses
import json
import re
import threading
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from eval.results_store import ResultsStore


_UI_DIST = Path(__file__).parent.parent / "ui" / "dist"


def _slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:50] or "task"


def create_app(results_path: Path, harness_dir: Path | None = None) -> FastAPI:
    app = FastAPI(title="Agent Eval UI")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    store = ResultsStore(results_path)

    # Simple run state — one run at a time.
    _run_state: dict = {"running": False, "error": None}
    _run_lock = threading.Lock()

    # ------------------------------------------------------------------
    # API
    # ------------------------------------------------------------------

    @app.get("/api/runs")
    def list_runs():
        records = store.load_all()
        return [
            {
                "index": i,
                "task_id": r.task_id,
                "agent_id": r.agent_id,
                "timestamp": r.timestamp,
                "run_status": r.run_status,
                "run_duration": r.run_duration,
                "eval_passed": r.eval_passed,
                "total_turns": r.total_turns,
                "total_input_tokens": r.total_input_tokens,
                "total_output_tokens": r.total_output_tokens,
                "tool_call_count": len(r.tool_calls),
                "model_used": r.model_used,
                "failure_type": r.failure_type,
                "context_condensations": r.context_condensations,
                "retry_count": r.retry_count,
                "control_flow_aborts": r.control_flow_aborts,
            }
            for i, r in enumerate(records)
        ]

    @app.get("/api/runs/{index}")
    def get_run(index: int):
        records = store.load_all()
        if index < 0 or index >= len(records):
            raise HTTPException(status_code=404, detail="Run not found")
        return dataclasses.asdict(records[index])

    @app.get("/api/run/status")
    def run_status():
        return {
            "running": _run_state["running"],
            "error": _run_state["error"],
            "harness_configured": harness_dir is not None,
        }

    @app.post("/api/run")
    def start_run(body: dict = None):
        if harness_dir is None:
            raise HTTPException(status_code=400, detail="No --harness-dir configured. Restart server with --harness-dir.")

        with _run_lock:
            if _run_state["running"]:
                raise HTTPException(status_code=409, detail="A run is already in progress.")
            _run_state["running"] = True
            _run_state["error"] = None

        body = body or {}
        project_root = Path(__file__).parent.parent
        agent_id = body.get("agent_id", "agent-v1")

        # Inline task creation: build task.json from form fields.
        if "description" in body:
            task_id = body.get("task_id") or _slugify(body["description"])
            codebase_path = body.get("codebase_path", "")
            eval_commands = body.get("eval_commands") or []
            if not codebase_path:
                _run_state["running"] = False
                raise HTTPException(status_code=400, detail="codebase_path is required.")
            if not eval_commands:
                _run_state["running"] = False
                raise HTTPException(status_code=400, detail="eval_commands must not be empty.")
            task_dir = project_root / "tasks" / task_id
            task_dir.mkdir(parents=True, exist_ok=True)
            task_json = {
                "id": task_id,
                "description": body["description"],
                "source_path": codebase_path,
                "evaluation": {"commands": eval_commands},
            }
            (task_dir / "task.json").write_text(json.dumps(task_json, indent=2))
            task_path = task_dir / "task.json"
        else:
            task_path = project_root / body.get("task", "tasks/your-task/task.json")

        def _do_run():
            try:
                from eval.adapters.custom_harness import CustomHarnessAdapter, HarnessConfig
                from eval.evaluator import Evaluator
                from eval.runner import Runner, RunnerConfig
                from eval.task_spec import TaskSpec

                task_spec = TaskSpec.from_json(task_path.resolve())
                task_dir = task_path.resolve().parent
                adapter = CustomHarnessAdapter(HarnessConfig(harness_dir=harness_dir))
                # start subprocess with adapter
                with adapter:
                    # run agent get results as events
                    Runner(adapter, store, RunnerConfig()).run(
                        task_spec, agent_id=agent_id, task_dir=task_dir
                    )
                _run_state["error"] = None
            except Exception as exc:
                _run_state["error"] = str(exc)
            finally:
                _run_state["running"] = False

        threading.Thread(target=_do_run, daemon=True).start()
        return {"status": "started"}

    # ------------------------------------------------------------------
    # React UI (served from ui/dist after npm run build)
    # ------------------------------------------------------------------

    if _UI_DIST.exists():
        app.mount("/assets", StaticFiles(directory=_UI_DIST / "assets"), name="assets")

        @app.get("/")
        def index():
            return FileResponse(_UI_DIST / "index.html")

        @app.get("/{path:path}")
        def spa(path: str):
            return FileResponse(_UI_DIST / "index.html")
    else:
        @app.get("/")
        def no_ui():
            return {
                "message": "UI not built. Run: cd ui && npm install && npm run build",
                "api": "/api/runs",
            }

    return app
