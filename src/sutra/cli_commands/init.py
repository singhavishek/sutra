"""Orchestrator for `sutra init`.

Idempotent. Creates every user-scope directory, installs the FalkorDB
launchd plist, and registers the sutra MCP server with Claude Code.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from sutra.core import claude_mcp, launchd
from sutra.core.launchd import DEFAULT_SUTRA_BINARY
from sutra.core.paths import SutraPaths

if TYPE_CHECKING:
    from pathlib import Path


@dataclass
class InitResult:
    """Observable outcome of `run()`."""

    plist_path: Path
    plist_was_new: bool
    mcp_was_already_registered: bool
    created_dirs: list[Path] = field(default_factory=list)
    existing_dirs: list[Path] = field(default_factory=list)


def run(
    paths: SutraPaths | None = None,
    *,
    sutra_binary: Path = DEFAULT_SUTRA_BINARY,
) -> InitResult:
    """Perform `sutra init`. Safe to re-run."""
    p = paths or SutraPaths()

    created: list[Path] = []
    existing: list[Path] = []
    for directory in p.all_dirs():
        if directory.exists():
            existing.append(directory)
        else:
            directory.mkdir(parents=True, exist_ok=True)
            created.append(directory)

    plist = launchd.write_plist(p, sutra_binary=sutra_binary)
    mcp_already = claude_mcp.is_registered(p)
    claude_mcp.register(p)

    return InitResult(
        plist_path=plist.path,
        plist_was_new=plist.was_new,
        mcp_was_already_registered=mcp_already,
        created_dirs=created,
        existing_dirs=existing,
    )
