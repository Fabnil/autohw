from __future__ import annotations

from pathlib import Path


def validate_absolute_file_path(path: Path, *, field_name: str) -> None:
    if not isinstance(path, Path):
        raise ValueError(f"{field_name} must be a pathlib.Path, got {type(path).__name__}")

    if not path.is_absolute():
        raise ValueError(f"{field_name} must be an absolute path: {path}")

    if not path.is_file():
        raise ValueError(f"{field_name} must point to an existing file: {path}")
