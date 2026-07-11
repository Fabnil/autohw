from __future__ import annotations

from pathlib import Path


def validate_absolute_existing_file_path(path: Path) -> Path:
    if not path.is_absolute():
        raise ValueError(f"path must be absolute, but given path: {str(path)}")

    if not path.is_file():
        raise ValueError(f"path must point to an existing file, but given path: {str(path)}")

    return path
