"""Smoke tests for the top-level `sutra` CLI wiring."""

from __future__ import annotations

from typing import TYPE_CHECKING

from typer.testing import CliRunner

from sutra import __version__
from sutra.cli import app

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

runner = CliRunner()


def test_version_flag_prints_version_and_exits_zero() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.stdout


def test_short_version_flag_matches_long_form() -> None:
    result = runner.invoke(app, ["-V"])
    assert result.exit_code == 0
    assert __version__ in result.stdout


def test_bare_invocation_shows_help() -> None:
    result = runner.invoke(app, [])
    assert result.exit_code == 2
    assert "Usage:" in result.stdout


def test_init_runs_end_to_end_and_reports_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SUTRA_CONFIG_HOME", str(tmp_path / "cfg"))
    monkeypatch.setenv("SUTRA_DATA_HOME", str(tmp_path / "data"))
    monkeypatch.setenv("SUTRA_LOG_HOME", str(tmp_path / "logs"))
    monkeypatch.setenv("SUTRA_LAUNCH_AGENTS_DIR", str(tmp_path / "launchagents"))
    monkeypatch.setenv("SUTRA_CLAUDE_MCP_CONFIG_PATH", str(tmp_path / ".claude.json"))

    result = runner.invoke(app, ["init"])

    assert result.exit_code == 0, result.stdout
    assert "sutra initialized" in result.stdout
    assert (tmp_path / ".claude.json").exists()
    assert (tmp_path / "launchagents" / "ai.sutra.falkordb.plist").exists()
