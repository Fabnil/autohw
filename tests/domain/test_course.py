from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path

import pytest
from pydantic import ValidationError
from pydantic_core import ErrorDetails

from study_agent.domain.context_reference import ContextReference
from study_agent.domain.course import CourseContext, CoursesCatalog

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures"
COURSE_FIXTURES_DIR = FIXTURES_DIR / "domain" / "course"
FILES_FIXTURES_DIR = FIXTURES_DIR / "files"
COURSE_ID = "linear-algebra"
COURSE_TITLE = "Linear Algebra"


def _assert_single_error(
    errors: Sequence[ErrorDetails],
    *,
    loc: tuple[object, ...],
    type_: str,
    msg: str | None = None,
    msg_contains: str | None = None,
) -> None:
    assert len(errors) == 1

    error = errors[0]
    assert tuple(error["loc"]) == loc
    assert error["type"] == type_

    actual_message = str(error["msg"])
    if msg is not None:
        assert actual_message == msg
    if msg_contains is not None:
        assert msg_contains in actual_message


def _create_course_root(
    tmp_path: Path,
    name: str = "course-root",
) -> Path:
    course_root = (tmp_path / name).resolve()
    course_root.mkdir()
    return course_root


def _render_course_fixture(
    tmp_path: Path,
    fixture_name: str,
    *,
    course_root: Path,
) -> Path:
    fixture_text = (COURSE_FIXTURES_DIR / fixture_name).read_text(encoding="utf-8")
    rendered_text = (
        fixture_text.replace(
            "__REFERENCE_A__",
            str((FILES_FIXTURES_DIR / "reference_a.md").resolve()),
        )
        .replace(
            "__REFERENCE_B__",
            str((FILES_FIXTURES_DIR / "reference_b.md").resolve()),
        )
        .replace("__COURSE_ROOT__", str(course_root))
    )

    rendered_path = tmp_path / fixture_name
    rendered_path.write_text(rendered_text, encoding="utf-8")
    return rendered_path.resolve()


def test_course_context_from_json_parses_valid_manifest(tmp_path: Path) -> None:
    course_root = _create_course_root(tmp_path)
    context_json_path = _render_course_fixture(
        tmp_path,
        "valid_context.json",
        course_root=course_root,
    )

    context = CourseContext.from_json(context_json_path=context_json_path)

    assert context == CourseContext(
        id=COURSE_ID,
        title=COURSE_TITLE,
        description="Course overview and important conventions.",
        course_root=course_root,
        references=(
            ContextReference(
                path=(FILES_FIXTURES_DIR / "reference_a.md").resolve(),
                summary="Core course instructions.",
                location="entire file",
            ),
            ContextReference(
                path=(FILES_FIXTURES_DIR / "reference_b.md").resolve(),
                summary="Primary formulas and notation reference.",
                location="pages 1-3",
            ),
        ),
    )


def test_course_context_from_json_allows_empty_references(tmp_path: Path) -> None:
    course_root = _create_course_root(tmp_path)
    context_json_path = _render_course_fixture(
        tmp_path,
        "empty_references.json",
        course_root=course_root,
    )

    context = CourseContext.from_json(context_json_path=context_json_path)

    assert context == CourseContext(
        id=COURSE_ID,
        title=COURSE_TITLE,
        description="Course overview without curated references yet.",
        course_root=course_root,
        references=(),
    )


def test_course_context_normalizes_values_and_reference_list(tmp_path: Path) -> None:
    course_root = _create_course_root(tmp_path)
    context = CourseContext(
        id="  linear-algebra  ",
        title="  Linear Algebra  ",
        description="  Course overview and important conventions.  ",
        course_root=course_root,
        references=[  # type: ignore[arg-type]
            ContextReference(
                path=(FILES_FIXTURES_DIR / "reference_a.md").resolve(),
                summary="  Core course instructions.  ",
                location="  entire file  ",
            )
        ],
    )

    assert context.id == COURSE_ID
    assert context.title == COURSE_TITLE
    assert context.description == "Course overview and important conventions."
    assert isinstance(context.references, tuple)
    assert context.references[0].summary == "Core course instructions."
    assert context.references[0].location == "entire file"


def test_course_context_rejects_relative_course_root() -> None:
    with pytest.raises(ValidationError) as exc_info:
        CourseContext(
            id=COURSE_ID,
            title=COURSE_TITLE,
            description="Course overview.",
            course_root=Path("relative-course-root"),
            references=(),
        )

    _assert_single_error(
        exc_info.value.errors(include_url=False),
        loc=("course_root",),
        type_="path_not_absolute",
        msg="path must be absolute",
    )


