from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from common.validation.json_data import (
    require_json_array,
    require_json_object,
    validate_object_fields,
)

FIXTURES_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "validation" / "json_data"


def _load_json_fixture(name: str) -> Any:
    return json.loads((FIXTURES_DIR / name).read_text(encoding="utf-8"))


def test_require_json_object_returns_dict_from_fixture() -> None:
    data = _load_json_fixture("object.json")

    result = require_json_object(
        data,
        field_name="ValidationFixture.object",
    )

    assert result == data


def test_require_json_object_rejects_non_object() -> None:
    data = _load_json_fixture("array.json")

    with pytest.raises(
        ValueError,
        match=r"ValidationFixture.array must be a JSON object, got list",
    ):
        require_json_object(
            data,
            field_name="ValidationFixture.array",
        )


def test_require_json_object_rejects_non_string_keys() -> None:
    with pytest.raises(
        ValueError,
        match=r"ValidationFixture.object must contain only string keys",
    ):
        require_json_object(
            {1: "value"},
            field_name="ValidationFixture.object",
        )


def test_require_json_array_returns_list_from_fixture() -> None:
    data = _load_json_fixture("array.json")

    result = require_json_array(
        data,
        field_name="ValidationFixture.array",
    )

    assert result == data


def test_require_json_array_rejects_non_array() -> None:
    data = _load_json_fixture("object.json")

    with pytest.raises(
        ValueError,
        match=r"ValidationFixture.object must be a JSON array, got dict",
    ):
        require_json_array(
            data,
            field_name="ValidationFixture.object",
        )


def test_validate_object_fields_accepts_required_and_optional_fields() -> None:
    data = _load_json_fixture("object_with_optional_field.json")

    validate_object_fields(
        data,
        required_fields={"summary", "references"},
        optional_fields={"location"},
        object_name="ValidationFixture.object",
    )


def test_validate_object_fields_rejects_missing_required_fields() -> None:
    data = _load_json_fixture("object_missing_required_fields.json")

    with pytest.raises(
        ValueError,
        match=r"ValidationFixture.object is missing required fields: \['references'\]",
    ):
        validate_object_fields(
            data,
            required_fields={"summary", "references"},
            object_name="ValidationFixture.object",
        )


def test_validate_object_fields_rejects_unknown_fields() -> None:
    data = _load_json_fixture("object_with_unknown_field.json")

    with pytest.raises(
        ValueError,
        match=r"ValidationFixture.object contains unknown fields: \['extra'\]",
    ):
        validate_object_fields(
            data,
            required_fields={"summary", "references"},
            object_name="ValidationFixture.object",
        )
