"""User-scope filesystem paths for sutra.

Every configurable path is overridable via `SUTRA_*` environment variables so
tests never touch real system locations. Production defaults target macOS
user conventions per `docs/sutra-architecture.md` §4.2.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


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


class SutraPaths(BaseSettings):
    """Canonical filesystem paths for sutra's user-scope state."""

    model_config = SettingsConfigDict(
        env_prefix="SUTRA_",
        env_file=None,
        extra="ignore",
    )

    config_home: Path = Field(default_factory=_default_config_home)
    data_home: Path = Field(default_factory=_default_data_home)
    log_home: Path = Field(default_factory=_default_log_home)
    launch_agents_dir: Path = Field(default_factory=_default_launch_agents_dir)
    claude_mcp_config_path: Path = Field(default_factory=_default_claude_mcp_config_path)
    launchd_label: str = "ai.sutra.falkordb"

    @property
    def config_toml(self) -> Path:
        return self.config_home / "config.toml"

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
