from __future__ import annotations

from typing import Any


def require_json_object(
    value: Any,
    *,
    field_name: str,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{field_name} must be a JSON object, got {type(value).__name__}")

    if not all(isinstance(key, str) for key in value):
        raise ValueError(f"{field_name} must contain only string keys")

    return value


def require_json_array(
    value: Any,
    *,
    field_name: str,
) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(f"{field_name} must be a JSON array, got {type(value).__name__}")

    return value


def validate_object_fields(
    data: dict[str, Any],
    *,
    required_fields: set[str],
    optional_fields: set[str] | None = None,
    object_name: str,
) -> None:
    optional_fields = optional_fields or set()
    allowed_fields = required_fields | optional_fields

    missing_fields = required_fields - data.keys()
    if missing_fields:
        raise ValueError(f"{object_name} is missing required fields: {sorted(missing_fields)}")

    unknown_fields = data.keys() - allowed_fields
    if unknown_fields:
        raise ValueError(f"{object_name} contains unknown fields: {sorted(unknown_fields)}")
