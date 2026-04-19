"""Tests for sutra.cli_commands.init orchestrator."""

from __future__ import annotations

import json
import plistlib
from pathlib import Path
from typing import TYPE_CHECKING

from sutra.cli_commands.init import run
from sutra.core.claude_mcp import SUTRA_SERVER_NAME, is_registered
from sutra.core.paths import SutraPaths

if TYPE_CHECKING:
    import pytest


def _paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> SutraPaths:
    monkeypatch.setenv("SUTRA_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("SUTRA_DATA_HOME", str(tmp_path / "data"))
    monkeypatch.setenv("SUTRA_LOG_HOME", str(tmp_path / "logs"))
    monkeypatch.setenv("SUTRA_LAUNCH_AGENTS_DIR", str(tmp_path / "launchagents"))
    monkeypatch.setenv("SUTRA_CLAUDE_MCP_CONFIG_PATH", str(tmp_path / ".claude.json"))
    monkeypatch.delenv("SUTRA_LAUNCHD_LABEL", raising=False)
    return SutraPaths()


def test_run_creates_every_directory_in_all_dirs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths = _paths(tmp_path, monkeypatch)
    run(paths)
    for d in paths.all_dirs():
        assert d.is_dir()


def test_run_reports_created_vs_existing_dirs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths = _paths(tmp_path, monkeypatch)
    paths.config_home.mkdir(parents=True, exist_ok=True)

    result = run(paths)

    assert paths.config_home in result.existing_dirs
    assert paths.graph_dir in result.created_dirs


def test_run_writes_launchd_plist_with_expected_label(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths = _paths(tmp_path, monkeypatch)
    result = run(paths)

    assert result.plist_path == paths.launchd_plist
    assert paths.launchd_plist.exists()
    data = plistlib.loads(paths.launchd_plist.read_bytes())
    assert data["Label"] == paths.launchd_label


def test_run_registers_sutra_with_claude_mcp(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths = _paths(tmp_path, monkeypatch)
    run(paths)
    assert is_registered(paths) is True


def test_run_reports_plist_was_new_on_first_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths = _paths(tmp_path, monkeypatch)
    result = run(paths)
    assert result.plist_was_new is True


def test_run_reports_plist_not_new_on_second_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths = _paths(tmp_path, monkeypatch)
    run(paths)
    second = run(paths)
    assert second.plist_was_new is False


def test_run_reports_mcp_already_registered_on_second_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths = _paths(tmp_path, monkeypatch)
    first = run(paths)
    second = run(paths)
    assert first.mcp_was_already_registered is False
    assert second.mcp_was_already_registered is True


def test_run_is_idempotent_on_directory_creation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths = _paths(tmp_path, monkeypatch)
    run(paths)
    second = run(paths)
    assert second.created_dirs == []
    assert set(second.existing_dirs) == set(paths.all_dirs())


def test_run_respects_sutra_binary_override(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths = _paths(tmp_path, monkeypatch)
    run(paths, sutra_binary=Path("/custom/path/sutra"))

    data = plistlib.loads(paths.launchd_plist.read_bytes())
    assert data["ProgramArguments"][0] == "/custom/path/sutra"


def test_run_mcp_entry_uses_default_command_and_serve_mcp(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths = _paths(tmp_path, monkeypatch)
    run(paths)
    config = json.loads(paths.claude_mcp_config_path.read_text(encoding="utf-8"))
    entry = config["mcpServers"][SUTRA_SERVER_NAME]
    assert entry == {"command": "sutra", "args": ["serve-mcp"]}
