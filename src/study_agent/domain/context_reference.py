from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from common.validation.json_data import (
    require_json_object as _require_json_object,
)
from common.validation.json_data import (
    validate_object_fields as _validate_object_fields,
)
from common.validation.paths import validate_absolute_file_path as _validate_absolute_file_path
from common.validation.strings import validate_non_empty_string as _validate_non_empty_string


@dataclass(frozen=True, slots=True)
class ContextReference:
    path: Path
    summary: str
    location: str | None = None  # где конкретно в файле нужно смотреть

    def __post_init__(self) -> None:
        _validate_absolute_file_path(
            self.path,
            field_name="ContextReference.path",
        )
        _validate_non_empty_string(
            self.summary,
            field_name="ContextReference.summary",
        )

        if self.location is not None:
            _validate_non_empty_string(
                self.location,
                field_name="ContextReference.location",
            )

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
    ) -> ContextReference:
        data = _require_json_object(
            data,
            field_name="ContextReference",
        )

        _validate_object_fields(
            data,
            required_fields={"path", "summary"},
            optional_fields={"location"},
            object_name="ContextReference",
        )

        raw_path = data["path"]
        raw_summary = data["summary"]
        raw_location = data.get("location")

        if not isinstance(raw_path, str):
            raise ValueError("ContextReference.path must be a string")

        if not isinstance(raw_summary, str):
            raise ValueError("ContextReference.summary must be a string")

        if raw_location is not None and not isinstance(
            raw_location,
            str,
        ):
            raise ValueError("ContextReference.location must be a string or null")

        return cls(
            path=Path(raw_path),
            summary=raw_summary,
            location=raw_location,
        )
