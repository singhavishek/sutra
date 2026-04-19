"""Sutra runtime settings. Source precedence: init > env (SUTRA_*__*) > TOML > defaults."""

from __future__ import annotations

import os
import re
from pathlib import Path

from pydantic import BaseModel, Field, field_validator
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    TomlConfigSettingsSource,
)

_LAUNCHD_LABEL_RE = re.compile(r"^[A-Za-z0-9._-]+$")


# --- defaults ---------------------------------------------------------------


def _default_config_home() -> Path:
    return Path.home() / ".sutra"


def _default_data_home() -> Path:
    return Path.home() / "Library" / "Application Support" / "sutra"


def _default_log_home() -> Path:
    return Path.home() / "Library" / "Logs" / "sutra"


def _default_launch_agents_dir() -> Path:
    return Path.home() / "Library" / "LaunchAgents"


def _default_claude_mcp_config_path() -> Path:
    return Path.home() / ".claude.json"


def _resolved_toml_path() -> Path:
    """Resolve the active TOML config path, honouring SUTRA_CONFIG_TOML."""
    override = os.environ.get("SUTRA_CONFIG_TOML")
    if override:
        return Path(override)
    return _default_config_home() / "config.toml"


# --- sub-models -------------------------------------------------------------


class PathsSettings(BaseModel):
    """Filesystem locations for sutra's user-scope state."""

    config_home: Path = Field(default_factory=_default_config_home)
    data_home: Path = Field(default_factory=_default_data_home)
    log_home: Path = Field(default_factory=_default_log_home)
    launch_agents_dir: Path = Field(default_factory=_default_launch_agents_dir)
    claude_mcp_config_path: Path = Field(default_factory=_default_claude_mcp_config_path)
    launchd_label: str = "ai.sutra.falkordb"

    @field_validator("launchd_label")
    @classmethod
    def _validate_launchd_label(cls, value: str) -> str:
        if not _LAUNCHD_LABEL_RE.fullmatch(value):
            msg = (
                f"Invalid launchd_label {value!r}: must match [A-Za-z0-9._-]+ "
                f"(no path separators, whitespace, or shell metacharacters)."
            )
            raise ValueError(msg)
        return value

    @property
    def config_toml(self) -> Path:
        return self.config_home / "config.toml"

    @property
    def config_example_toml(self) -> Path:
        return self.config_home / "config.example.toml"

    @property
    def projects_yaml(self) -> Path:
        return self.config_home / "projects.yaml"

    @property
    def rules_dir(self) -> Path:
        return self.config_home / "rules"

    @property
    def ignore_default(self) -> Path:
        return self.config_home / "ignore.default"

    @property
    def graph_dir(self) -> Path:
        return self.data_home / "graph"

    @property
    def vectors_dir(self) -> Path:
        return self.data_home / "vectors"

    @property
    def metadata_dir(self) -> Path:
        return self.data_home / "metadata"

    @property
    def cache_dir(self) -> Path:
        return self.data_home / "cache"

    @property
    def models_dir(self) -> Path:
        return self.data_home / "models"

    @property
    def audit_log_dir(self) -> Path:
        return self.log_home / "audit"

    @property
    def launchd_plist(self) -> Path:
        return self.launch_agents_dir / f"{self.launchd_label}.plist"

    def all_dirs(self) -> list[Path]:
        """Return every directory that `sutra init` must ensure exists."""
        return [
            self.config_home,
            self.rules_dir,
            self.graph_dir,
            self.vectors_dir,
            self.metadata_dir,
            self.cache_dir,
            self.models_dir,
            self.log_home,
            self.audit_log_dir,
        ]


class NetworkSettings(BaseModel):
    """TCP ports for sutra services."""

    falkordb_port: int = Field(
        default=16379,
        description="Redis-protocol port FalkorDB listens on. Default: 16379 (Redis +10000).",
    )
    bolt_port: int = Field(
        default=17687,
        description="Bolt-protocol port FalkorDB listens on. Default: 17687 (Neo4j Bolt +10000).",
    )


class FalkorDBSettings(BaseModel):
    """Discovery hints for the FalkorDB Redis module and host binary."""

    redis_server_binary: Path | None = Field(
        default=None,
        description="Absolute path to redis-server. Falls back to PATH lookup.",
    )
    module_path: Path | None = Field(
        default=None,
        description="Absolute path to falkordb.so. Falls back to standard install locations.",
    )
    data_dir: Path | None = Field(
        default=None,
        description="Working directory for redis-server (rdb/aof). Defaults to paths.graph_dir.",
    )


# --- root -------------------------------------------------------------------


class SutraSettings(BaseSettings):
    """Root settings object. Construct once per process; pass to consumers."""

    model_config = SettingsConfigDict(
        env_prefix="SUTRA_",
        env_nested_delimiter="__",
        env_file=None,
        extra="ignore",
    )

    paths: PathsSettings = Field(default_factory=PathsSettings)
    network: NetworkSettings = Field(default_factory=NetworkSettings)
    falkordb: FalkorDBSettings = Field(default_factory=FalkorDBSettings)

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        toml_path = _resolved_toml_path()
        toml_source = TomlConfigSettingsSource(settings_cls, toml_file=toml_path)
        return (init_settings, env_settings, toml_source)
