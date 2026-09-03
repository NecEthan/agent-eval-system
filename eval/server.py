"""FastAPI server — serves results API and the React UI.

Start with:
    python -m eval.cli serve [--results results.jsonl] [--port 7000]
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from eval.results_store import ResultsStore


_UI_DIST = Path(__file__).parent.parent / "ui" / "dist"


def create_app(results_path: Path) -> FastAPI:
    app = FastAPI(title="Agent Eval UI")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    store = ResultsStore(results_path)

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
            }
            for i, r in enumerate(records)
        ]

    @app.get("/api/runs/{index}")
    def get_run(index: int):
        records = store.load_all()
        if index < 0 or index >= len(records):
            raise HTTPException(status_code=404, detail="Run not found")
        return dataclasses.asdict(records[index])

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
