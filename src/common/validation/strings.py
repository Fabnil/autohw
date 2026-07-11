from __future__ import annotations


def validate_non_empty_trimmed_string(value: str) -> str:
    stripped_value = value.strip()
    if not stripped_value:
        raise ValueError("must not be empty")

    return stripped_value
