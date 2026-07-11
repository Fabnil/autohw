from __future__ import annotations

import json
from pathlib import Path
from typing import Self, TypeVar

from pydantic import BaseModel, model_validator, validate_call
from pydantic_core import PydanticCustomError

from study_agent.domain.context_reference import ContextReference
from study_agent.domain.pydantic_types import (
    MODEL_CONFIG,
    AbsoluteExistingDirectoryPath,
    AbsoluteExistingFilePath,
    NonEmptyTrimmedStr,
    ensure_unique_paths,
)

_ModelT = TypeVar("_ModelT", bound=BaseModel)


def _read_model_json(
    model_type: type[_ModelT],
    *,
    json_path: Path,
    error_label: str,
) -> _ModelT:
    try:
        raw_json = json_path.read_bytes()
    except OSError as error:
        raise ValueError(f"Failed to read {error_label}: {json_path}") from error

    return model_type.model_validate_json(raw_json)


def _model_to_json_text(model: BaseModel) -> str:
    return json.dumps(
        model.model_dump(mode="json"),
        ensure_ascii=False,
        indent=2,
    ) + "\n"


class CourseContext(BaseModel):
    model_config = MODEL_CONFIG

    id: NonEmptyTrimmedStr
    title: NonEmptyTrimmedStr
    description: NonEmptyTrimmedStr
    course_root: AbsoluteExistingDirectoryPath
    references: tuple[ContextReference, ...]

    @model_validator(mode="after")
    def validate_unique_reference_paths(self) -> Self:
        ensure_unique_paths(
            (reference.path for reference in self.references),
            field_name="references",
        )
        return self

    @classmethod
    @validate_call
    def from_json(
        cls,
        *,
        context_json_path: AbsoluteExistingFilePath,
    ) -> Self:
        return _read_model_json(
            cls,
            json_path=context_json_path,
            error_label="course context JSON",
        )

    def to_json_text(self) -> str:
        return _model_to_json_text(self)


class CoursesCatalog(BaseModel):
    model_config = MODEL_CONFIG

    courses: tuple[CourseContext, ...]

    @model_validator(mode="after")
    def validate_unique_courses(self) -> Self:
        course_ids = [course.id for course in self.courses]
        if len(course_ids) != len(set(course_ids)):
            raise PydanticCustomError(
                "duplicate_course_id",
                "courses must not contain duplicate ids",
            )

        course_roots = [course.course_root for course in self.courses]
        if len(course_roots) != len(set(course_roots)):
            raise PydanticCustomError(
                "duplicate_course_root",
                "courses must not contain duplicate course_root values",
            )

        return self

    @classmethod
    def from_course_json_files(
        cls,
        *,
        courses_dir: Path,
    ) -> Self:
        courses: list[CourseContext] = []
        if not courses_dir.exists():
            return cls(courses=())

        for context_json_path in sorted(courses_dir.glob("*.json")):
            courses.append(
                CourseContext.from_json(context_json_path=context_json_path.resolve())
            )

        return cls(
            courses=tuple(sorted(courses, key=lambda course: course.id)),
        )
