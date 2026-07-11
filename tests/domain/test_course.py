from __future__ import annotations

from pathlib import Path

import pytest

from study_agent.domain.context_reference import ContextReference
from study_agent.domain.course import CourseContext

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures"
COURSE_FIXTURES_DIR = FIXTURES_DIR / "domain" / "course"
FILES_FIXTURES_DIR = FIXTURES_DIR / "files"
COURSE_ID = "linear-algebra"
COURSE_TITLE = "Linear Algebra"


def _render_course_fixture(
    tmp_path: Path,
    fixture_name: str,
) -> Path:
    fixture_text = (COURSE_FIXTURES_DIR / fixture_name).read_text(encoding="utf-8")
    rendered_text = fixture_text.replace(
        "__REFERENCE_A__",
        str((FILES_FIXTURES_DIR / "reference_a.md").resolve()),
    ).replace(
        "__REFERENCE_B__",
        str((FILES_FIXTURES_DIR / "reference_b.md").resolve()),
    )

    rendered_path = tmp_path / fixture_name
    rendered_path.write_text(rendered_text, encoding="utf-8")
    return rendered_path


def test_course_context_from_json_parses_valid_manifest(tmp_path: Path) -> None:
    context_json_path = _render_course_fixture(
        tmp_path,
        "valid_context.json",
    )

    context = CourseContext.from_json(
        id=COURSE_ID,
        title=COURSE_TITLE,
        context_json_path=context_json_path,
    )

    assert context == CourseContext(
        id=COURSE_ID,
        title=COURSE_TITLE,
        description="Course overview and important conventions.",
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
    context_json_path = _render_course_fixture(
        tmp_path,
        "empty_references.json",
    )

    context = CourseContext.from_json(
        id=COURSE_ID,
        title=COURSE_TITLE,
        context_json_path=context_json_path,
    )

    assert context == CourseContext(
        id=COURSE_ID,
        title=COURSE_TITLE,
        description="Course overview without curated references yet.",
        references=(),
    )


def test_course_context_rejects_non_tuple_references() -> None:
    with pytest.raises(
        ValueError,
        match=r"CourseContext.references must be a tuple",
    ):
        CourseContext(
            id=COURSE_ID,
            title=COURSE_TITLE,
            description="Course overview and important conventions.",
            references=[],  # type: ignore[arg-type]
        )


def test_course_context_rejects_non_context_reference_item() -> None:
    with pytest.raises(
        ValueError,
        match=r"CourseContext.references\[0\] must be a ContextReference",
    ):
        CourseContext(
            id=COURSE_ID,
            title=COURSE_TITLE,
            description="Course overview and important conventions.",
            references=("not-a-reference",),  # type: ignore[arg-type]
        )


def test_course_context_rejects_empty_id() -> None:
    with pytest.raises(
        ValueError,
        match=r"CourseContext.id must not be empty",
    ):
        CourseContext(
            id="  ",
            title=COURSE_TITLE,
            description="Course overview and important conventions.",
            references=(),
        )


def test_course_context_rejects_empty_title() -> None:
    with pytest.raises(
        ValueError,
        match=r"CourseContext.title must not be empty",
    ):
        CourseContext(
            id=COURSE_ID,
            title="",
            description="Course overview and important conventions.",
            references=(),
        )


def test_course_context_from_json_rejects_unknown_root_field(tmp_path: Path) -> None:
    context_json_path = _render_course_fixture(
        tmp_path,
        "unknown_field.json",
    )

    with pytest.raises(
        ValueError,
        match=r"CourseContext contains unknown fields: \['extra'\]",
    ):
        CourseContext.from_json(
            id=COURSE_ID,
            title=COURSE_TITLE,
            context_json_path=context_json_path,
        )


def test_course_context_from_json_rejects_non_string_description(tmp_path: Path) -> None:
    context_json_path = _render_course_fixture(
        tmp_path,
        "description_not_string.json",
    )

    with pytest.raises(
        ValueError,
        match=r"CourseContext.description must be a string",
    ):
        CourseContext.from_json(
            id=COURSE_ID,
            title=COURSE_TITLE,
            context_json_path=context_json_path,
        )


def test_course_context_from_json_wraps_invalid_reference_error_with_index(
    tmp_path: Path,
) -> None:
    context_json_path = _render_course_fixture(
        tmp_path,
        "invalid_reference_type.json",
    )

    with pytest.raises(
        ValueError,
        match=(
            r"Invalid CourseContext reference at index 1: "
            r"ContextReference.path must be a string"
        ),
    ):
        CourseContext.from_json(
            id=COURSE_ID,
            title=COURSE_TITLE,
            context_json_path=context_json_path,
        )


def test_course_context_from_json_rejects_duplicate_reference_paths(tmp_path: Path) -> None:
    context_json_path = _render_course_fixture(
        tmp_path,
        "duplicate_reference_paths.json",
    )

    with pytest.raises(
        ValueError,
        match=r"CourseContext.references must not contain duplicate paths",
    ):
        CourseContext.from_json(
            id=COURSE_ID,
            title=COURSE_TITLE,
            context_json_path=context_json_path,
        )


def test_course_context_from_json_rejects_malformed_json(tmp_path: Path) -> None:
    context_json_path = _render_course_fixture(
        tmp_path,
        "malformed.json",
    )

    with pytest.raises(
        ValueError,
        match=rf"Invalid JSON in {context_json_path}: line \d+, column \d+: .*",
    ):
        CourseContext.from_json(
            id=COURSE_ID,
            title=COURSE_TITLE,
            context_json_path=context_json_path,
        )


def test_course_context_from_json_rejects_invalid_utf8(tmp_path: Path) -> None:
    context_json_path = tmp_path / "invalid_utf8.json"
    context_json_path.write_bytes(b"\x80\x81")

    with pytest.raises(
        ValueError,
        match=rf"Invalid UTF-8 in course context JSON: {context_json_path}",
    ):
        CourseContext.from_json(
            id=COURSE_ID,
            title=COURSE_TITLE,
            context_json_path=context_json_path,
        )
