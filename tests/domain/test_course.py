from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path

import pytest
from pydantic import ValidationError
from pydantic_core import ErrorDetails

from study_agent.domain.context_reference import ContextReference
from study_agent.domain.course import CourseContext

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


def test_course_context_normalizes_list_references_to_tuple() -> None:
    context = CourseContext(
        id=COURSE_ID,
        title=COURSE_TITLE,
        description="Course overview and important conventions.",
        references=[  # type: ignore[arg-type]
            ContextReference(
                path=(FILES_FIXTURES_DIR / "reference_a.md").resolve(),
                summary="Core course instructions.",
            )
        ],
    )

    assert isinstance(context.references, tuple)


def test_course_context_rejects_non_context_reference_item() -> None:
    with pytest.raises(ValidationError) as exc_info:
        CourseContext(
            id=COURSE_ID,
            title=COURSE_TITLE,
            description="Course overview and important conventions.",
            references=("not-a-reference",),  # type: ignore[arg-type]
        )

    _assert_single_error(
        exc_info.value.errors(include_url=False),
        loc=("references", 0),
        type_="model_type",
        msg_contains="valid dictionary or instance of ContextReference",
    )


def test_course_context_rejects_empty_id() -> None:
    with pytest.raises(ValidationError) as exc_info:
        CourseContext(
            id="  ",
            title=COURSE_TITLE,
            description="Course overview and important conventions.",
            references=(),
        )

    _assert_single_error(
        exc_info.value.errors(include_url=False),
        loc=("id",),
        type_="empty_string",
        msg="must not be empty",
    )


def test_course_context_rejects_empty_title() -> None:
    with pytest.raises(ValidationError) as exc_info:
        CourseContext(
            id=COURSE_ID,
            title="",
            description="Course overview and important conventions.",
            references=(),
        )

    _assert_single_error(
        exc_info.value.errors(include_url=False),
        loc=("title",),
        type_="empty_string",
        msg="must not be empty",
    )


def test_course_context_rejects_duplicate_reference_paths(tmp_path: Path) -> None:
    reference_path = tmp_path / "README.md"
    reference_path.write_text("course rules", encoding="utf-8")

    with pytest.raises(ValidationError) as exc_info:
        CourseContext(
            id=COURSE_ID,
            title=COURSE_TITLE,
            description="Course overview and important conventions.",
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


def test_course_context_from_json_rejects_unknown_root_field(tmp_path: Path) -> None:
    context_json_path = _render_course_fixture(
        tmp_path,
        "unknown_field.json",
    )

    with pytest.raises(ValidationError) as exc_info:
        CourseContext.from_json(
            id=COURSE_ID,
            title=COURSE_TITLE,
            context_json_path=context_json_path,
        )

    _assert_single_error(
        exc_info.value.errors(include_url=False),
        loc=("extra",),
        type_="extra_forbidden",
        msg="Extra inputs are not permitted",
    )


def test_course_context_from_json_rejects_non_string_description(tmp_path: Path) -> None:
    context_json_path = _render_course_fixture(
        tmp_path,
        "description_not_string.json",
    )

    with pytest.raises(ValidationError) as exc_info:
        CourseContext.from_json(
            id=COURSE_ID,
            title=COURSE_TITLE,
            context_json_path=context_json_path,
        )

    _assert_single_error(
        exc_info.value.errors(include_url=False),
        loc=("description",),
        type_="string_type",
        msg="Input should be a valid string",
    )


def test_course_context_from_json_rejects_missing_required_field(
    tmp_path: Path,
) -> None:
    context_json_path = tmp_path / "missing_references.json"
    context_json_path.write_text(
        json.dumps({"description": "Course overview and important conventions."}),
        encoding="utf-8",
    )

    with pytest.raises(ValidationError) as exc_info:
        CourseContext.from_json(
            id=COURSE_ID,
            title=COURSE_TITLE,
            context_json_path=context_json_path,
        )

    _assert_single_error(
        exc_info.value.errors(include_url=False),
        loc=("references",),
        type_="missing",
        msg="Field required",
    )


def test_course_context_from_json_rejects_invalid_reference_path_type(
    tmp_path: Path,
) -> None:
    context_json_path = _render_course_fixture(
        tmp_path,
        "invalid_reference_type.json",
    )

    with pytest.raises(ValidationError) as exc_info:
        CourseContext.from_json(
            id=COURSE_ID,
            title=COURSE_TITLE,
            context_json_path=context_json_path,
        )

    _assert_single_error(
        exc_info.value.errors(include_url=False),
        loc=("references", 1, "path"),
        type_="path_type",
        msg_contains="Input is not a valid path",
    )


def test_course_context_from_json_rejects_duplicate_reference_paths(
    tmp_path: Path,
) -> None:
    context_json_path = _render_course_fixture(
        tmp_path,
        "duplicate_reference_paths.json",
    )

    with pytest.raises(ValidationError) as exc_info:
        CourseContext.from_json(
            id=COURSE_ID,
            title=COURSE_TITLE,
            context_json_path=context_json_path,
        )

    _assert_single_error(
        exc_info.value.errors(include_url=False),
        loc=(),
        type_="duplicate_reference_paths",
        msg="references must not contain duplicate paths",
    )


def test_course_context_from_json_rejects_malformed_json(tmp_path: Path) -> None:
    context_json_path = _render_course_fixture(
        tmp_path,
        "malformed.json",
    )

    with pytest.raises(ValidationError) as exc_info:
        CourseContext.from_json(
            id=COURSE_ID,
            title=COURSE_TITLE,
            context_json_path=context_json_path,
        )

    _assert_single_error(
        exc_info.value.errors(include_url=False),
        loc=(),
        type_="json_invalid",
        msg_contains="Invalid JSON",
    )


def test_course_context_from_json_rejects_invalid_utf8(tmp_path: Path) -> None:
    context_json_path = tmp_path / "invalid_utf8.json"
    context_json_path.write_bytes(b"\x80\x81")

    with pytest.raises(ValidationError) as exc_info:
        CourseContext.from_json(
            id=COURSE_ID,
            title=COURSE_TITLE,
            context_json_path=context_json_path,
        )

    _assert_single_error(
        exc_info.value.errors(include_url=False),
        loc=(),
        type_="json_invalid",
        msg_contains="Invalid JSON",
    )


def test_course_context_from_json_surfaces_read_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context_json_path = _render_course_fixture(
        tmp_path,
        "valid_context.json",
    )

    def _raise_read_error(self: Path) -> bytes:
        raise OSError("boom")

    monkeypatch.setattr(Path, "read_bytes", _raise_read_error)

    with pytest.raises(
        ValueError,
        match=rf"Failed to read course context JSON: {context_json_path}",
    ):
        CourseContext.from_json(
            id=COURSE_ID,
            title=COURSE_TITLE,
            context_json_path=context_json_path,
        )
