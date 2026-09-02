"""Environment — isolated working directory for one evaluation run."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path


class Environment:
    """Manages an isolated filesystem workspace for a single evaluation run.

    The caller is responsible for passing an absolute, resolved source_path.
    Relative paths are resolved against the current working directory at
    prepare() time, which may not be what you want.

    Usage:
        with Environment(source_path) as working_dir:
            # agent writes here
            # evaluator reads from here
    """

    def __init__(self, source_path: Path) -> None:
        self._source_path = source_path
        self._working_dir: Path | None = None

    def prepare(self) -> Path:
        """Create a temp directory and copy the source repo into it.

        Returns the path to the working directory.
        """
        self._working_dir = Path(tempfile.mkdtemp(prefix="eval-"))
        shutil.copytree(self._source_path, self._working_dir, dirs_exist_ok=True)
        return self._working_dir

    def cleanup(self) -> None:
        """Delete the working directory. Safe to call even if prepare() failed."""
        if self._working_dir and self._working_dir.exists():
            shutil.rmtree(self._working_dir)
            self._working_dir = None

    def __enter__(self) -> Path:
        return self.prepare()

    def __exit__(self, *_) -> None:
        self.cleanup()
