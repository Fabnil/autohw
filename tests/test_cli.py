from __future__ import annotations

import pytest

from study_agent import __version__
from study_agent.cli.main import main


def test_version_constant() -> None:
    assert __version__ == "0.1.0"


def test_main_prints_placeholder_message(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main()
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "CLI entry point" in captured.out
