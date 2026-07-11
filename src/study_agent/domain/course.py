from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from common.validation.json_data import (
    require_json_array as _require_json_array,
)
from common.validation.json_data import (
    require_json_object as _require_json_object,
)
from common.validation.json_data import (
    validate_object_fields as _validate_object_fields,
)
from common.validation.paths import validate_absolute_file_path as _validate_absolute_file_path
from common.validation.strings import validate_non_empty_string as _validate_non_empty_string
from study_agent.domain.context_reference import ContextReference


@dataclass(frozen=True, slots=True)
class CourseContext:
    id: str
    title: str
    description: str
    references: tuple[ContextReference, ...]

    def __post_init__(self) -> None:
        _validate_non_empty_string(
            self.description,
            field_name="CourseContext.description",
        )

        if not isinstance(self.references, tuple):
            raise ValueError("CourseContext.references must be a tuple")

        for index, reference in enumerate(self.references):
            if not isinstance(reference, ContextReference):
                raise ValueError(f"CourseContext.references[{index}] must be a ContextReference")

        reference_paths = [reference.path for reference in self.references]
        if len(reference_paths) != len(set(reference_paths)):
            raise ValueError("CourseContext.references must not contain duplicate paths")

    @classmethod
    def from_json(
        cls,
        *,
        context_json_path: Path,
    ) -> CourseContext:
        _validate_absolute_file_path(
            context_json_path,
            field_name="context_json_path",
        )

        try:
            raw_json = context_json_path.read_text(encoding="utf-8")
        except UnicodeDecodeError as error:
            raise ValueError(
                f"Invalid UTF-8 in course context JSON: {context_json_path}"
            ) from error
        except OSError as error:
            raise ValueError(f"Failed to read course context JSON: {context_json_path}") from error

        try:
            raw_data = json.loads(raw_json)
        except json.JSONDecodeError as error:
            raise ValueError(
                f"Invalid JSON in {context_json_path}: "
                f"line {error.lineno}, column {error.colno}: "
                f"{error.msg}"
            ) from error

        data = _require_json_object(
            raw_data,
            field_name="CourseContext",
        )

        _validate_object_fields(
            data,
            required_fields={"description", "references"},
            object_name="CourseContext",
        )

        raw_description = data["description"]
        if not isinstance(raw_description, str):
            raise ValueError("CourseContext.description must be a string")

        raw_references = _require_json_array(
            data["references"],
            field_name="CourseContext.references",
        )

        references: list[ContextReference] = []
        for index, raw_reference in enumerate(raw_references):
            try:
                reference_data = _require_json_object(
                    raw_reference,
                    field_name=f"CourseContext.references[{index}]",
                )
                references.append(ContextReference.from_dict(reference_data))
            except ValueError as error:
                raise ValueError(
                    f"Invalid CourseContext reference at index {index}: {error}"
                ) from error

        return cls(
            description=raw_description,
            references=tuple(references),
        )
