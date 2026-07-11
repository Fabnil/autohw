from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path

import pytest
from pydantic import ValidationError
from pydantic_core import ErrorDetails

from study_agent.domain.context_reference import ContextReference
from study_agent.domain.course import CourseContext

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


def test_course_context_from_json_parses_valid_manifest(tmp_path: Path) -> None:
    reference_path = tmp_path / "README.md"
    reference_path.write_text("course rules", encoding="utf-8")

    context_json_path = tmp_path / "context.json"
    context_json_path.write_text(
        json.dumps(
            {
                "description": "Course overview and important conventions.",
                "references": [
                    {
                        "path": str(reference_path),
                        "summary": "Core course instructions.",
                        "location": "entire file",
                    }
                ],
            }
        ),
        encoding="utf-8",
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
                path=reference_path,
                summary="Core course instructions.",
                location="entire file",
            ),
        ),
    )


def test_course_context_normalizes_values_and_reference_list(tmp_path: Path) -> None:
    reference_path = tmp_path / "README.md"
    reference_path.write_text("course rules", encoding="utf-8")

    context = CourseContext(
        id="  linear-algebra  ",
        title="  Linear Algebra  ",
        description="  Course overview and important conventions.  ",
        references=[  # type: ignore[arg-type]
            ContextReference(
                path=reference_path,
                summary="  Core course instructions.  ",
                location="  entire file  ",
            )
        ],
    )

    assert context.id == COURSE_ID
    assert context.title == COURSE_TITLE
    assert context.description == "Course overview and important conventions."
    assert context.references == (
        ContextReference(
            path=reference_path,
            summary="Core course instructions.",
            location="entire file",
        ),
    )


def test_course_context_from_json_validates_wrapper_path() -> None:
    with pytest.raises(ValidationError) as exc_info:
        CourseContext.from_json(
            id=COURSE_ID,
            title=COURSE_TITLE,
            context_json_path=Path("context.json"),
        )

    _assert_single_error(
        exc_info.value.errors(include_url=False),
        loc=("context_json_path",),
        type_="path_not_absolute",
        msg="path must be absolute",
    )
