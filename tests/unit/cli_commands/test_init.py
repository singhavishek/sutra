"""Tests for sutra.cli_commands.init orchestrator."""

from __future__ import annotations

import json
import plistlib
import tomllib
from pathlib import Path

import pytest

from sutra.cli_commands.init import run
from sutra.core import launchd as launchd_module
from sutra.core.claude_mcp import SUTRA_SERVER_NAME, is_registered
from sutra.core.settings import SutraSettings


@pytest.fixture(autouse=True)
def _skip_launchctl(monkeypatch: pytest.MonkeyPatch) -> None:
    """Force `launchd.bootstrap` to no-op during these unit tests."""
    monkeypatch.setattr(launchd_module.sys, "platform", "linux")


def _settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> SutraSettings:
    monkeypatch.setenv("SUTRA_PATHS__CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("SUTRA_PATHS__DATA_HOME", str(tmp_path / "data"))
    monkeypatch.setenv("SUTRA_PATHS__LOG_HOME", str(tmp_path / "logs"))
    monkeypatch.setenv("SUTRA_PATHS__LAUNCH_AGENTS_DIR", str(tmp_path / "launchagents"))
    monkeypatch.setenv("SUTRA_PATHS__CLAUDE_MCP_CONFIG_PATH", str(tmp_path / ".claude.json"))
    monkeypatch.setenv("SUTRA_CONFIG_TOML", str(tmp_path / "missing.toml"))
    monkeypatch.delenv("SUTRA_PATHS__LAUNCHD_LABEL", raising=False)
    return SutraSettings()


def test_run_creates_every_directory_in_all_dirs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = _settings(tmp_path, monkeypatch)
    run(settings)
    for d in settings.paths.all_dirs():
        assert d.is_dir()


def test_run_reports_created_vs_existing_dirs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = _settings(tmp_path, monkeypatch)
    settings.paths.config_home.mkdir(parents=True, exist_ok=True)

    result = run(settings)

    assert settings.paths.config_home in result.existing_dirs
    assert settings.paths.graph_dir in result.created_dirs


def test_run_writes_launchd_plist_with_expected_label(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = _settings(tmp_path, monkeypatch)
    result = run(settings)

    assert result.plist_path == settings.paths.launchd_plist
    assert settings.paths.launchd_plist.exists()
    data = plistlib.loads(settings.paths.launchd_plist.read_bytes())
    assert data["Label"] == settings.paths.launchd_label


def test_run_registers_sutra_with_claude_mcp(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = _settings(tmp_path, monkeypatch)
    run(settings)
    assert is_registered(settings) is True


def test_run_reports_plist_was_new_on_first_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = _settings(tmp_path, monkeypatch)
    result = run(settings)
    assert result.plist_was_new is True


def test_run_reports_plist_not_new_on_second_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = _settings(tmp_path, monkeypatch)
    run(settings)
    second = run(settings)
    assert second.plist_was_new is False


def test_run_reports_mcp_already_registered_on_second_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = _settings(tmp_path, monkeypatch)
    first = run(settings)
    second = run(settings)
    assert first.mcp_was_already_registered is False
    assert second.mcp_was_already_registered is True


def test_run_is_idempotent_on_directory_creation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = _settings(tmp_path, monkeypatch)
    run(settings)
    second = run(settings)
    assert second.created_dirs == []
    assert set(second.existing_dirs) == set(settings.paths.all_dirs())


def test_run_respects_sutra_binary_override(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = _settings(tmp_path, monkeypatch)
    run(settings, sutra_binary=Path("/custom/path/sutra"))

    data = plistlib.loads(settings.paths.launchd_plist.read_bytes())
    assert data["ProgramArguments"][0] == "/custom/path/sutra"


def test_run_mcp_entry_uses_default_command_and_serve_mcp(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = _settings(tmp_path, monkeypatch)
    run(settings)
    config = json.loads(settings.paths.claude_mcp_config_path.read_text(encoding="utf-8"))
    entry = config["mcpServers"][SUTRA_SERVER_NAME]
    assert entry == {"command": "sutra", "args": ["serve-mcp"]}


def test_run_writes_config_example_toml(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    settings = _settings(tmp_path, monkeypatch)
    result = run(settings)

    assert result.config_example_path == settings.paths.config_example_toml
    assert settings.paths.config_example_toml.exists()
    text = settings.paths.config_example_toml.read_text(encoding="utf-8")
    assert "[network]" in text
    assert "[paths]" in text


def test_run_does_not_create_live_config_toml(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = _settings(tmp_path, monkeypatch)
    run(settings)
    assert not settings.paths.config_toml.exists()


def test_run_overwrites_existing_config_example(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = _settings(tmp_path, monkeypatch)
    settings.paths.config_home.mkdir(parents=True, exist_ok=True)
    sentinel = "# SENTINEL_PRE_EXISTING_CONTENT_XYZ\n"
    settings.paths.config_example_toml.write_text(sentinel, encoding="utf-8")

    run(settings)

    text = settings.paths.config_example_toml.read_text(encoding="utf-8")
    assert "SENTINEL_PRE_EXISTING_CONTENT_XYZ" not in text
    assert "[network]" in text


def test_run_config_example_is_valid_toml_when_uncommented(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = _settings(tmp_path, monkeypatch)
    run(settings)
    text = settings.paths.config_example_toml.read_text(encoding="utf-8")
    activated_lines: list[str] = []
    for line in text.splitlines():
        if line.startswith("# ") and "=" in line and "<unset>" not in line:
            activated_lines.append(line[2:])
        else:
            activated_lines.append(line)
    parsed = tomllib.loads("\n".join(activated_lines))
    assert parsed["network"]["falkordb_port"] == 16379


def test_run_skips_launchctl_on_non_darwin(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    settings = _settings(tmp_path, monkeypatch)
    result = run(settings)
    assert result.launchd_skipped is True
    assert result.launchd_action == "skipped-non-darwin"


def test_run_invokes_launchctl_bootstrap_on_darwin(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = _settings(tmp_path, monkeypatch)
    monkeypatch.setattr(launchd_module.sys, "platform", "darwin")
    monkeypatch.setattr(launchd_module, "_is_loaded", lambda _s: False)

    calls: list[list[str]] = []

    def fake_run(argv: list[str], **_: object) -> object:
        calls.append(list(argv))

        class _R:
            returncode = 0
            stdout = b""
            stderr = b""

        return _R()

    monkeypatch.setattr(launchd_module.subprocess, "run", fake_run)

    result = run(settings)

    assert result.launchd_skipped is False
    assert result.launchd_action == "bootstrap"
    assert calls, "launchctl should have been invoked"
    assert calls[-1][0] == "/bin/launchctl"
    assert "bootstrap" in calls[-1]
