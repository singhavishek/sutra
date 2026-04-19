"""Smoke tests for the top-level `sutra` CLI wiring."""

from __future__ import annotations

from typing import TYPE_CHECKING

from typer.testing import CliRunner

from sutra import __version__
from sutra.cli import app
from sutra.core import launchd as launchd_module

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
    monkeypatch.setattr(launchd_module.sys, "platform", "linux")
    monkeypatch.setenv("SUTRA_PATHS__CONFIG_HOME", str(tmp_path / "cfg"))
    monkeypatch.setenv("SUTRA_PATHS__DATA_HOME", str(tmp_path / "data"))
    monkeypatch.setenv("SUTRA_PATHS__LOG_HOME", str(tmp_path / "logs"))
    monkeypatch.setenv("SUTRA_PATHS__LAUNCH_AGENTS_DIR", str(tmp_path / "launchagents"))
    monkeypatch.setenv("SUTRA_PATHS__CLAUDE_MCP_CONFIG_PATH", str(tmp_path / ".claude.json"))

    result = runner.invoke(app, ["init"])

    assert result.exit_code == 0, result.stdout
    assert "sutra initialized" in result.stdout
    assert (tmp_path / ".claude.json").exists()
    assert (tmp_path / "launchagents" / "ai.sutra.falkordb.plist").exists()


def test_falkordb_serve_reports_setup_error_with_nonzero_exit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SUTRA_FALKORDB__REDIS_SERVER_BINARY", "/does/not/exist/redis-server")
    result = runner.invoke(app, ["falkordb-serve"])
    assert result.exit_code == 1
    assert "redis-server not found" in result.stdout
