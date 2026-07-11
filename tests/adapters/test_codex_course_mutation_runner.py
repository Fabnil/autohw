from __future__ import annotations

import asyncio
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from study_agent.adapters.codex_course_mutation_runner import CodexCourseMutationRunner


@dataclass(slots=True)
class FakeProcess:
    returncode: int
    stdout: bytes = b""
    stderr: bytes = b""
    inputs: list[bytes | None] = field(default_factory=list)

    async def communicate(
        self,
        input: bytes | None = None,
    ) -> tuple[bytes, bytes]:
        self.inputs.append(input)
        return self.stdout, self.stderr


@dataclass(frozen=True, slots=True)
class ProcessCall:
    args: tuple[str, ...]
    cwd: str | None


class FakeCreateSubprocessExec:
    def __init__(self, processes: Sequence[FakeProcess]) -> None:
        self._processes = list(processes)
        self.calls: list[ProcessCall] = []

    async def __call__(self, *args: str, **kwargs: object) -> FakeProcess:
        if not self._processes:
            raise AssertionError("No fake processes left")

        cwd = kwargs.get("cwd")
        assert cwd is None or isinstance(cwd, str)
        self.calls.append(
            ProcessCall(
                args=tuple(args),
                cwd=cwd,
            )
        )
        return self._processes.pop(0)


def test_runner_executes_codex_and_writes_logs(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    course_root = (tmp_path / "course-root").resolve()
    course_root.mkdir()
    artifact_path = (tmp_path / "artifact.txt").resolve()
    stdout_log_path = (tmp_path / "stdout.jsonl").resolve()
    stderr_log_path = (tmp_path / "stderr.log").resolve()
    fake_exec = FakeCreateSubprocessExec(
        [
            FakeProcess(returncode=0),
            FakeProcess(returncode=0, stdout=b'{"type":"done"}\n', stderr=b"warning\n"),
        ]
    )
    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_exec)

    asyncio.run(
        CodexCourseMutationRunner().run(
            course_root=course_root,
            prompt="hello",
            artifact_path=artifact_path,
            stdout_log_path=stdout_log_path,
            stderr_log_path=stderr_log_path,
        )
    )

    assert fake_exec.calls[0].args == ("codex", "login", "status")
    assert fake_exec.calls[1].args[:4] == ("codex", "exec", "-C", str(course_root))
    assert fake_exec.calls[1].cwd == str(course_root)
    assert fake_exec._processes == []
    assert stdout_log_path.read_text(encoding="utf-8") == '{"type":"done"}\n'
    assert stderr_log_path.read_text(encoding="utf-8") == "warning\n"


def test_runner_requires_login_when_no_session_and_no_api_key(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    course_root = (tmp_path / "course-root").resolve()
    course_root.mkdir()
    fake_exec = FakeCreateSubprocessExec([FakeProcess(returncode=1)])
    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_exec)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match=r"codex login"):
        asyncio.run(
            CodexCourseMutationRunner().run(
                course_root=course_root,
                prompt="hello",
                artifact_path=(tmp_path / "artifact.txt").resolve(),
                stdout_log_path=(tmp_path / "stdout.jsonl").resolve(),
                stderr_log_path=(tmp_path / "stderr.log").resolve(),
            )
        )


def test_runner_uses_api_key_for_headless_login(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    course_root = (tmp_path / "course-root").resolve()
    course_root.mkdir()
    login_process = FakeProcess(returncode=0)
    fake_exec = FakeCreateSubprocessExec(
        [
            FakeProcess(returncode=1),
            login_process,
            FakeProcess(returncode=0),
        ]
    )
    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_exec)
    monkeypatch.setenv("OPENAI_API_KEY", "secret-key")

    asyncio.run(
        CodexCourseMutationRunner().run(
            course_root=course_root,
            prompt="hello",
            artifact_path=(tmp_path / "artifact.txt").resolve(),
            stdout_log_path=(tmp_path / "stdout.jsonl").resolve(),
            stderr_log_path=(tmp_path / "stderr.log").resolve(),
        )
    )

    assert fake_exec.calls[1].args == ("codex", "login", "--with-api-key")
    assert login_process.inputs == [b"secret-key\n"]


def test_runner_raises_when_headless_login_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    course_root = (tmp_path / "course-root").resolve()
    course_root.mkdir()
    login_process = FakeProcess(returncode=1, stderr=b"bad key\n")
    fake_exec = FakeCreateSubprocessExec(
        [
            FakeProcess(returncode=1),
            login_process,
        ]
    )
    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_exec)
    monkeypatch.setenv("OPENAI_API_KEY", "secret-key")

    with pytest.raises(RuntimeError, match=r"bad key"):
        asyncio.run(
            CodexCourseMutationRunner().run(
                course_root=course_root,
                prompt="hello",
                artifact_path=(tmp_path / "artifact.txt").resolve(),
                stdout_log_path=(tmp_path / "stdout.jsonl").resolve(),
                stderr_log_path=(tmp_path / "stderr.log").resolve(),
            )
        )

    assert login_process.inputs == [b"secret-key\n"]


def test_runner_raises_when_codex_exec_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    course_root = (tmp_path / "course-root").resolve()
    course_root.mkdir()
    stdout_log_path = (tmp_path / "stdout.jsonl").resolve()
    stderr_log_path = (tmp_path / "stderr.log").resolve()
    fake_exec = FakeCreateSubprocessExec(
        [
            FakeProcess(returncode=0),
            FakeProcess(returncode=1, stdout=b"partial\n", stderr=b"boom\n"),
        ]
    )
    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_exec)

    with pytest.raises(RuntimeError, match=r"non-zero exit code"):
        asyncio.run(
            CodexCourseMutationRunner().run(
                course_root=course_root,
                prompt="hello",
                artifact_path=(tmp_path / "artifact.txt").resolve(),
                stdout_log_path=stdout_log_path,
                stderr_log_path=stderr_log_path,
            )
        )

    assert stdout_log_path.read_text(encoding="utf-8") == "partial\n"
    assert stderr_log_path.read_text(encoding="utf-8") == "boom\n"


def test_runner_raises_when_codex_cli_is_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    course_root = (tmp_path / "course-root").resolve()
    course_root.mkdir()

    async def raise_not_found(*args: str, **kwargs: object) -> FakeProcess:
        raise FileNotFoundError

    monkeypatch.setattr(asyncio, "create_subprocess_exec", raise_not_found)

    with pytest.raises(RuntimeError, match=r"not found in PATH"):
        asyncio.run(
            CodexCourseMutationRunner().run(
                course_root=course_root,
                prompt="hello",
                artifact_path=(tmp_path / "artifact.txt").resolve(),
                stdout_log_path=(tmp_path / "stdout.jsonl").resolve(),
                stderr_log_path=(tmp_path / "stderr.log").resolve(),
            )
        )
