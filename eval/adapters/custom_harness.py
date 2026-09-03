"""AgentAdapter implementation for github.com/NecEthan/custom-harness.

Starts the harness FastAPI server as a subprocess and communicates via HTTP.
The eval platform never imports harness internals — all communication is HTTP.

Constraint: the harness server is single-tenant (one run at a time).
"""

from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

import httpx

from eval.run_result import RunResult


_POLL_INTERVAL = 0.5    # seconds between /run/state polls
_STARTUP_TIMEOUT = 15.0  # seconds to wait for server to become ready


@dataclass
class HarnessConfig:
    harness_dir: Path           # path to the custom-harness repo on disk
    host: str = "127.0.0.1"
    port: int = 8000
    max_turns: int = 20


class CustomHarnessAdapter:
    """Adapter for the custom harness. Manages the server subprocess lifecycle.

    Start once, call run() for each task, stop when done.

        with CustomHarnessAdapter(config) as adapter:
            result = adapter.run(task, working_dir, timeout=300)
    """

    def __init__(self, config: HarnessConfig) -> None:
        self._config = config
        self._process: subprocess.Popen | None = None
        self._base_url = f"http://{config.host}:{config.port}"

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start the harness server subprocess."""
        self._process = subprocess.Popen(
            [
                "python", "-m", "uvicorn", "harness.server:app",
                "--host", self._config.host,
                "--port", str(self._config.port),
            ],
            cwd=self._config.harness_dir,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self._wait_for_ready()

    def stop(self) -> None:
        """Terminate the harness server subprocess."""
        if self._process is not None:
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
            self._process = None

    def _wait_for_ready(self) -> None:
        deadline = time.monotonic() + _STARTUP_TIMEOUT
        while time.monotonic() < deadline:
            try:
                httpx.get(f"{self._base_url}/health", timeout=1.0)
                return
            except Exception:
                time.sleep(0.25)
        raise RuntimeError(
            f"Harness server did not become ready within {_STARTUP_TIMEOUT}s. "
            f"Check that {self._config.harness_dir} is a valid harness installation "
            f"and that port {self._config.port} is free."
        )

    # ------------------------------------------------------------------
    # AgentAdapter contract
    # ------------------------------------------------------------------

    def run(self, task: str, working_dir: Path, timeout: float) -> RunResult:
        """Run the agent on task in working_dir. Blocks until done or timeout."""
        start = time.monotonic()

        httpx.post(
            f"{self._base_url}/run",
            json={
                "task": task,
                "work_dir": str(working_dir),
                "max_turns": self._config.max_turns,
            },
            timeout=10.0,
        )

        while True:
            elapsed = time.monotonic() - start
            if elapsed >= timeout:
                return RunResult(
                    status="timeout",
                    duration=elapsed,
                    logs=[],
                    error=None,
                )

            state = httpx.get(f"{self._base_url}/run/state", timeout=5.0).json()

            if state["done"]:
                return _result_from_events(
                    events=state["events"],
                    duration=time.monotonic() - start,
                )

            time.sleep(_POLL_INTERVAL)

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------

    def __enter__(self) -> CustomHarnessAdapter:
        self.start()
        return self

    def __exit__(self, *_) -> None:
        self.stop()


def _result_from_events(events: list[dict], duration: float) -> RunResult:
    """Scan the event list for the terminal event and map to RunResult.

    Event types come from harness serialization: class name is used as
    the 'type' field (e.g. AgentFinished, AgentFailed).
    """
    for event in reversed(events):
        if event["type"] == "AgentFinished":
            return RunResult(
                status="completed",
                duration=duration,
                logs=events,
                error=None,
            )
        if event["type"] == "AgentFailed":
            return RunResult(
                status="failed",
                duration=duration,
                logs=events,
                error=event.get("error"),
            )

    # done=True but no terminal event — harness exited abnormally
    return RunResult(
        status="failed",
        duration=duration,
        logs=events,
        error="Run ended without AgentFinished or AgentFailed event",
    )
