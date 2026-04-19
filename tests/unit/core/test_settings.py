"""Tests for sutra.core.settings."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from sutra.core.settings import NetworkSettings, PathsSettings, SutraSettings

if TYPE_CHECKING:
    from pathlib import Path


_ENV_VARS = (
    "SUTRA_PATHS__CONFIG_HOME",
    "SUTRA_PATHS__DATA_HOME",
    "SUTRA_PATHS__LOG_HOME",
    "SUTRA_PATHS__LAUNCH_AGENTS_DIR",
    "SUTRA_PATHS__CLAUDE_MCP_CONFIG_PATH",
    "SUTRA_PATHS__LAUNCHD_LABEL",
    "SUTRA_NETWORK__FALKORDB_PORT",
    "SUTRA_NETWORK__BOLT_PORT",
    "SUTRA_CONFIG_TOML",
)


def _clear_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in _ENV_VARS:
        monkeypatch.delenv(var, raising=False)


def _settings(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, **env: str) -> SutraSettings:
    _clear_env(monkeypatch)
    monkeypatch.setenv("SUTRA_CONFIG_TOML", str(tmp_path / "missing.toml"))
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    return SutraSettings()


# --- defaults ---------------------------------------------------------------


def test_paths_defaults_are_user_scoped(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    s = _settings(monkeypatch, tmp_path)
    assert s.paths.config_home.is_absolute()
    assert str(s.paths.config_home).endswith("/.sutra")
    assert "Application Support/sutra" in str(s.paths.data_home)
    assert "Logs/sutra" in str(s.paths.log_home)
    assert str(s.paths.launch_agents_dir).endswith("/Library/LaunchAgents")
    assert s.paths.claude_mcp_config_path.name == ".claude.json"
    assert s.paths.launchd_label == "ai.sutra.falkordb"


def test_network_defaults_avoid_common_port_clashes(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    s = _settings(monkeypatch, tmp_path)
    assert s.network.falkordb_port == 16379
    assert s.network.bolt_port == 17687


# --- nested env overrides ---------------------------------------------------


def test_nested_env_overrides_paths(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    cfg = tmp_path / "cfg"
    s = _settings(monkeypatch, tmp_path, SUTRA_PATHS__CONFIG_HOME=str(cfg))
    assert s.paths.config_home == cfg


def test_nested_env_overrides_network(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    s = _settings(
        monkeypatch,
        tmp_path,
        SUTRA_NETWORK__FALKORDB_PORT="26379",
        SUTRA_NETWORK__BOLT_PORT="27687",
    )
    assert s.network.falkordb_port == 26379
    assert s.network.bolt_port == 27687


def test_launchd_label_overridable(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    s = _settings(
        monkeypatch,
        tmp_path,
        SUTRA_PATHS__LAUNCHD_LABEL="com.example.custom",
        SUTRA_PATHS__LAUNCH_AGENTS_DIR=str(tmp_path),
    )
    assert s.paths.launchd_label == "com.example.custom"
    assert s.paths.launchd_plist == tmp_path / "com.example.custom.plist"


def test_launchd_label_rejects_path_traversal(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _clear_env(monkeypatch)
    monkeypatch.setenv("SUTRA_PATHS__LAUNCHD_LABEL", "../../../etc/passwd")
    with pytest.raises(ValueError, match="launchd_label"):
        SutraSettings()


def test_launchd_label_rejects_shell_metacharacters(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _clear_env(monkeypatch)
    monkeypatch.setenv("SUTRA_PATHS__LAUNCHD_LABEL", "evil; rm -rf /")
    with pytest.raises(ValueError, match="launchd_label"):
        SutraSettings()


# --- derived properties -----------------------------------------------------


def test_derived_config_paths(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    s = _settings(monkeypatch, tmp_path, SUTRA_PATHS__CONFIG_HOME=str(tmp_path))
    assert s.paths.config_toml == tmp_path / "config.toml"
    assert s.paths.config_example_toml == tmp_path / "config.example.toml"
    assert s.paths.projects_yaml == tmp_path / "projects.yaml"
    assert s.paths.rules_dir == tmp_path / "rules"
    assert s.paths.ignore_default == tmp_path / "ignore.default"


def test_derived_data_paths(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    s = _settings(monkeypatch, tmp_path, SUTRA_PATHS__DATA_HOME=str(tmp_path))
    assert s.paths.graph_dir == tmp_path / "graph"
    assert s.paths.vectors_dir == tmp_path / "vectors"
    assert s.paths.metadata_dir == tmp_path / "metadata"
    assert s.paths.cache_dir == tmp_path / "cache"
    assert s.paths.models_dir == tmp_path / "models"


def test_derived_log_paths(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    s = _settings(monkeypatch, tmp_path, SUTRA_PATHS__LOG_HOME=str(tmp_path))
    assert s.paths.audit_log_dir == tmp_path / "audit"


def test_all_dirs_returns_every_init_target(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    s = _settings(
        monkeypatch,
        tmp_path,
        SUTRA_PATHS__CONFIG_HOME=str(tmp_path / "cfg"),
        SUTRA_PATHS__DATA_HOME=str(tmp_path / "data"),
        SUTRA_PATHS__LOG_HOME=str(tmp_path / "logs"),
    )
    assert set(s.paths.all_dirs()) == {
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


# --- TOML source ------------------------------------------------------------


def test_missing_toml_is_silent(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _clear_env(monkeypatch)
    monkeypatch.setenv("SUTRA_CONFIG_TOML", str(tmp_path / "does_not_exist.toml"))
    s = SutraSettings()
    assert s.network.falkordb_port == 16379


def test_toml_overrides_defaults(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    toml = tmp_path / "config.toml"
    toml.write_text(
        "[network]\nfalkordb_port = 36379\nbolt_port = 37687\n",
        encoding="utf-8",
    )
    _clear_env(monkeypatch)
    monkeypatch.setenv("SUTRA_CONFIG_TOML", str(toml))
    s = SutraSettings()
    assert s.network.falkordb_port == 36379
    assert s.network.bolt_port == 37687


def test_env_beats_toml(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    toml = tmp_path / "config.toml"
    toml.write_text("[network]\nfalkordb_port = 36379\n", encoding="utf-8")
    _clear_env(monkeypatch)
    monkeypatch.setenv("SUTRA_CONFIG_TOML", str(toml))
    monkeypatch.setenv("SUTRA_NETWORK__FALKORDB_PORT", "46379")
    s = SutraSettings()
    assert s.network.falkordb_port == 46379


def test_init_kwargs_beat_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _clear_env(monkeypatch)
    monkeypatch.setenv("SUTRA_CONFIG_TOML", str(tmp_path / "missing.toml"))
    monkeypatch.setenv("SUTRA_NETWORK__FALKORDB_PORT", "46379")
    s = SutraSettings(network=NetworkSettings(falkordb_port=56379))
    assert s.network.falkordb_port == 56379


# --- sub-models construct independently for tests ---------------------------


def test_sub_models_are_directly_constructable() -> None:
    p = PathsSettings()
    n = NetworkSettings()
    assert p.launchd_label == "ai.sutra.falkordb"
    assert n.falkordb_port == 16379
