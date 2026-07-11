from __future__ import annotations

import pytest

from common.validation.strings import validate_non_empty_string


def test_validate_non_empty_string_accepts_non_empty_string() -> None:
    validate_non_empty_string(
        "Study Agent",
        field_name="ValidationFixture.string",
    )


def test_validate_non_empty_string_rejects_non_string() -> None:
    with pytest.raises(
        ValueError,
        match=r"ValidationFixture.string must be a string, got int",
    ):
        validate_non_empty_string(
            123,  # type: ignore[arg-type]
            field_name="ValidationFixture.string",
        )


def test_validate_non_empty_string_rejects_whitespace_only_string() -> None:
    with pytest.raises(
        ValueError,
        match=r"ValidationFixture.string must not be empty",
    ):
        validate_non_empty_string(
            "   ",
            field_name="ValidationFixture.string",
        )
