from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Annotated

from pydantic import AfterValidator, ConfigDict
from pydantic_core import PydanticCustomError

from common.validation.paths import validate_absolute_existing_file_path
from common.validation.strings import validate_non_empty_trimmed_string

MODEL_CONFIG = ConfigDict(
    extra="forbid",
    frozen=True,
)


def _validate_non_empty_trimmed_string(value: str) -> str:
    try:
        return validate_non_empty_trimmed_string(value)
    except ValueError as error:
        raise PydanticCustomError(
            "empty_string",
            str(error),
        ) from error


def _validate_absolute_existing_file_path(path: Path) -> Path:
    try:
        return validate_absolute_existing_file_path(path)
    except ValueError as error:
        error_message = str(error)
        error_type = (
            "path_not_absolute"
            if error_message == "path must be absolute"
            else "path_not_file"
        )
        raise PydanticCustomError(
            error_type,
            error_message,
        ) from error


def ensure_unique_paths(paths: Iterable[Path], *, field_name: str) -> None:
    normalized_paths = tuple(paths)
    if len(normalized_paths) != len(set(normalized_paths)):
        raise PydanticCustomError(
            "duplicate_reference_paths",
            f"{field_name} must not contain duplicate paths",
        )


NonEmptyTrimmedStr = Annotated[
    str,
    AfterValidator(_validate_non_empty_trimmed_string),
]

AbsoluteExistingFilePath = Annotated[
    Path,
    AfterValidator(_validate_absolute_existing_file_path),
]
