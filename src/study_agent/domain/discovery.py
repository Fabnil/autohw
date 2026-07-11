from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from common.validation.json_data import (
    require_json_array as _require_json_array,
)
from common.validation.json_data import (
    require_json_object as _require_json_object,
)
from common.validation.json_data import (
    validate_object_fields as _validate_object_fields,
)
from common.validation.paths import validate_absolute_file_path as _validate_absolute_file_path
from common.validation.strings import validate_non_empty_string as _validate_non_empty_string


@dataclass(frozen=True, slots=True)
class DiscoveryReference:
    path: Path
    summary: str
    location: str | None = None  # где конкретно в файле нужно смотреть

    def __post_init__(self) -> None:
        _validate_absolute_file_path(
            self.path,
            field_name="DiscoveryReference.path",
        )
        _validate_non_empty_string(
            self.summary,
            field_name="DiscoveryReference.summary",
        )

        if self.location is not None:
            _validate_non_empty_string(
                self.location,
                field_name="DiscoveryReference.location",
            )

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
    ) -> DiscoveryReference:
        data = _require_json_object(
            data,
            field_name="DiscoveryReference",
        )

        _validate_object_fields(
            data,
            required_fields={"path", "summary"},
            optional_fields={"location"},
            object_name="DiscoveryReference",
        )

        raw_path = data["path"]
        raw_summary = data["summary"]
        raw_location = data.get("location")

        if not isinstance(raw_path, str):
            raise ValueError("DiscoveryReference.path must be a string")

        if not isinstance(raw_summary, str):
            raise ValueError("DiscoveryReference.summary must be a string")

        if raw_location is not None and not isinstance(
            raw_location,
            str,
        ):
            raise ValueError("DiscoveryReference.location must be a string or null")

        return cls(
            path=Path(raw_path),
            summary=raw_summary,
            location=raw_location,
        )


@dataclass(frozen=True, slots=True)
class DiscoveryResult:
    """
    Результат discovery-стадии.

    Содержит путь к полному Markdown-отчёту, краткое резюме,
    ссылки на релевантные файлы с пояснениями и свободные наблюдения,
    которые могут пригодиться на стадии реализации.
    """

    report_path: Path
    summary: str
    references: tuple[DiscoveryReference, ...]
    findings: tuple[str, ...]

    def __post_init__(self) -> None:
        _validate_absolute_file_path(
            self.report_path,
            field_name="DiscoveryResult.report_path",
        )
        _validate_non_empty_string(
            self.summary,
            field_name="DiscoveryResult.summary",
        )

        if not isinstance(self.references, tuple):
            raise ValueError("DiscoveryResult.references must be a tuple")

        for index, reference in enumerate(self.references):
            if not isinstance(reference, DiscoveryReference):
                raise ValueError(
                    "DiscoveryResult.references"
                    f"[{index}] must be a DiscoveryReference, "
                    f"got {type(reference).__name__}"
                )

        reference_paths = [reference.path for reference in self.references]
        if len(reference_paths) != len(set(reference_paths)):
            raise ValueError("DiscoveryResult.references must not contain duplicate paths")

        if not isinstance(self.findings, tuple):
            raise ValueError("DiscoveryResult.findings must be a tuple")

        for index, finding in enumerate(self.findings):
            _validate_non_empty_string(
                finding,
                field_name=f"DiscoveryResult.findings[{index}]",
            )

    @classmethod
    def from_json(
        cls,
        *,
        result_json_path: Path,
        report_path: Path,
    ) -> DiscoveryResult:
        """
        Загружает результат discovery-стадии из JSON manifest.

        `result_json_path` указывает на JSON, созданный Codex.

        `report_path` передаётся отдельно, поскольку его заранее задаёт
        coordinator. Codex не должен дублировать этот системный путь
        внутри result.json.

        Ожидаемый JSON:

        {
          "summary": "...",
          "references": [
            {
              "path": "/absolute/path/to/file",
              "summary": "...",
              "location": "pages 10-15"
            }
          ],
          "findings": [
            "..."
          ]
        }
        """
        _validate_absolute_file_path(
            result_json_path,
            field_name="result_json_path",
        )

        try:
            raw_json = result_json_path.read_text(encoding="utf-8")
        except OSError as error:
            raise ValueError(f"Failed to read discovery result JSON: {result_json_path}") from error

        try:
            raw_data = json.loads(raw_json)
        except json.JSONDecodeError as error:
            raise ValueError(
                f"Invalid JSON in {result_json_path}: "
                f"line {error.lineno}, column {error.colno}: "
                f"{error.msg}"
            ) from error

        data = _require_json_object(
            raw_data,
            field_name="DiscoveryResult",
        )

        _validate_object_fields(
            data,
            required_fields={
                "summary",
                "references",
                "findings",
            },
            object_name="DiscoveryResult",
        )

        raw_summary = data["summary"]
        if not isinstance(raw_summary, str):
            raise ValueError("DiscoveryResult.summary must be a string")

        raw_references = _require_json_array(
            data["references"],
            field_name="DiscoveryResult.references",
        )
        raw_findings = _require_json_array(
            data["findings"],
            field_name="DiscoveryResult.findings",
        )

        references: list[DiscoveryReference] = []
        for index, raw_reference in enumerate(raw_references):
            try:
                reference_data = _require_json_object(
                    raw_reference,
                    field_name=(f"DiscoveryResult.references[{index}]"),
                )
                references.append(DiscoveryReference.from_dict(reference_data))
            except ValueError as error:
                raise ValueError(
                    f"Invalid discovery reference at index {index}: {error}"
                ) from error

        findings: list[str] = []
        for index, raw_finding in enumerate(raw_findings):
            if not isinstance(raw_finding, str):
                raise ValueError(f"DiscoveryResult.findings[{index}] must be a string")

            findings.append(raw_finding)

        return cls(
            report_path=report_path,
            summary=raw_summary,
            references=tuple(references),
            findings=tuple(findings),
        )
