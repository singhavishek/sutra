"""Tests for sutra.core.launchd."""

from __future__ import annotations

import plistlib
from pathlib import Path
from typing import TYPE_CHECKING

from sutra.core.launchd import remove_plist, render_plist, write_plist
from sutra.core.paths import SutraPaths

if TYPE_CHECKING:
    import pytest


def _paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> SutraPaths:
    monkeypatch.setenv("SUTRA_CONFIG_HOME", str(tmp_path / "cfg"))
    monkeypatch.setenv("SUTRA_DATA_HOME", str(tmp_path / "data"))
    monkeypatch.setenv("SUTRA_LOG_HOME", str(tmp_path / "logs"))
    monkeypatch.setenv("SUTRA_LAUNCH_AGENTS_DIR", str(tmp_path / "launchagents"))
    monkeypatch.delenv("SUTRA_LAUNCHD_LABEL", raising=False)
    return SutraPaths()


def test_render_plist_contains_required_keys(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths = _paths(tmp_path, monkeypatch)
    data = plistlib.loads(render_plist(paths))
    assert data["Label"] == "ai.sutra.falkordb"
    assert data["RunAtLoad"] is True
    assert data["KeepAlive"] == {"Crashed": True, "SuccessfulExit": False}
    assert data["ThrottleInterval"] == 10
    assert "ProgramArguments" in data
    assert "WatchPaths" in data
    assert "StandardOutPath" in data
    assert "StandardErrorPath" in data


def test_render_plist_label_follows_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SUTRA_LAUNCH_AGENTS_DIR", str(tmp_path))
    monkeypatch.setenv("SUTRA_LAUNCHD_LABEL", "com.example.custom")
    paths = SutraPaths()
    data = plistlib.loads(render_plist(paths))
    assert data["Label"] == "com.example.custom"


def test_render_plist_program_arguments_point_to_falkordb_serve(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths = _paths(tmp_path, monkeypatch)
    data = plistlib.loads(render_plist(paths))
    args = data["ProgramArguments"]
    assert args[0] == "/opt/homebrew/bin/sutra"
    assert "falkordb-serve" in args
    assert "--config" in args
    assert str(paths.config_toml) in args


def test_render_plist_sutra_binary_overridable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths = _paths(tmp_path, monkeypatch)
    data = plistlib.loads(render_plist(paths, sutra_binary=Path("/usr/local/bin/sutra")))
    assert data["ProgramArguments"][0] == "/usr/local/bin/sutra"


def test_render_plist_watchpaths_cover_registry_and_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths = _paths(tmp_path, monkeypatch)
    data = plistlib.loads(render_plist(paths))
    watch = set(data["WatchPaths"])
    assert str(paths.projects_yaml) in watch
    assert str(paths.config_toml) in watch


def test_render_plist_standard_out_and_err_point_at_falkordb_logs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths = _paths(tmp_path, monkeypatch)
    data = plistlib.loads(render_plist(paths))
    assert data["StandardOutPath"] == str(paths.log_home / "falkordb.log")
    assert data["StandardErrorPath"] == str(paths.log_home / "falkordb.err.log")


def test_write_plist_creates_launch_agents_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths = _paths(tmp_path, monkeypatch)
    assert not paths.launch_agents_dir.exists()
    result = write_plist(paths)
    assert result.path == paths.launchd_plist
    assert result.was_new is True
    assert result.path.exists()
    assert result.path.read_bytes().startswith(b"<?xml")


def test_write_plist_reports_not_new_on_second_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths = _paths(tmp_path, monkeypatch)
    write_plist(paths)
    assert write_plist(paths).was_new is False


def test_write_plist_overwrites_existing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    paths = _paths(tmp_path, monkeypatch)
    write_plist(paths)
    first = plistlib.loads(paths.launchd_plist.read_bytes())
    write_plist(paths, sutra_binary=Path("/usr/local/bin/sutra"))
    second = plistlib.loads(paths.launchd_plist.read_bytes())
    assert first["ProgramArguments"][0] == "/opt/homebrew/bin/sutra"
    assert second["ProgramArguments"][0] == "/usr/local/bin/sutra"


def test_write_plist_sets_mode_0o600(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    paths = _paths(tmp_path, monkeypatch)
    write_plist(paths)
    assert (paths.launchd_plist.stat().st_mode & 0o777) == 0o600


def test_remove_plist_returns_true_when_present(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths = _paths(tmp_path, monkeypatch)
    write_plist(paths)
    assert remove_plist(paths) is True
    assert not paths.launchd_plist.exists()


def test_remove_plist_returns_false_when_absent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths = _paths(tmp_path, monkeypatch)
    assert remove_plist(paths) is False