def test_course_context_rejects_missing_course_root_directory(tmp_path: Path) -> None:
    missing_root = (tmp_path / "missing-root").resolve()

    with pytest.raises(ValidationError) as exc_info:
        CourseContext(
            id=COURSE_ID,
            title=COURSE_TITLE,
            description="Course overview.",
            course_root=missing_root,
            references=(),
        )

    _assert_single_error(
        exc_info.value.errors(include_url=False),
        loc=("course_root",),
        type_="path_not_directory",
        msg="path must point to an existing directory",
    )


def test_course_context_rejects_non_context_reference_item(tmp_path: Path) -> None:
    course_root = _create_course_root(tmp_path)

    with pytest.raises(ValidationError) as exc_info:
        CourseContext(
            id=COURSE_ID,
            title=COURSE_TITLE,
            description="Course overview and important conventions.",
            course_root=course_root,
            references=("not-a-reference",),  # type: ignore[arg-type]
        )

    _assert_single_error(
        exc_info.value.errors(include_url=False),
        loc=("references", 0),
        type_="model_type",
        msg_contains="valid dictionary or instance of ContextReference",
    )


def test_course_context_rejects_duplicate_reference_paths(tmp_path: Path) -> None:
    course_root = _create_course_root(tmp_path)
    reference_path = (FILES_FIXTURES_DIR / "reference_a.md").resolve()

    with pytest.raises(ValidationError) as exc_info:
        CourseContext(
            id=COURSE_ID,
            title=COURSE_TITLE,
            description="Course overview and important conventions.",
            course_root=course_root,
            references=(
                ContextReference(
                    path=reference_path,
                    summary="Core course instructions.",
                ),
                ContextReference(
                    path=reference_path,
                    summary="Another explanation for the same file.",
                ),
            ),
        )

    _assert_single_error(
        exc_info.value.errors(include_url=False),
        loc=(),
        type_="duplicate_reference_paths",
        msg="references must not contain duplicate paths",
    )


def test_course_context_from_json_validates_wrapper_path() -> None:
    with pytest.raises(ValidationError) as exc_info:
        CourseContext.from_json(context_json_path=Path("context.json"))

    _assert_single_error(
        exc_info.value.errors(include_url=False),
        loc=("context_json_path",),
        type_="path_not_absolute",
        msg="path must be absolute",
    )


def test_course_context_from_json_rejects_unknown_root_field(tmp_path: Path) -> None:
    course_root = _create_course_root(tmp_path)
    context_json_path = _render_course_fixture(
        tmp_path,
        "unknown_field.json",
        course_root=course_root,
    )

    with pytest.raises(ValidationError) as exc_info:
        CourseContext.from_json(context_json_path=context_json_path)

    _assert_single_error(
        exc_info.value.errors(include_url=False),
        loc=("extra",),
        type_="extra_forbidden",
        msg="Extra inputs are not permitted",
    )


def test_course_context_from_json_rejects_non_string_description(tmp_path: Path) -> None:
    course_root = _create_course_root(tmp_path)
    context_json_path = _render_course_fixture(
        tmp_path,
        "description_not_string.json",
        course_root=course_root,
    )

    with pytest.raises(ValidationError) as exc_info:
        CourseContext.from_json(context_json_path=context_json_path)

    _assert_single_error(
        exc_info.value.errors(include_url=False),
        loc=("description",),
        type_="string_type",
        msg="Input should be a valid string",
    )


