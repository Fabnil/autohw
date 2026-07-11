from __future__ import annotations

import pytest

from common.validation.strings import validate_non_empty_trimmed_string


def test_validate_non_empty_trimmed_string_returns_trimmed_value() -> None:
    result = validate_non_empty_trimmed_string("  course context  ")

    assert result == "course context"


def test_validate_non_empty_trimmed_string_rejects_whitespace_only_string() -> None:
    with pytest.raises(ValueError, match=r"must not be empty"):
        validate_non_empty_trimmed_string("   ")
