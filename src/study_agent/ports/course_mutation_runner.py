from __future__ import annotations

from pathlib import Path
from typing import Protocol


class CourseMutationRunner(Protocol):
    async def run(
        self,
        *,
        course_root: Path,
        prompt: str,
        artifact_path: Path,
        stdout_log_path: Path,
        stderr_log_path: Path,
    ) -> None:
        ...
