from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path

import pytest
from pydantic import ValidationError
from pydantic_core import ErrorDetails

from study_agent.domain.context_reference import ContextReference
from study_agent.domain.discovery import DiscoveryFilesResult

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures"
DISCOVERY_FIXTURES_DIR = FIXTURES_DIR / "domain" / "discovery"
FILES_FIXTURES_DIR = FIXTURES_DIR / "files"


def _assert_has_error(
    errors: Sequence[ErrorDetails],
    *,
    loc: tuple[object, ...],
    type_: str,
    msg: str | None = None,
    msg_contains: str | None = None,
) -> None:
    for error in errors:
        if tuple(error["loc"]) != loc:
            continue

        if error["type"] != type_:
            continue

        actual_message = str(error["msg"])
        if msg is not None and actual_message != msg:
            continue
        if msg_contains is not None and msg_contains not in actual_message:
            continue

        return

    raise AssertionError(
        f"Did not find error loc={loc!r}, type={type_!r}, msg={msg!r}, "
        f"msg_contains={msg_contains!r} in {list(errors)!r}"
    )


def _assert_single_error(
    errors: Sequence[ErrorDetails],
    *,
    loc: tuple[object, ...],
    type_: str,
    msg: str | None = None,
    msg_contains: str | None = None,
) -> None:
    assert len(errors) == 1
    _assert_has_error(
        errors,
        loc=loc,
        type_=type_,
        msg=msg,
        msg_contains=msg_contains,
    )


def _render_discovery_fixture(
    tmp_path: Path,
    fixture_name: str,
) -> Path:
    fixture_text = (DISCOVERY_FIXTURES_DIR / fixture_name).read_text(encoding="utf-8")
    rendered_text = fixture_text.replace(
        "__REFERENCE_A__",
        str((FILES_FIXTURES_DIR / "reference_a.md").resolve()),
    ).replace(
        "__REFERENCE_B__",
        str((FILES_FIXTURES_DIR / "reference_b.md").resolve()),
    )

    rendered_path = tmp_path / fixture_name
    rendered_path.write_text(rendered_text, encoding="utf-8")
    return rendered_path


def test_context_reference_from_dict_parses_valid_reference() -> None:
    reference = ContextReference.from_dict(
        {
            "path": str((FILES_FIXTURES_DIR / "reference_a.md").resolve()),
            "summary": "  Core course instructions.  ",
            "location": "  entire file  ",
        }
    )

    assert reference == ContextReference(
        path=(FILES_FIXTURES_DIR / "reference_a.md").resolve(),
        summary="Core course instructions.",
        location="entire file",
    )


def test_context_reference_from_dict_rejects_unknown_field() -> None:
    with pytest.raises(ValidationError) as exc_info:
        ContextReference.from_dict(
            {
                "path": str((FILES_FIXTURES_DIR / "reference_a.md").resolve()),
                "summary": "Core course instructions.",
                "extra": "boom",
            }
        )

    _assert_single_error(
        exc_info.value.errors(include_url=False),
        loc=("extra",),
        type_="extra_forbidden",
        msg="Extra inputs are not permitted",
    )


def test_context_reference_from_dict_rejects_non_object() -> None:
    with pytest.raises(ValidationError) as exc_info:
        ContextReference.from_dict(["bad"])  # type: ignore[arg-type]

    _assert_single_error(
        exc_info.value.errors(include_url=False),
        loc=(),
        type_="model_type",
        msg_contains="valid dictionary or instance of ContextReference",
    )


def test_context_reference_rejects_relative_path() -> None:
    with pytest.raises(ValidationError) as exc_info:
        ContextReference(
            path=Path("relative.md"),
            summary="Core course instructions.",
        )

    _assert_single_error(
        exc_info.value.errors(include_url=False),
        loc=("path",),
        type_="path_not_absolute",
        msg="path must be absolute",
    )


def test_context_reference_rejects_directory_path(tmp_path: Path) -> None:
    with pytest.raises(ValidationError) as exc_info:
        ContextReference(
            path=tmp_path,
            summary="Core course instructions.",
        )

    _assert_single_error(
        exc_info.value.errors(include_url=False),
        loc=("path",),
        type_="path_not_file",
        msg="path must point to an existing file",
    )


