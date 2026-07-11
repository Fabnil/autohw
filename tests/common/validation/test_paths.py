from __future__ import annotations

from pathlib import Path

import pytest

from common.validation.paths import (
    validate_absolute_existing_directory_path,
    validate_absolute_existing_file_path,
)

FIXTURES_DIR = Path(__file__).resolve().parents[2] / "fixtures"
FILES_FIXTURES_DIR = FIXTURES_DIR / "files"


def test_validate_absolute_existing_file_path_returns_file_path() -> None:
    path = (FILES_FIXTURES_DIR / "reference_a.md").resolve()

    result = validate_absolute_existing_file_path(path)

    assert result == path


def test_validate_absolute_existing_file_path_rejects_relative_path() -> None:
    with pytest.raises(ValueError, match=r"path must be absolute"):
        validate_absolute_existing_file_path(Path("relative/file.md"))


def test_validate_absolute_existing_file_path_rejects_missing_file(tmp_path: Path) -> None:
    missing_path = tmp_path / "missing.md"

    with pytest.raises(ValueError, match=r"path must point to an existing file"):
        validate_absolute_existing_file_path(missing_path)


def test_validate_absolute_existing_directory_path_returns_directory_path(
    tmp_path: Path,
) -> None:
    path = tmp_path.resolve()

    result = validate_absolute_existing_directory_path(path)

    assert result == path


def test_validate_absolute_existing_directory_path_rejects_relative_path() -> None:
    with pytest.raises(ValueError, match=r"path must be absolute"):
        validate_absolute_existing_directory_path(Path("relative/dir"))


def test_validate_absolute_existing_directory_path_rejects_missing_directory(
    tmp_path: Path,
) -> None:
    missing_path = tmp_path / "missing-dir"

    with pytest.raises(ValueError, match=r"path must point to an existing directory"):
        validate_absolute_existing_directory_path(missing_path)
