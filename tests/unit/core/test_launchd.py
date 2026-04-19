"""Tests for sutra.core.launchd."""

from __future__ import annotations

import plistlib
from pathlib import Path
from typing import TYPE_CHECKING

from sutra.core.launchd import remove_plist, render_plist, write_plist
from sutra.core.settings import SutraSettings

if TYPE_CHECKING:
    import pytest


def _settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> SutraSettings:
    monkeypatch.setenv("SUTRA_PATHS__CONFIG_HOME", str(tmp_path / "cfg"))
    monkeypatch.setenv("SUTRA_PATHS__DATA_HOME", str(tmp_path / "data"))
    monkeypatch.setenv("SUTRA_PATHS__LOG_HOME", str(tmp_path / "logs"))
    monkeypatch.setenv("SUTRA_PATHS__LAUNCH_AGENTS_DIR", str(tmp_path / "launchagents"))
    monkeypatch.delenv("SUTRA_PATHS__LAUNCHD_LABEL", raising=False)
    return SutraSettings()


def test_render_plist_contains_required_keys(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = _settings(tmp_path, monkeypatch)
    data = plistlib.loads(render_plist(settings))
    assert data["Label"] == "ai.sutra.falkordb"
    assert data["RunAtLoad"] is True
    assert data["KeepAlive"] == {"Crashed": True, "SuccessfulExit": False}
    assert data["ThrottleInterval"] == 10
    assert "ProgramArguments" in data
    assert "WatchPaths" in data
    assert "StandardOutPath" in data
    assert "StandardErrorPath" in data


def test_render_plist_label_follows_settings(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SUTRA_PATHS__LAUNCH_AGENTS_DIR", str(tmp_path))
    monkeypatch.setenv("SUTRA_PATHS__LAUNCHD_LABEL", "com.example.custom")
    settings = SutraSettings()
    data = plistlib.loads(render_plist(settings))
    assert data["Label"] == "com.example.custom"


def test_render_plist_program_arguments_point_to_falkordb_serve(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = _settings(tmp_path, monkeypatch)
    data = plistlib.loads(render_plist(settings))
    args = data["ProgramArguments"]
    assert args == ["/opt/homebrew/bin/sutra", "falkordb-serve"]


def test_render_plist_sutra_binary_overridable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = _settings(tmp_path, monkeypatch)
    data = plistlib.loads(render_plist(settings, sutra_binary=Path("/usr/local/bin/sutra")))
    assert data["ProgramArguments"][0] == "/usr/local/bin/sutra"


def test_render_plist_watchpaths_cover_registry_and_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = _settings(tmp_path, monkeypatch)
    data = plistlib.loads(render_plist(settings))
    watch = set(data["WatchPaths"])
    assert str(settings.paths.projects_yaml) in watch
    assert str(settings.paths.config_toml) in watch


def test_render_plist_standard_out_and_err_point_at_falkordb_logs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = _settings(tmp_path, monkeypatch)
    data = plistlib.loads(render_plist(settings))
    assert data["StandardOutPath"] == str(settings.paths.log_home / "falkordb.log")
    assert data["StandardErrorPath"] == str(settings.paths.log_home / "falkordb.err.log")


def test_write_plist_creates_launch_agents_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = _settings(tmp_path, monkeypatch)
    assert not settings.paths.launch_agents_dir.exists()
    result = write_plist(settings)
    assert result.path == settings.paths.launchd_plist
    assert result.was_new is True
    assert result.path.exists()
    assert result.path.read_bytes().startswith(b"<?xml")


def test_write_plist_reports_not_new_on_second_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = _settings(tmp_path, monkeypatch)
    write_plist(settings)
    assert write_plist(settings).was_new is False


def test_write_plist_overwrites_existing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    settings = _settings(tmp_path, monkeypatch)
    write_plist(settings)
    first = plistlib.loads(settings.paths.launchd_plist.read_bytes())
    write_plist(settings, sutra_binary=Path("/usr/local/bin/sutra"))
    second = plistlib.loads(settings.paths.launchd_plist.read_bytes())
    assert first["ProgramArguments"][0] == "/opt/homebrew/bin/sutra"
    assert second["ProgramArguments"][0] == "/usr/local/bin/sutra"


def test_write_plist_sets_mode_0o600(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    settings = _settings(tmp_path, monkeypatch)
    write_plist(settings)
    assert (settings.paths.launchd_plist.stat().st_mode & 0o777) == 0o600


def test_remove_plist_returns_true_when_present(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = _settings(tmp_path, monkeypatch)
    write_plist(settings)
    assert remove_plist(settings) is True
    assert not settings.paths.launchd_plist.exists()


def test_remove_plist_returns_false_when_absent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = _settings(tmp_path, monkeypatch)
    assert remove_plist(settings) is False
