from __future__ import annotations


def validate_non_empty_string(value: str, *, field_name: str) -> None:
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string, got {type(value).__name__}")

    if not value.strip():
        raise ValueError(f"{field_name} must not be empty")
