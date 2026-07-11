from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from study_agent.domain.pydantic_types import (
    MODEL_CONFIG,
    AbsoluteExistingFilePath,
    NonEmptyTrimmedStr,
)


class ContextReference(BaseModel):
    model_config = MODEL_CONFIG

    path: AbsoluteExistingFilePath
    summary: NonEmptyTrimmedStr
    location: NonEmptyTrimmedStr | None = None  # где конкретно в файле нужно смотреть

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
    ) -> ContextReference:
        return cls.model_validate(data)