def test_context_reference_rejects_empty_location() -> None:
    with pytest.raises(ValidationError) as exc_info:
        ContextReference(
            path=(FILES_FIXTURES_DIR / "reference_a.md").resolve(),
            summary="Core course instructions.",
            location="   ",
        )

    _assert_single_error(
        exc_info.value.errors(include_url=False),
        loc=("location",),
        type_="empty_string",
        msg="must not be empty",
    )


def test_discovery_files_result_from_json_parses_valid_manifest(tmp_path: Path) -> None:
    result_json_path = _render_discovery_fixture(
        tmp_path,
        "valid_result.json",
    )
    report_path = (FILES_FIXTURES_DIR / "report.md").resolve()

    result = DiscoveryFilesResult.from_json(
        result_json_path=result_json_path,
        report_path=report_path,
    )

    assert result == DiscoveryFilesResult(
        report_path=report_path,
        summary="Discovery summary for the course materials.",
        references=(
            ContextReference(
                path=(FILES_FIXTURES_DIR / "reference_a.md").resolve(),
                summary="Core course instructions.",
                location="entire file",
            ),
            ContextReference(
                path=(FILES_FIXTURES_DIR / "reference_b.md").resolve(),
                summary="Primary formulas and notation reference.",
                location="pages 1-3",
            ),
        ),
        findings=(
            "Most assignments rely on the formulas reference.",
            "The README defines the expected project layout.",
        ),
    )


@pytest.fixture
def report_path() -> Path:
    return (FILES_FIXTURES_DIR / "report.md").resolve()


def test_discovery_files_result_normalizes_lists_to_tuples(report_path: Path) -> None:
    result = DiscoveryFilesResult(
        report_path=report_path,
        summary="  Discovery summary for the course materials.  ",
        references=[  # type: ignore[arg-type]
            ContextReference(
                path=(FILES_FIXTURES_DIR / "reference_a.md").resolve(),
                summary="  Core course instructions.  ",
            )
        ],
        findings=["  Most assignments rely on the formulas reference.  "],  # type: ignore[arg-type]
    )

    assert isinstance(result.references, tuple)
    assert isinstance(result.findings, tuple)
    assert result.summary == "Discovery summary for the course materials."
    assert result.references[0].summary == "Core course instructions."
    assert result.findings[0] == "Most assignments rely on the formulas reference."


def test_discovery_files_result_rejects_duplicate_reference_paths(report_path: Path) -> None:
    reference_path = (FILES_FIXTURES_DIR / "reference_a.md").resolve()

    with pytest.raises(ValidationError) as exc_info:
        DiscoveryFilesResult(
            report_path=report_path,
            summary="Discovery summary for the course materials.",
            references=(
                ContextReference(
                    path=reference_path,
                    summary="Core course instructions.",
                ),
                ContextReference(
                    path=reference_path,
                    summary="Same file repeated.",
                ),
            ),
            findings=(),
        )

    _assert_single_error(
        exc_info.value.errors(include_url=False),
        loc=(),
        type_="duplicate_reference_paths",
        msg="references must not contain duplicate paths",
    )


def test_discovery_files_result_rejects_non_string_finding(report_path: Path) -> None:
    with pytest.raises(ValidationError) as exc_info:
        DiscoveryFilesResult(
            report_path=report_path,
            summary="Discovery summary for the course materials.",
            references=(),
            findings=(123,),  # type: ignore[arg-type]
        )

    _assert_single_error(
        exc_info.value.errors(include_url=False),
        loc=("findings", 0),
        type_="string_type",
        msg="Input should be a valid string",
    )


def test_discovery_files_result_from_json_rejects_unknown_root_field(
    tmp_path: Path,
    report_path: Path,
) -> None:
    result_json_path = _render_discovery_fixture(
        tmp_path,
        "unknown_field.json",
    )

    with pytest.raises(ValidationError) as exc_info:
        DiscoveryFilesResult.from_json(
            result_json_path=result_json_path,
            report_path=report_path,
        )

    _assert_single_error(
        exc_info.value.errors(include_url=False),
        loc=("extra",),
        type_="extra_forbidden",
        msg="Extra inputs are not permitted",
    )


