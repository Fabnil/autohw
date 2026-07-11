from __future__ import annotations

import asyncio
import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import pytest

from study_agent.application.course_mutation import (
    AddCourseCommand,
    UpdateCourseCommand,
    add_course,
    update_course,
)
from study_agent.domain.course import CourseContext, CoursesCatalog

CourseMutationAction = Callable[[Path, str, Path, Path, Path], None]


@dataclass(frozen=True, slots=True)
class RunnerCall:
    course_root: Path
    prompt: str
    artifact_path: Path
    stdout_log_path: Path
    stderr_log_path: Path


class FakeCourseMutationRunner:
    def __init__(self, actions: list[CourseMutationAction]) -> None:
        self._actions = actions
        self.calls: list[RunnerCall] = []

    async def run(
        self,
        *,
        course_root: Path,
        prompt: str,
        artifact_path: Path,
        stdout_log_path: Path,
        stderr_log_path: Path,
    ) -> None:
        self.calls.append(
            RunnerCall(
                course_root=course_root,
                prompt=prompt,
                artifact_path=artifact_path,
                stdout_log_path=stdout_log_path,
                stderr_log_path=stderr_log_path,
            )
        )
        artifact_path.write_text("done\n", encoding="utf-8")
        stdout_log_path.write_text('{"event":"done"}\n', encoding="utf-8")
        stderr_log_path.write_text("", encoding="utf-8")

        if self._actions:
            action = self._actions.pop(0)
            action(
                course_root,
                prompt,
                artifact_path,
                stdout_log_path,
                stderr_log_path,
            )


def _create_course_root(
    tmp_path: Path,
    name: str = "course-root",
) -> Path:
    course_root = (tmp_path / name).resolve()
    course_root.mkdir()
    return course_root


def _write_course_json(
    path: Path,
    *,
    course_id: str,
    title: str,
    description: str,
    course_root: Path,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        CourseContext(
            id=course_id,
            title=title,
            description=description,
            course_root=course_root,
            references=(),
        ).to_json_text(),
        encoding="utf-8",
    )


def _write_invalid_course_json(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"id": "broken"}),
        encoding="utf-8",
    )


def test_add_course_happy_path(tmp_path: Path) -> None:
    workspace_root = tmp_path.resolve()
    course_root = _create_course_root(tmp_path)
    target_json_path = workspace_root / ".runtime" / "courses" / "by-id" / "linear-algebra.json"

    def write_target(
        course_root_arg: Path,
        prompt: str,
        artifact_path: Path,
        stdout_log_path: Path,
        stderr_log_path: Path,
    ) -> None:
        assert course_root_arg == course_root
        assert str(target_json_path) in prompt
        _write_course_json(
            target_json_path,
            course_id="linear-algebra",
            title="Linear Algebra",
            description="Course overview.",
            course_root=course_root,
        )

    runner = FakeCourseMutationRunner([write_target])

    result = asyncio.run(
        add_course(
            AddCourseCommand(
                id="linear-algebra",
                title="Linear Algebra",
                description="Course overview.",
                course_root=course_root,
            ),
            workspace_root=workspace_root,
            runner=runner,
        )
    )

    assert result.mode == "add"
    assert result.attempts == 1
    assert result.target_json_path == target_json_path
    assert result.course.description == "Course overview."
    assert CoursesCatalog.from_course_json_files(
        courses_dir=result.target_json_path.parent
    ).courses == (result.course,)
    assert tuple((workspace_root / ".runtime" / "courses").glob("*.json")) == ()


def test_update_course_happy_path(tmp_path: Path) -> None:
    workspace_root = tmp_path.resolve()
    course_root = _create_course_root(tmp_path)
    target_json_path = workspace_root / ".runtime" / "courses" / "by-id" / "linear-algebra.json"
    _write_course_json(
        target_json_path,
        course_id="linear-algebra",
        title="Linear Algebra",
        description="Old description.",
        course_root=course_root,
    )

    def rewrite_target(
        course_root_arg: Path,
        prompt: str,
        artifact_path: Path,
        stdout_log_path: Path,
        stderr_log_path: Path,
    ) -> None:
        assert course_root_arg == course_root
        assert "Updated description." in prompt
        _write_course_json(
            target_json_path,
            course_id="linear-algebra",
            title="Linear Algebra",
            description="Updated description.",
            course_root=course_root,
        )

    runner = FakeCourseMutationRunner([rewrite_target])

    result = asyncio.run(
        update_course(
            UpdateCourseCommand(
                id="linear-algebra",
                description="Updated description.",
            ),
            workspace_root=workspace_root,
            runner=runner,
        )
    )

    assert result.mode == "update"
    assert result.attempts == 1
    assert result.course.description == "Updated description."
    assert CoursesCatalog.from_course_json_files(
        courses_dir=result.target_json_path.parent
    ).courses == (result.course,)
    assert tuple((workspace_root / ".runtime" / "courses").glob("*.json")) == ()