def test_course_context_from_json_rejects_missing_required_field(tmp_path: Path) -> None:
    course_root = _create_course_root(tmp_path)
    context_json_path = (tmp_path / "missing_references.json").resolve()
    context_json_path.write_text(
        json.dumps(
            {
                "id": COURSE_ID,
                "title": COURSE_TITLE,
                "description": "Course overview and important conventions.",
                "course_root": str(course_root),
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValidationError) as exc_info:
        CourseContext.from_json(context_json_path=context_json_path)

    _assert_single_error(
        exc_info.value.errors(include_url=False),
        loc=("references",),
        type_="missing",
        msg="Field required",
    )


def test_course_context_from_json_rejects_invalid_reference_item(tmp_path: Path) -> None:
    course_root = _create_course_root(tmp_path)
    context_json_path = _render_course_fixture(
        tmp_path,
        "invalid_reference_type.json",
        course_root=course_root,
    )

    with pytest.raises(ValidationError) as exc_info:
        CourseContext.from_json(context_json_path=context_json_path)

    _assert_single_error(
        exc_info.value.errors(include_url=False),
        loc=("references", 1, "path"),
        type_="path_type",
        msg_contains="Input is not a valid path",
    )


def test_course_context_from_json_rejects_malformed_json(tmp_path: Path) -> None:
    course_root = _create_course_root(tmp_path)
    context_json_path = _render_course_fixture(
        tmp_path,
        "malformed.json",
        course_root=course_root,
    )

    with pytest.raises(ValidationError) as exc_info:
        CourseContext.from_json(context_json_path=context_json_path)

    _assert_single_error(
        exc_info.value.errors(include_url=False),
        loc=(),
        type_="json_invalid",
        msg_contains="Invalid JSON",
    )


def test_course_context_from_json_rejects_invalid_utf8_json(tmp_path: Path) -> None:
    context_json_path = (tmp_path / "context.json").resolve()
    context_json_path.write_bytes(b"\xff")

    with pytest.raises(ValidationError) as exc_info:
        CourseContext.from_json(context_json_path=context_json_path)

    _assert_single_error(
        exc_info.value.errors(include_url=False),
        loc=(),
        type_="json_invalid",
        msg_contains="Invalid JSON",
    )


def test_courses_catalog_from_course_json_files_returns_sorted_courses(
    tmp_path: Path,
) -> None:
    courses_dir = (tmp_path / "courses").resolve()
    courses_dir.mkdir()
    course_root_a = _create_course_root(tmp_path, "course-a")
    course_root_b = _create_course_root(tmp_path, "course-b")

    (courses_dir / "statistics.json").write_text(
        CourseContext(
            id="statistics",
            title="Statistics",
            description="Probability and inference course.",
            course_root=course_root_b,
            references=(),
        ).to_json_text(),
        encoding="utf-8",
    )
    (courses_dir / "linear-algebra.json").write_text(
        CourseContext(
            id=COURSE_ID,
            title=COURSE_TITLE,
            description="Course overview and important conventions.",
            course_root=course_root_a,
            references=(),
        ).to_json_text(),
        encoding="utf-8",
    )

    catalog = CoursesCatalog.from_course_json_files(courses_dir=courses_dir)

    assert tuple(course.id for course in catalog.courses) == ("linear-algebra", "statistics")


def test_courses_catalog_from_course_json_files_rejects_duplicate_ids(
    tmp_path: Path,
) -> None:
    courses_dir = (tmp_path / "courses").resolve()
    courses_dir.mkdir()
    course_root_a = _create_course_root(tmp_path, "course-a")
    course_root_b = _create_course_root(tmp_path, "course-b")

    (courses_dir / "first.json").write_text(
        CourseContext(
            id=COURSE_ID,
            title=COURSE_TITLE,
            description="First course.",
            course_root=course_root_a,
            references=(),
        ).to_json_text(),
        encoding="utf-8",
    )
    (courses_dir / "second.json").write_text(
        CourseContext(
            id=COURSE_ID,
            title="Another title",
            description="Duplicate id.",
            course_root=course_root_b,
            references=(),
        ).to_json_text(),
        encoding="utf-8",
    )

    with pytest.raises(ValidationError) as exc_info:
        CoursesCatalog.from_course_json_files(courses_dir=courses_dir)

    _assert_single_error(
        exc_info.value.errors(include_url=False),
        loc=(),
        type_="duplicate_course_id",
        msg="courses must not contain duplicate ids",
    )


def test_courses_catalog_from_course_json_files_rejects_duplicate_course_roots(
    tmp_path: Path,
) -> None:
    courses_dir = (tmp_path / "courses").resolve()
    courses_dir.mkdir()
    course_root = _create_course_root(tmp_path, "course-a")

    (courses_dir / "first.json").write_text(
        CourseContext(
            id=COURSE_ID,
            title=COURSE_TITLE,
            description="First course.",
            course_root=course_root,
            references=(),
        ).to_json_text(),
        encoding="utf-8",
    )
    (courses_dir / "second.json").write_text(
        CourseContext(
            id="statistics",
            title="Statistics",
            description="Duplicate root.",
            course_root=course_root,
            references=(),
        ).to_json_text(),
        encoding="utf-8",
    )

    with pytest.raises(ValidationError) as exc_info:
        CoursesCatalog.from_course_json_files(courses_dir=courses_dir)

    _assert_single_error(
        exc_info.value.errors(include_url=False),
        loc=(),
        type_="duplicate_course_root",
        msg="courses must not contain duplicate course_root values",
    )


def test_courses_catalog_from_course_json_files_returns_empty_for_missing_directory(
    tmp_path: Path,
) -> None:
    catalog = CoursesCatalog.from_course_json_files(
        courses_dir=(tmp_path / "missing-courses").resolve()
    )

    assert catalog.courses == ()
