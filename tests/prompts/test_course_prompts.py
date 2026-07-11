from __future__ import annotations

from pathlib import Path

import pytest

from study_agent.prompts.course.create_add_course_prompt import create_add_course_prompt
from study_agent.prompts.course.create_update_course_prompt import (
    create_update_course_prompt,
)


def test_create_add_course_prompt_contains_absolute_paths_and_contract(
    tmp_path: Path,
) -> None:
    course_root = (tmp_path / "course-root").resolve()
    course_root.mkdir()
    target_json_path = (
        tmp_path / ".runtime" / "courses" / "by-id" / "linear-algebra.json"
    ).resolve()
    courses_by_id_root = target_json_path.parent

    prompt = create_add_course_prompt(
        course_id="linear-algebra",
        title="Linear Algebra",
        description="Course overview.",
        course_root=course_root,
        target_json_path=target_json_path,
        courses_by_id_root=courses_by_id_root,
    )

    assert str(course_root) in prompt
    assert str(target_json_path) in prompt
    assert str(courses_by_id_root) in prompt
    assert '"course_root": "/абсолютный/путь/к/корню/курса"' in prompt
    assert '"references": [' in prompt


def test_create_add_course_prompt_rejects_empty_course_id(tmp_path: Path) -> None:
    course_root = (tmp_path / "course-root").resolve()
    course_root.mkdir()

    with pytest.raises(ValueError, match=r"course_id must not be empty"):
        create_add_course_prompt(
            course_id="  ",
            title="Linear Algebra",
            description="Course overview.",
            course_root=course_root,
            target_json_path=(tmp_path / "target.json").resolve(),
            courses_by_id_root=(tmp_path / "courses").resolve(),
        )


def test_create_update_course_prompt_rejects_relative_target_path(
    tmp_path: Path,
) -> None:
    course_root = (tmp_path / "course-root").resolve()
    course_root.mkdir()

    with pytest.raises(ValueError, match=r"target_json_path must be absolute"):
        create_update_course_prompt(
            course_id="linear-algebra",
            title="Linear Algebra",
            description="Updated description.",
            course_root=course_root,
            target_json_path=Path("relative.json"),
            courses_by_id_root=(tmp_path / "courses").resolve(),
        )


def test_create_update_course_prompt_contains_update_invariants(tmp_path: Path) -> None:
    course_root = (tmp_path / "course-root").resolve()
    course_root.mkdir()
    target_json_path = (
        tmp_path / ".runtime" / "courses" / "by-id" / "linear-algebra.json"
    ).resolve()

    prompt = create_update_course_prompt(
        course_id="linear-algebra",
        title="Linear Algebra",
        description="Updated description.",
        course_root=course_root,
        target_json_path=target_json_path,
        courses_by_id_root=target_json_path.parent,
    )

    assert "update course" in prompt
    assert "description должен стать ровно Updated description." in prompt
    assert "Не создавай, не изменяй и не удаляй другие course JSON" in prompt
