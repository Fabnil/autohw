from __future__ import annotations

from pathlib import Path

import pytest

from study_agent.domain.discovery import ContextReference, DiscoveryFilesResult

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures"
DISCOVERY_FIXTURES_DIR = FIXTURES_DIR / "domain" / "discovery"
FILES_FIXTURES_DIR = FIXTURES_DIR / "files"


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
            "summary": "Core course instructions.",
            "location": "entire file",
        }
    )

    assert reference == ContextReference(
        path=(FILES_FIXTURES_DIR / "reference_a.md").resolve(),
        summary="Core course instructions.",
        location="entire file",
    )


def test_context_reference_from_dict_rejects_unknown_field() -> None:
    with pytest.raises(
        ValueError,
        match=r"ContextReference contains unknown fields: \['extra'\]",
    ):
        ContextReference.from_dict(
            {
                "path": str((FILES_FIXTURES_DIR / "reference_a.md").resolve()),
                "summary": "Core course instructions.",
                "extra": "boom",
            }
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


def test_discovery_files_result_rejects_non_tuple_references(report_path: Path) -> None:
    with pytest.raises(
        ValueError,
        match=r"DiscoveryFilesResult.references must be a tuple",
    ):
        DiscoveryFilesResult(
            report_path=report_path,
            summary="Discovery summary for the course materials.",
            references=[],  # type: ignore[arg-type]
            findings=(),
        )


@pytest.fixture
def report_path() -> Path:
    return (FILES_FIXTURES_DIR / "report.md").resolve()


def test_discovery_files_result_rejects_duplicate_reference_paths(report_path: Path) -> None:
    reference_path = (FILES_FIXTURES_DIR / "reference_a.md").resolve()

    with pytest.raises(
        ValueError,
        match=r"DiscoveryFilesResult.references must not contain duplicate paths",
    ):
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


def test_discovery_files_result_rejects_non_string_finding(report_path: Path) -> None:
    with pytest.raises(
        ValueError,
        match=r"DiscoveryFilesResult.findings\[0\] must be a string, got int",
    ):
        DiscoveryFilesResult(
            report_path=report_path,
            summary="Discovery summary for the course materials.",
            references=(),
            findings=(123,),  # type: ignore[arg-type]
        )


def test_discovery_files_result_from_json_rejects_unknown_root_field(
    tmp_path: Path,
    report_path: Path,
) -> None:
    result_json_path = _render_discovery_fixture(
        tmp_path,
        "unknown_field.json",
    )

    with pytest.raises(
        ValueError,
        match=r"DiscoveryFilesResult contains unknown fields: \['extra'\]",
    ):
        DiscoveryFilesResult.from_json(
            result_json_path=result_json_path,
            report_path=report_path,
        )


def test_discovery_files_result_from_json_wraps_invalid_reference_error_with_index(
    tmp_path: Path,
    report_path: Path,
) -> None:
    result_json_path = _render_discovery_fixture(
        tmp_path,
        "invalid_reference_type.json",
    )

    with pytest.raises(
        ValueError,
        match=(
            r"Invalid discovery reference at index 1: "
            r"ContextReference.path must be a string"
        ),
    ):
        DiscoveryFilesResult.from_json(
            result_json_path=result_json_path,
            report_path=report_path,
        )


def test_discovery_files_result_from_json_rejects_non_string_finding_value(
    tmp_path: Path,
    report_path: Path,
) -> None:
    result_json_path = _render_discovery_fixture(
        tmp_path,
        "invalid_finding_type.json",
    )

    with pytest.raises(
        ValueError,
        match=r"DiscoveryFilesResult.findings\[1\] must be a string",
    ):
        DiscoveryFilesResult.from_json(
            result_json_path=result_json_path,
            report_path=report_path,
        )


def test_discovery_files_result_from_json_rejects_malformed_json(
    tmp_path: Path,
    report_path: Path,
) -> None:
    result_json_path = _render_discovery_fixture(
        tmp_path,
        "malformed.json",
    )

    with pytest.raises(
        ValueError,
        match=rf"Invalid JSON in {result_json_path}: line \d+, column \d+: .*",
    ):
        DiscoveryFilesResult.from_json(
            result_json_path=result_json_path,
            report_path=report_path,
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

    def _raise_read_error(self: Path, *, encoding: str) -> str:
        raise OSError("boom")

    monkeypatch.setattr(Path, "read_text", _raise_read_error)

    with pytest.raises(
        ValueError,
        match=rf"Failed to read discovery result JSON: {result_json_path}",
    ):
        DiscoveryFilesResult.from_json(
            result_json_path=result_json_path,
            report_path=report_path,
        )
