from __future__ import annotations

from typing import Self

from pydantic import BaseModel, model_validator, validate_call

from study_agent.domain.context_reference import ContextReference
from study_agent.domain.pydantic_types import (
    MODEL_CONFIG,
    AbsoluteExistingFilePath,
    NonEmptyTrimmedStr,
    ensure_unique_paths,
)


class _DiscoveryFilesResultJson(BaseModel):
    model_config = MODEL_CONFIG

    summary: NonEmptyTrimmedStr
    references: tuple[ContextReference, ...]
    findings: tuple[NonEmptyTrimmedStr, ...]


class DiscoveryFilesResult(BaseModel):
    model_config = MODEL_CONFIG

    """
    Результат discovery-стадии - той её части где ищутся файлы.

    Содержит путь к полному Markdown-отчёту, краткое резюме,
    ссылки на релевантные файлы с пояснениями и свободные наблюдения,
    которые могут пригодиться на стадии реализации.
    """

    report_path: AbsoluteExistingFilePath
    summary: NonEmptyTrimmedStr
    references: tuple[ContextReference, ...]
    findings: tuple[NonEmptyTrimmedStr, ...]

    @model_validator(mode="after")
    def validate_unique_reference_paths(self) -> Self:
        ensure_unique_paths(
            (reference.path for reference in self.references),
            field_name="references",
        )
        return self

    @classmethod
    @validate_call
    def from_json(
        cls,
        *,
        result_json_path: AbsoluteExistingFilePath,
        report_path: AbsoluteExistingFilePath,
    ) -> Self:
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
        try:
            raw_json = result_json_path.read_bytes()
        except OSError as error:
            raise ValueError(f"Failed to read discovery result JSON: {result_json_path}") from error

        json_data = _DiscoveryFilesResultJson.model_validate_json(raw_json)

        return cls(
            report_path=report_path,
            summary=json_data.summary,
            references=json_data.references,
            findings=json_data.findings,
        )
