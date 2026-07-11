from __future__ import annotations

from typing import Self

from pydantic import BaseModel, model_validator, validate_call

from study_agent.domain.context_reference import ContextReference
from study_agent.domain.pydantic_types import (
    MODEL_CONFIG,
    AbsoluteExistingFilePath,
    NonEmptyTrimmedStr,
    ensure_unique_paths,
)


class _CourseContextJson(BaseModel):
    model_config = MODEL_CONFIG

    description: NonEmptyTrimmedStr
    references: tuple[ContextReference, ...]


class CourseContext(BaseModel):
    model_config = MODEL_CONFIG

    id: NonEmptyTrimmedStr
    title: NonEmptyTrimmedStr
    description: NonEmptyTrimmedStr
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
        id: NonEmptyTrimmedStr,
        title: NonEmptyTrimmedStr,
        context_json_path: AbsoluteExistingFilePath,
    ) -> Self:
        try:
            raw_json = context_json_path.read_bytes()
        except OSError as error:
            raise ValueError(f"Failed to read course context JSON: {context_json_path}") from error

        json_data = _CourseContextJson.model_validate_json(raw_json)

        return cls(
            id=id,
            title=title,
            description=json_data.description,
            references=json_data.references,
        )
