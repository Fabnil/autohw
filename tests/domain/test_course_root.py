from __future__ import annotations

from pathlib import Path

import pytest

from study_agent.domain.course_root import validate_course_root_structure


def _create_course_root(
    tmp_path: Path,
    name: str = "course-root",
) -> Path:
    course_root = (tmp_path / name).resolve()
    course_root.mkdir()
    return course_root


def test_validate_course_root_structure_allows_empty_directory(tmp_path: Path) -> None:
    course_root = _create_course_root(tmp_path)

    assert validate_course_root_structure(course_root) == course_root


def test_validate_course_root_structure_allows_known_top_level_entries(
    tmp_path: Path,
) -> None:
    course_root = _create_course_root(tmp_path)
    (course_root / ".git").mkdir()
    (course_root / "materials").mkdir()
    (course_root / "assignments").mkdir()
    (course_root / "instructions").mkdir()
    (course_root / ".gitignore").write_text(".venv/\n", encoding="utf-8")
    (course_root / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
    (course_root / "uv.lock").write_text("version = 1\n", encoding="utf-8")

    assert validate_course_root_structure(course_root) == course_root


def test_validate_course_root_structure_allows_gitignored_top_level_entries(
    tmp_path: Path,
) -> None:
    course_root = _create_course_root(tmp_path)
    (course_root / ".gitignore").write_text(".venv/\n*.log\nbuild/\n", encoding="utf-8")
    (course_root / ".venv").mkdir()
    (course_root / "build").mkdir()
    (course_root / "debug.log").write_text("ignored\n", encoding="utf-8")

    assert validate_course_root_structure(course_root) == course_root


def test_validate_course_root_structure_rejects_unknown_top_level_entry(
    tmp_path: Path,
) -> None:
    course_root = _create_course_root(tmp_path)
    (course_root / "unexpected.txt").write_text("boom\n", encoding="utf-8")

    with pytest.raises(ValueError, match=r"Unexpected top-level entry in course_root"):
        validate_course_root_structure(course_root)


def test_validate_course_root_structure_rejects_wrong_directory_type(
    tmp_path: Path,
) -> None:
    course_root = _create_course_root(tmp_path)
    (course_root / "materials").write_text("not a directory\n", encoding="utf-8")

    with pytest.raises(ValueError, match=r"course_root entry must be a directory"):
        validate_course_root_structure(course_root)


def test_validate_course_root_structure_rejects_wrong_file_type(
    tmp_path: Path,
) -> None:
    course_root = _create_course_root(tmp_path)
    (course_root / "uv.lock").mkdir()

    with pytest.raises(ValueError, match=r"course_root entry must be a file"):
        validate_course_root_structure(course_root)


def test_validate_course_root_structure_ignores_nested_structure(tmp_path: Path) -> None:
    course_root = _create_course_root(tmp_path)
    nested_file = course_root / "materials" / "lectures" / "week-01.md"
    nested_file.parent.mkdir(parents=True)
    nested_file.write_text("notes\n", encoding="utf-8")

    assert validate_course_root_structure(course_root) == course_root
