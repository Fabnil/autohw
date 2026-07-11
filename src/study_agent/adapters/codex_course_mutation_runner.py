from __future__ import annotations

import asyncio
import os
from pathlib import Path


class CodexCourseMutationRunner:
    async def run(
        self,
        *,
        course_root: Path,
        prompt: str,
        artifact_path: Path,
        stdout_log_path: Path,
        stderr_log_path: Path,
    ) -> None:
        for path in (artifact_path, stdout_log_path, stderr_log_path):
            path.parent.mkdir(parents=True, exist_ok=True)

        await self._ensure_login(course_root=course_root)

        process = await self._create_process(
            "codex",
            "exec",
            "-C",
            str(course_root),
            "--sandbox",
            "danger-full-access",
            "--dangerously-bypass-approvals-and-sandbox",
            "--ephemeral",
            "--json",
            "--output-last-message",
            str(artifact_path),
            "-",
            course_root=course_root,
        )

        stdout, stderr = await process.communicate(prompt.encode())
        stdout_log_path.write_bytes(stdout)
        stderr_log_path.write_bytes(stderr)

        if process.returncode != 0:
            raise RuntimeError(
                "Codex CLI failed with a non-zero exit code. "
                f"See logs: {stdout_log_path} and {stderr_log_path}"
            )

    async def _ensure_login(
        self,
        *,
        course_root: Path,
    ) -> None:
        status_process = await self._create_process(
            "codex",
            "login",
            "status",
            course_root=course_root,
        )
        _, _ = await status_process.communicate()
        if status_process.returncode == 0:
            return

        api_key = os.environ.get("OPENAI_API_KEY")
        if api_key is None:
            raise RuntimeError(
                "Codex CLI is not logged in. Run `codex login` or set `OPENAI_API_KEY` "
                "for one-shot headless login."
            )

        login_process = await self._create_process(
            "codex",
            "login",
            "--with-api-key",
            course_root=course_root,
        )
        _, stderr = await login_process.communicate(f"{api_key}\n".encode())
        if login_process.returncode != 0:
            stderr_text = stderr.decode("utf-8", errors="replace").strip()
            raise RuntimeError(
                "Failed to authenticate Codex CLI using `OPENAI_API_KEY`. "
                f"Run `codex login`. Details: {stderr_text or 'no stderr output'}"
            )

    async def _create_process(
        self,
        *args: str,
        course_root: Path,
    ) -> asyncio.subprocess.Process:
        try:
            return await asyncio.create_subprocess_exec(
                *args,
                cwd=str(course_root),
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except FileNotFoundError as error:
            raise RuntimeError("`codex` CLI is not installed or not found in PATH") from error
