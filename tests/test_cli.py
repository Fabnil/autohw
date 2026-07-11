from __future__ import annotations

import importlib
from pathlib import Path

import pytest

from study_agent import __version__
from study_agent.application.course_mutation import CourseMutationResult
from study_agent.domain.course import CourseContext

cli_main_module = importlib.import_module("study_agent.cli.main")


def test_version_constant() -> None:
    assert __version__ == "0.1.0"


def test_main_without_arguments_prints_help(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = cli_main_module.main([])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "usage:" in captured.out


def test_main_dispatches_add_course(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    course_root = (tmp_path / "course-root").resolve()
    course_root.mkdir()
    target_json_path = (
        tmp_path / ".runtime" / "courses" / "by-id" / "linear-algebra.json"
    ).resolve()
    run_dir = (tmp_path / ".runtime" / "runs" / "courses" / "run").resolve()
    captured: dict[str, object] = {}

    async def fake_add_course(command: object, *, workspace_root: Path) -> CourseMutationResult:
        captured["command"] = command
        captured["workspace_root"] = workspace_root
        return CourseMutationResult(
            mode="add",
            course=CourseContext(
                id="linear-algebra",
                title="Linear Algebra",
                description="Course overview.",
                course_root=course_root,
                references=(),
            ),
            target_json_path=target_json_path,
            run_dir=run_dir,
            attempts=1,
        )

    monkeypatch.setattr(cli_main_module, "add_course", fake_add_course)
    monkeypatch.chdir(tmp_path)

    exit_code = cli_main_module.main(
        [
            "add",
            "course",
            "--id",
            "linear-algebra",
            "--title",
            "Linear Algebra",
            "--description",
            "Course overview.",
            "--course-root",
            str(course_root),
        ]
    )
    output = capsys.readouterr()

    assert exit_code == 0
    assert "Added course JSON" in output.out
    assert str(target_json_path) in output.out
    assert str(captured["workspace_root"]) == str(tmp_path.resolve())


def test_main_dispatches_update_course(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    course_root = (tmp_path / "course-root").resolve()
    course_root.mkdir()
    target_json_path = (
        tmp_path / ".runtime" / "courses" / "by-id" / "linear-algebra.json"
    ).resolve()
    run_dir = (tmp_path / ".runtime" / "runs" / "courses" / "run").resolve()

    async def fake_update_course(command: object, *, workspace_root: Path) -> CourseMutationResult:
        assert workspace_root == tmp_path.resolve()
        return CourseMutationResult(
            mode="update",
            course=CourseContext(
                id="linear-algebra",
                title="Linear Algebra",
                description="Updated course overview.",
                course_root=course_root,
                references=(),
            ),
            target_json_path=target_json_path,
            run_dir=run_dir,
            attempts=1,
        )

    monkeypatch.setattr(cli_main_module, "update_course", fake_update_course)
    monkeypatch.chdir(tmp_path)

    exit_code = cli_main_module.main(
        [
            "update",
            "course",
            "--id",
            "linear-algebra",
            "--description",
            "Updated course overview.",
        ]
    )
    output = capsys.readouterr()

    assert exit_code == 0
    assert "Updated course JSON" in output.out


def test_main_returns_error_code_for_application_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    course_root = (tmp_path / "course-root").resolve()
    course_root.mkdir()

    async def fake_add_course(command: object, *, workspace_root: Path) -> CourseMutationResult:
        raise RuntimeError("boom")

    monkeypatch.setattr(cli_main_module, "add_course", fake_add_course)
    monkeypatch.chdir(tmp_path)

    exit_code = cli_main_module.main(
        [
            "add",
            "course",
            "--id",
            "linear-algebra",
            "--title",
            "Linear Algebra",
            "--description",
            "Course overview.",
            "--course-root",
            str(course_root),
        ]
    )
    output = capsys.readouterr()

    assert exit_code == 1
    assert "boom" in output.err
