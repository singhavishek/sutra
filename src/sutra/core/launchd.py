"""Launchd user agent for FalkorDB supervision (macOS).

The plist at `SutraSettings.paths.launchd_plist` keeps FalkorDB running. It
restarts on crash with a 10s throttle and reloads whenever the project
registry or config file is written (launchd `WatchPaths`).
"""

from __future__ import annotations

import os
import plistlib
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any, NamedTuple

if TYPE_CHECKING:
    from sutra.core.settings import SutraSettings

DEFAULT_SUTRA_BINARY = Path("/opt/homebrew/bin/sutra")
_FALKORDB_LOG_FILENAME = "falkordb.log"
_FALKORDB_ERR_LOG_FILENAME = "falkordb.err.log"
_PLIST_MODE = 0o600
_LAUNCHCTL = "/bin/launchctl"


class WritePlistResult(NamedTuple):
    path: Path
    was_new: bool


class BootstrapResult(NamedTuple):
    action: str
    skipped: bool


class LaunchctlError(RuntimeError):
    """Raised when a launchctl invocation exits non-zero."""


def render_plist(settings: SutraSettings, *, sutra_binary: Path = DEFAULT_SUTRA_BINARY) -> bytes:
    """Render the FalkorDB launchd plist as XML bytes."""
    paths = settings.paths
    payload: dict[str, Any] = {
        "Label": paths.launchd_label,
        "ProgramArguments": [str(sutra_binary), "falkordb-serve"],
        "RunAtLoad": True,
        "KeepAlive": {"Crashed": True, "SuccessfulExit": False},
        "ThrottleInterval": 10,
        "WatchPaths": [str(paths.projects_yaml), str(paths.config_toml)],
        "StandardOutPath": str(paths.log_home / _FALKORDB_LOG_FILENAME),
        "StandardErrorPath": str(paths.log_home / _FALKORDB_ERR_LOG_FILENAME),
    }
    return plistlib.dumps(payload)


def write_plist(
    settings: SutraSettings, *, sutra_binary: Path = DEFAULT_SUTRA_BINARY
) -> WritePlistResult:
    """Write the rendered plist. Return destination and whether it pre-existed."""
    paths = settings.paths
    paths.launch_agents_dir.mkdir(parents=True, exist_ok=True)
    dest = paths.launchd_plist
    was_new = not dest.exists()
    dest.write_bytes(render_plist(settings, sutra_binary=sutra_binary))
    dest.chmod(_PLIST_MODE)
    return WritePlistResult(dest, was_new)


def remove_plist(settings: SutraSettings) -> bool:
    """Delete the plist if present. Return True if it existed."""
    dest = settings.paths.launchd_plist
    if not dest.exists():
        return False
    dest.unlink()
    return True


def bootstrap(settings: SutraSettings) -> BootstrapResult:
    """Load (or reload) the plist into the user's launchd domain.

    No-ops cleanly on non-Darwin. Bootstrap when unloaded, kickstart to pick
    up edits when already loaded. Idempotent for a plist that already matches.
    """
    if sys.platform != "darwin":
        return BootstrapResult(action="skipped-non-darwin", skipped=True)

    uid = os.getuid()
    domain = f"gui/{uid}"
    service = f"{domain}/{settings.paths.launchd_label}"

    if _is_loaded(settings):
        argv = [_LAUNCHCTL, "kickstart", "-k", service]
        action = "kickstart"
    else:
        argv = [_LAUNCHCTL, "bootstrap", domain, str(settings.paths.launchd_plist)]
        action = "bootstrap"

    proc = subprocess.run(argv, capture_output=True, check=False)  # noqa: S603
    if proc.returncode != 0:
        stderr = proc.stderr.decode("utf-8", errors="replace").strip()
        msg = f"launchctl {action} failed (rc={proc.returncode}): {stderr}"
        raise LaunchctlError(msg)

    return BootstrapResult(action=action, skipped=False)


def _is_loaded(settings: SutraSettings) -> bool:
    """Return True if `launchctl print` reports the service is loaded."""
    if sys.platform != "darwin":
        return False
    uid = os.getuid()
    service = f"gui/{uid}/{settings.paths.launchd_label}"
    proc = subprocess.run(  # noqa: S603
        [_LAUNCHCTL, "print", service],
        capture_output=True,
        check=False,
    )
    return proc.returncode == 0
