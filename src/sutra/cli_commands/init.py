"""Orchestrator for `sutra init`.

Idempotent. Creates every user-scope directory, installs the FalkorDB launchd
plist, loads it into launchd, registers the sutra MCP server with Claude Code,
and writes the latest `config.example.toml` (live `config.toml` is never
touched).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from sutra.core import claude_mcp, launchd
from sutra.core.config_example import render_example_toml
from sutra.core.launchd import DEFAULT_SUTRA_BINARY
from sutra.core.settings import SutraSettings

if TYPE_CHECKING:
    from pathlib import Path


@dataclass
class InitResult:
    """Observable outcome of `run()`."""

    plist_path: Path
    plist_was_new: bool
    mcp_was_already_registered: bool
    config_example_path: Path
    launchd_action: str
    launchd_skipped: bool
    created_dirs: list[Path] = field(default_factory=list)
    existing_dirs: list[Path] = field(default_factory=list)


def run(
    settings: SutraSettings | None = None,
    *,
    sutra_binary: Path = DEFAULT_SUTRA_BINARY,
) -> InitResult:
    """Perform `sutra init`. Safe to re-run."""
    s = settings or SutraSettings()

    created: list[Path] = []
    existing: list[Path] = []
    for directory in s.paths.all_dirs():
        if directory.exists():
            existing.append(directory)
        else:
            directory.mkdir(parents=True, exist_ok=True)
            created.append(directory)

    plist = launchd.write_plist(s, sutra_binary=sutra_binary)
    bootstrap = launchd.bootstrap(s)

    mcp_already = claude_mcp.is_registered(s)
    claude_mcp.register(s)

    example_path = s.paths.config_example_toml
    example_path.write_text(render_example_toml(s), encoding="utf-8")

    return InitResult(
        plist_path=plist.path,
        plist_was_new=plist.was_new,
        mcp_was_already_registered=mcp_already,
        config_example_path=example_path,
        launchd_action=bootstrap.action,
        launchd_skipped=bootstrap.skipped,
        created_dirs=created,
        existing_dirs=existing,
    )
