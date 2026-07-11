from __future__ import annotations

from pathlib import Path


def validate_absolute_existing_file_path(path: Path) -> Path:
    if not path.is_absolute():
        raise ValueError("path must be absolute")

    if not path.is_file():
        raise ValueError("path must point to an existing file")

    return path


def validate_absolute_existing_directory_path(path: Path) -> Path:
    if not path.is_absolute():
        raise ValueError("path must be absolute")

    if not path.is_dir():
        raise ValueError("path must point to an existing directory")

    return path
