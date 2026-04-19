"""Tests for sutra.core.paths."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sutra.core.paths import SutraPaths

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

_ENV_VARS = (
    "SUTRA_CONFIG_HOME",
    "SUTRA_DATA_HOME",
    "SUTRA_LOG_HOME",
    "SUTRA_LAUNCH_AGENTS_DIR",
    "SUTRA_CLAUDE_MCP_CONFIG_PATH",
    "SUTRA_LAUNCHD_LABEL",
)


def _clear_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in _ENV_VARS:
        monkeypatch.delenv(var, raising=False)


def test_defaults_are_absolute_and_user_scoped(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_env(monkeypatch)
    paths = SutraPaths()
    assert paths.config_home.is_absolute()
    assert paths.data_home.is_absolute()
    assert paths.log_home.is_absolute()
    assert paths.launch_agents_dir.is_absolute()
    assert paths.claude_mcp_config_path.is_absolute()
    assert str(paths.config_home).endswith("/.sutra")
    assert "Application Support/sutra" in str(paths.data_home)
    assert "Logs/sutra" in str(paths.log_home)
    assert str(paths.launch_agents_dir).endswith("/Library/LaunchAgents")
    assert paths.claude_mcp_config_path.name == ".claude.json"


def test_env_overrides_every_configurable_path(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config = tmp_path / "cfg"
    data = tmp_path / "data"
    logs = tmp_path / "logs"
    la_dir = tmp_path / "launchagents"
    mcp = tmp_path / ".claude.json"
    monkeypatch.setenv("SUTRA_CONFIG_HOME", str(config))
    monkeypatch.setenv("SUTRA_DATA_HOME", str(data))
    monkeypatch.setenv("SUTRA_LOG_HOME", str(logs))
    monkeypatch.setenv("SUTRA_LAUNCH_AGENTS_DIR", str(la_dir))
    monkeypatch.setenv("SUTRA_CLAUDE_MCP_CONFIG_PATH", str(mcp))

    paths = SutraPaths()

    assert paths.config_home == config
    assert paths.data_home == data
    assert paths.log_home == logs
    assert paths.launch_agents_dir == la_dir
    assert paths.claude_mcp_config_path == mcp


def test_derived_config_paths(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("SUTRA_CONFIG_HOME", str(tmp_path))
    paths = SutraPaths()
    assert paths.config_toml == tmp_path / "config.toml"
    assert paths.projects_yaml == tmp_path / "projects.yaml"
    assert paths.rules_dir == tmp_path / "rules"
    assert paths.ignore_default == tmp_path / "ignore.default"


def test_derived_data_paths(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("SUTRA_DATA_HOME", str(tmp_path))
    paths = SutraPaths()
    assert paths.graph_dir == tmp_path / "graph"
    assert paths.vectors_dir == tmp_path / "vectors"
    assert paths.metadata_dir == tmp_path / "metadata"
    assert paths.cache_dir == tmp_path / "cache"
    assert paths.models_dir == tmp_path / "models"


def test_derived_log_paths(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("SUTRA_LOG_HOME", str(tmp_path))
    paths = SutraPaths()
    assert paths.audit_log_dir == tmp_path / "audit"


def test_launchd_plist_uses_reverse_dns_label(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _clear_env(monkeypatch)
    monkeypatch.setenv("SUTRA_LAUNCH_AGENTS_DIR", str(tmp_path))
    paths = SutraPaths()
    assert paths.launchd_label == "ai.sutra.falkordb"
    assert paths.launchd_plist == tmp_path / "ai.sutra.falkordb.plist"


def test_launchd_label_overridable(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("SUTRA_LAUNCH_AGENTS_DIR", str(tmp_path))
    monkeypatch.setenv("SUTRA_LAUNCHD_LABEL", "com.example.custom")
    paths = SutraPaths()
    assert paths.launchd_label == "com.example.custom"
    assert paths.launchd_plist == tmp_path / "com.example.custom.plist"


def test_all_dirs_returns_every_init_target(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("SUTRA_CONFIG_HOME", str(tmp_path / "cfg"))
    monkeypatch.setenv("SUTRA_DATA_HOME", str(tmp_path / "data"))
    monkeypatch.setenv("SUTRA_LOG_HOME", str(tmp_path / "logs"))
    paths = SutraPaths()

    assert set(paths.all_dirs()) == {
        tmp_path / "cfg",
        tmp_path / "cfg" / "rules",
        tmp_path / "data" / "graph",
        tmp_path / "data" / "vectors",
        tmp_path / "data" / "metadata",
        tmp_path / "data" / "cache",
        tmp_path / "data" / "models",
        tmp_path / "logs",
        tmp_path / "logs" / "audit",
    }
