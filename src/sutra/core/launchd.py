"""Launchd user agent for FalkorDB supervision (macOS).

The plist at `SutraPaths.launchd_plist` keeps FalkorDB running. It restarts
on crash with a 10s throttle and reloads whenever the project registry or
config file is written (launchd `WatchPaths`).
"""

from __future__ import annotations

import plistlib
from pathlib import Path
from typing import TYPE_CHECKING, Any, NamedTuple

if TYPE_CHECKING:
    from sutra.core.paths import SutraPaths

DEFAULT_SUTRA_BINARY = Path("/opt/homebrew/bin/sutra")
_FALKORDB_LOG_FILENAME = "falkordb.log"
_FALKORDB_ERR_LOG_FILENAME = "falkordb.err.log"
_PLIST_MODE = 0o600


class WritePlistResult(NamedTuple):
    path: Path
    was_new: bool


def render_plist(paths: SutraPaths, *, sutra_binary: Path = DEFAULT_SUTRA_BINARY) -> bytes:
    """Render the FalkorDB launchd plist as XML bytes."""
    payload: dict[str, Any] = {
        "Label": paths.launchd_label,
        "ProgramArguments": [
            str(sutra_binary),
            "falkordb-serve",
            "--config",
            str(paths.config_toml),
        ],
        "RunAtLoad": True,
        "KeepAlive": {"Crashed": True, "SuccessfulExit": False},
        "ThrottleInterval": 10,
        "WatchPaths": [str(paths.projects_yaml), str(paths.config_toml)],
        "StandardOutPath": str(paths.log_home / _FALKORDB_LOG_FILENAME),
        "StandardErrorPath": str(paths.log_home / _FALKORDB_ERR_LOG_FILENAME),
    }
    return plistlib.dumps(payload)


def write_plist(
    paths: SutraPaths, *, sutra_binary: Path = DEFAULT_SUTRA_BINARY
) -> WritePlistResult:
    """Write the rendered plist. Return destination and whether it pre-existed."""
    paths.launch_agents_dir.mkdir(parents=True, exist_ok=True)
    dest = paths.launchd_plist
    was_new = not dest.exists()
    dest.write_bytes(render_plist(paths, sutra_binary=sutra_binary))
    dest.chmod(_PLIST_MODE)
    return WritePlistResult(dest, was_new)


def remove_plist(paths: SutraPaths) -> bool:
    """Delete the plist if present. Return True if it existed."""
    dest = paths.launchd_plist
    if not dest.exists():
        return False
    dest.unlink()
    return True