def test_discovery_files_result_from_json_rejects_missing_required_field(
    tmp_path: Path,
    report_path: Path,
) -> None:
    result_json_path = tmp_path / "missing_findings.json"
    result_json_path.write_text(
        json.dumps(
            {
                "summary": "Discovery summary for the course materials.",
                "references": [],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValidationError) as exc_info:
        DiscoveryFilesResult.from_json(
            result_json_path=result_json_path,
            report_path=report_path,
        )

    _assert_single_error(
        exc_info.value.errors(include_url=False),
        loc=("findings",),
        type_="missing",
        msg="Field required",
    )


def test_discovery_files_result_from_json_rejects_invalid_reference_path_type(
    tmp_path: Path,
    report_path: Path,
) -> None:
    result_json_path = _render_discovery_fixture(
        tmp_path,
        "invalid_reference_type.json",
    )

    with pytest.raises(ValidationError) as exc_info:
        DiscoveryFilesResult.from_json(
            result_json_path=result_json_path,
            report_path=report_path,
        )

    _assert_single_error(
        exc_info.value.errors(include_url=False),
        loc=("references", 1, "path"),
        type_="path_type",
        msg_contains="Input is not a valid path",
    )


def test_discovery_files_result_from_json_rejects_non_string_finding_value(
    tmp_path: Path,
    report_path: Path,
) -> None:
    result_json_path = _render_discovery_fixture(
        tmp_path,
        "invalid_finding_type.json",
    )

    with pytest.raises(ValidationError) as exc_info:
        DiscoveryFilesResult.from_json(
            result_json_path=result_json_path,
            report_path=report_path,
        )

    _assert_single_error(
        exc_info.value.errors(include_url=False),
        loc=("findings", 1),
        type_="string_type",
        msg="Input should be a valid string",
    )


def test_discovery_files_result_from_json_rejects_malformed_json(
    tmp_path: Path,
    report_path: Path,
) -> None:
    result_json_path = _render_discovery_fixture(
        tmp_path,
        "malformed.json",
    )

    with pytest.raises(ValidationError) as exc_info:
        DiscoveryFilesResult.from_json(
            result_json_path=result_json_path,
            report_path=report_path,
        )

    _assert_single_error(
        exc_info.value.errors(include_url=False),
        loc=(),
        type_="json_invalid",
        msg_contains="Invalid JSON",
    )


def test_discovery_files_result_from_json_rejects_invalid_utf8(
    tmp_path: Path,
    report_path: Path,
) -> None:
    result_json_path = tmp_path / "invalid_utf8.json"
    result_json_path.write_bytes(b"\x80\x81")

    with pytest.raises(ValidationError) as exc_info:
        DiscoveryFilesResult.from_json(
            result_json_path=result_json_path,
            report_path=report_path,
        )

    _assert_single_error(
        exc_info.value.errors(include_url=False),
        loc=(),
        type_="json_invalid",
        msg_contains="Invalid JSON",
    )


def test_discovery_files_result_from_json_surfaces_read_error(
    tmp_path: Path,
    report_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result_json_path = _render_discovery_fixture(
        tmp_path,
        "valid_result.json",
    )

    def _raise_read_error(self: Path) -> bytes:
        raise OSError("boom")

    monkeypatch.setattr(Path, "read_bytes", _raise_read_error)

    with pytest.raises(
        ValueError,
        match=rf"Failed to read discovery result JSON: {result_json_path}",
    ):
        DiscoveryFilesResult.from_json(
            result_json_path=result_json_path,
            report_path=report_path,
        )


def test_discovery_files_result_from_json_validates_wrapper_paths(
    report_path: Path,
) -> None:
    with pytest.raises(ValidationError) as exc_info:
        DiscoveryFilesResult.from_json(
            result_json_path=Path("relative.json"),
            report_path=report_path,
        )

    _assert_has_error(
        exc_info.value.errors(include_url=False),
        loc=("result_json_path",),
        type_="path_not_absolute",
        msg="path must be absolute",
    )
