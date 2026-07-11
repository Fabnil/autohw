from __future__ import annotations

import json
from pathlib import Path

import pytest

from study_agent.domain.context_reference import ContextReference
from study_agent.domain.course import CourseContext


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

    context = CourseContext.from_json(context_json_path=context_json_path)

    assert context == CourseContext(
        description="Course overview and important conventions.",
        references=(
            ContextReference(
                path=reference_path,
                summary="Core course instructions.",
                location="entire file",
            ),
        ),
    )


def test_course_context_rejects_duplicate_reference_paths(tmp_path: Path) -> None:
    reference_path = tmp_path / "README.md"
    reference_path.write_text("course rules", encoding="utf-8")

    with pytest.raises(
        ValueError,
        match="CourseContext.references must not contain duplicate paths",
    ):
        CourseContext(
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