def test_add_course_retries_when_target_json_missing(tmp_path: Path) -> None:
    workspace_root = tmp_path.resolve()
    course_root = _create_course_root(tmp_path)
    target_json_path = workspace_root / ".runtime" / "courses" / "by-id" / "linear-algebra.json"

    def do_nothing(
        course_root_arg: Path,
        prompt: str,
        artifact_path: Path,
        stdout_log_path: Path,
        stderr_log_path: Path,
    ) -> None:
        assert course_root_arg == course_root

    def write_target(
        course_root_arg: Path,
        prompt: str,
        artifact_path: Path,
        stdout_log_path: Path,
        stderr_log_path: Path,
    ) -> None:
        assert "Target course JSON was not created" in prompt
        _write_course_json(
            target_json_path,
            course_id="linear-algebra",
            title="Linear Algebra",
            description="Course overview.",
            course_root=course_root_arg,
        )

    runner = FakeCourseMutationRunner([do_nothing, write_target])

    result = asyncio.run(
        add_course(
            AddCourseCommand(
                id="linear-algebra",
                title="Linear Algebra",
                description="Course overview.",
                course_root=course_root,
            ),
            workspace_root=workspace_root,
            runner=runner,
        )
    )

    assert result.attempts == 2
    assert len(runner.calls) == 2


def test_add_course_retries_when_target_json_invalid(tmp_path: Path) -> None:
    workspace_root = tmp_path.resolve()
    course_root = _create_course_root(tmp_path)
    target_json_path = workspace_root / ".runtime" / "courses" / "by-id" / "linear-algebra.json"

    def write_invalid(
        course_root_arg: Path,
        prompt: str,
        artifact_path: Path,
        stdout_log_path: Path,
        stderr_log_path: Path,
    ) -> None:
        _write_invalid_course_json(target_json_path)

    def write_valid(
        course_root_arg: Path,
        prompt: str,
        artifact_path: Path,
        stdout_log_path: Path,
        stderr_log_path: Path,
    ) -> None:
        assert "Target course JSON is invalid" in prompt
        _write_course_json(
            target_json_path,
            course_id="linear-algebra",
            title="Linear Algebra",
            description="Course overview.",
            course_root=course_root_arg,
        )

    runner = FakeCourseMutationRunner([write_invalid, write_valid])

    result = asyncio.run(
        add_course(
            AddCourseCommand(
                id="linear-algebra",
                title="Linear Algebra",
                description="Course overview.",
                course_root=course_root,
            ),
            workspace_root=workspace_root,
            runner=runner,
        )
    )

    assert result.attempts == 2


def test_add_course_retries_when_extra_course_json_is_touched(tmp_path: Path) -> None:
    workspace_root = tmp_path.resolve()
    course_root = _create_course_root(tmp_path)
    target_json_path = workspace_root / ".runtime" / "courses" / "by-id" / "linear-algebra.json"
    extra_json_path = workspace_root / ".runtime" / "courses" / "by-id" / "extra.json"

    def write_target_and_extra(
        course_root_arg: Path,
        prompt: str,
        artifact_path: Path,
        stdout_log_path: Path,
        stderr_log_path: Path,
    ) -> None:
        _write_course_json(
            target_json_path,
            course_id="linear-algebra",
            title="Linear Algebra",
            description="Course overview.",
            course_root=course_root_arg,
        )
        _write_course_json(
            extra_json_path,
            course_id="extra",
            title="Extra",
            description="Unexpected extra file.",
            course_root=course_root_arg,
        )

    def fix_target_only(
        course_root_arg: Path,
        prompt: str,
        artifact_path: Path,
        stdout_log_path: Path,
        stderr_log_path: Path,
    ) -> None:
        assert "Only the target course JSON may change" in prompt
        if extra_json_path.exists():
            extra_json_path.unlink()
        _write_course_json(
            target_json_path,
            course_id="linear-algebra",
            title="Linear Algebra",
            description="Course overview.",
            course_root=course_root_arg,
        )

    runner = FakeCourseMutationRunner([write_target_and_extra, fix_target_only])

    result = asyncio.run(
        add_course(
            AddCourseCommand(
                id="linear-algebra",
                title="Linear Algebra",
                description="Course overview.",
                course_root=course_root,
            ),
            workspace_root=workspace_root,
            runner=runner,
        )
    )

    assert result.attempts == 2
    assert not extra_json_path.exists()


def test_add_course_fails_after_three_bad_attempts(tmp_path: Path) -> None:
    workspace_root = tmp_path.resolve()
    course_root = _create_course_root(tmp_path)

    def do_nothing(
        course_root_arg: Path,
        prompt: str,
        artifact_path: Path,
        stdout_log_path: Path,
        stderr_log_path: Path,
    ) -> None:
        assert course_root_arg == course_root

    runner = FakeCourseMutationRunner([do_nothing, do_nothing, do_nothing])

    with pytest.raises(RuntimeError, match=r"failed after 3 attempts"):
        asyncio.run(
            add_course(
                AddCourseCommand(
                    id="linear-algebra",
                    title="Linear Algebra",
                    description="Course overview.",
                    course_root=course_root,
                ),
                workspace_root=workspace_root,
                runner=runner,
            )
        )


