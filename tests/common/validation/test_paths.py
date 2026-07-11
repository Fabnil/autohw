from __future__ import annotations

from pathlib import Path

import pytest

from common.validation.paths import validate_absolute_file_path

EXISTING_FILE_PATH = (
    Path(__file__).resolve().parents[2] / "fixtures" / "files" / "reference_a.md"
).resolve()


def test_validate_absolute_file_path_accepts_existing_absolute_file() -> None:
    validate_absolute_file_path(
        EXISTING_FILE_PATH,
        field_name="ValidationFixture.path",
    )


def test_validate_absolute_file_path_rejects_non_path_value() -> None:
    with pytest.raises(
        ValueError,
        match=r"ValidationFixture.path must be a pathlib\.Path, got str",
    ):
        validate_absolute_file_path(
            "not-a-path",  # type: ignore[arg-type]
            field_name="ValidationFixture.path",
        )


def test_validate_absolute_file_path_rejects_relative_path() -> None:
    with pytest.raises(
        ValueError,
        match=r"ValidationFixture.path must be an absolute path: relative-file.md",
    ):
        validate_absolute_file_path(
            Path("relative-file.md"),
            field_name="ValidationFixture.path",
        )


def test_validate_absolute_file_path_rejects_missing_file(tmp_path: Path) -> None:
    missing_file_path = tmp_path / "missing.md"

    with pytest.raises(
        ValueError,
        match=rf"ValidationFixture\.path must point to an existing file: {missing_file_path}",
    ):
        validate_absolute_file_path(
            missing_file_path,
            field_name="ValidationFixture.path",
        )