def test_add_course_rejects_duplicate_id(tmp_path: Path) -> None:
    workspace_root = tmp_path.resolve()
    course_root = _create_course_root(tmp_path, "course-a")
    other_root = _create_course_root(tmp_path, "course-b")
    target_json_path = workspace_root / ".runtime" / "courses" / "by-id" / "linear-algebra.json"
    _write_course_json(
        target_json_path,
        course_id="linear-algebra",
        title="Linear Algebra",
        description="Existing course.",
        course_root=other_root,
    )

    with pytest.raises(ValueError, match=r"already exists"):
        asyncio.run(
            add_course(
                AddCourseCommand(
                    id="linear-algebra",
                    title="Linear Algebra",
                    description="Course overview.",
                    course_root=course_root,
                ),
                workspace_root=workspace_root,
                runner=FakeCourseMutationRunner([]),
            )
        )


def test_add_course_rejects_duplicate_course_root(tmp_path: Path) -> None:
    workspace_root = tmp_path.resolve()
    course_root = _create_course_root(tmp_path, "course-a")
    existing_json_path = workspace_root / ".runtime" / "courses" / "by-id" / "existing.json"
    _write_course_json(
        existing_json_path,
        course_id="existing",
        title="Existing",
        description="Existing course.",
        course_root=course_root,
    )

    with pytest.raises(ValueError, match=r"same course_root already exists"):
        asyncio.run(
            add_course(
                AddCourseCommand(
                    id="linear-algebra",
                    title="Linear Algebra",
                    description="Course overview.",
                    course_root=course_root,
                ),
                workspace_root=workspace_root,
                runner=FakeCourseMutationRunner([]),
            )
        )


def test_add_course_rejects_invalid_course_root_structure(tmp_path: Path) -> None:
    workspace_root = tmp_path.resolve()
    course_root = _create_course_root(tmp_path)
    (course_root / "unexpected.txt").write_text("boom\n", encoding="utf-8")
    runner = FakeCourseMutationRunner([])

    with pytest.raises(ValueError, match=r"Unexpected top-level entry in course_root"):
        asyncio.run(
            add_course(
                AddCourseCommand(
                    id="linear-algebra",
                    title="Linear Algebra",
                    description="Course overview.",
                    course_root=course_root,
                ),
                workspace_root=workspace_root,
                runner=runner,
            )
        )

    assert runner.calls == []


def test_update_course_rejects_unknown_course_id(tmp_path: Path) -> None:
    workspace_root = tmp_path.resolve()

    with pytest.raises(ValueError, match=r"does not exist"):
        asyncio.run(
            update_course(
                UpdateCourseCommand(
                    id="linear-algebra",
                    description="Updated description.",
                ),
                workspace_root=workspace_root,
                runner=FakeCourseMutationRunner([]),
            )
        )


def test_update_course_rejects_invalid_stored_course_root(tmp_path: Path) -> None:
    workspace_root = tmp_path.resolve()
    course_root = _create_course_root(tmp_path)
    target_json_path = workspace_root / ".runtime" / "courses" / "by-id" / "linear-algebra.json"
    _write_course_json(
        target_json_path,
        course_id="linear-algebra",
        title="Linear Algebra",
        description="Old description.",
        course_root=course_root,
    )
    (course_root / "unexpected.txt").write_text("boom\n", encoding="utf-8")
    runner = FakeCourseMutationRunner([])

    with pytest.raises(ValueError, match=r"Unexpected top-level entry in course_root"):
        asyncio.run(
            update_course(
                UpdateCourseCommand(
                    id="linear-algebra",
                    description="Updated description.",
                ),
                workspace_root=workspace_root,
                runner=runner,
            )
        )

    assert runner.calls == []


def test_update_course_retries_when_immutable_field_changes(tmp_path: Path) -> None:
    workspace_root = tmp_path.resolve()
    course_root = _create_course_root(tmp_path)
    target_json_path = workspace_root / ".runtime" / "courses" / "by-id" / "linear-algebra.json"
    _write_course_json(
        target_json_path,
        course_id="linear-algebra",
        title="Linear Algebra",
        description="Old description.",
        course_root=course_root,
    )

    def write_invalid_title(
        course_root_arg: Path,
        prompt: str,
        artifact_path: Path,
        stdout_log_path: Path,
        stderr_log_path: Path,
    ) -> None:
        _write_course_json(
            target_json_path,
            course_id="linear-algebra",
            title="Wrong Title",
            description="Updated description.",
            course_root=course_root_arg,
        )

    def write_valid(
        course_root_arg: Path,
        prompt: str,
        artifact_path: Path,
        stdout_log_path: Path,
        stderr_log_path: Path,
    ) -> None:
        assert "title must stay exactly `Linear Algebra`" in prompt
        _write_course_json(
            target_json_path,
            course_id="linear-algebra",
            title="Linear Algebra",
            description="Updated description.",
            course_root=course_root_arg,
        )

    runner = FakeCourseMutationRunner([write_invalid_title, write_valid])

    result = asyncio.run(
        update_course(
            UpdateCourseCommand(
                id="linear-algebra",
                description="Updated description.",
            ),
            workspace_root=workspace_root,
            runner=runner,
        )
    )

    assert result.attempts == 2
