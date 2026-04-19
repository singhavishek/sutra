"""`sutra falkordb-serve`. Exec FalkorDB inside this process.

Designed to be the launchd `ProgramArguments` target. Runs `redis-server`
with the FalkorDB module loaded, in the foreground, bound to loopback only,
on the ports configured in `SutraSettings.network`.

`os.execvp` replaces the Python process so launchd supervises the real
redis-server PID rather than a Python parent.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import TYPE_CHECKING, NoReturn

if TYPE_CHECKING:
    from sutra.core.settings import SutraSettings


_DEFAULT_MODULE_LOCATIONS: tuple[Path, ...] = (
    Path("/opt/homebrew/lib/falkordb.so"),
    Path("/opt/homebrew/Cellar/falkordb/lib/falkordb.so"),
    Path("/usr/local/lib/falkordb.so"),
)


class FalkorDBSetupError(RuntimeError):
    """Raised when FalkorDB prerequisites cannot be located."""


def discover_redis_server(settings: SutraSettings) -> Path:
    """Locate the redis-server binary. Raise with install hint if absent."""
    explicit = settings.falkordb.redis_server_binary
    if explicit is not None:
        if not explicit.exists():
            msg = (
                f"redis-server not found at configured path {explicit}. "
                f"Install via 'brew install redis' or unset SUTRA_FALKORDB__REDIS_SERVER_BINARY."
            )
            raise FalkorDBSetupError(msg)
        return explicit

    found = shutil.which("redis-server")
    if found is None:
        msg = (
            "redis-server not found on PATH. Install via 'brew install redis' or set "
            "SUTRA_FALKORDB__REDIS_SERVER_BINARY to its absolute path."
        )
        raise FalkorDBSetupError(msg)
    return Path(found)


def discover_module(settings: SutraSettings) -> Path:
    """Locate falkordb.so. Raise with install hint if absent."""
    explicit = settings.falkordb.module_path
    if explicit is not None:
        if not explicit.exists():
            msg = (
                f"FalkorDB module not found at configured path {explicit}. "
                f"Install via 'brew install falkordb' or fix SUTRA_FALKORDB__MODULE_PATH."
            )
            raise FalkorDBSetupError(msg)
        return explicit

    for candidate in _DEFAULT_MODULE_LOCATIONS:
        if candidate.exists():
            return candidate

    searched = ", ".join(str(p) for p in _DEFAULT_MODULE_LOCATIONS)
    msg = (
        f"FalkorDB module (falkordb.so) not found in any standard location ({searched}). "
        f"Install via 'brew install falkordb' or set SUTRA_FALKORDB__MODULE_PATH."
    )
    raise FalkorDBSetupError(msg)


def build_args(settings: SutraSettings, redis_server: Path, module: Path) -> list[str]:
    """Assemble the redis-server argv for FalkorDB."""
    data_dir = settings.falkordb.data_dir or settings.paths.graph_dir
    return [
        str(redis_server),
        "--bind",
        "127.0.0.1",
        "--port",
        str(settings.network.falkordb_port),
        "--dir",
        str(data_dir),
        "--loadmodule",
        str(module),
        "BOLT_PORT",
        str(settings.network.bolt_port),
    ]


def run(settings: SutraSettings) -> NoReturn:
    """Discover dependencies, ensure data dir exists, exec redis-server."""
    redis_server = discover_redis_server(settings)
    module = discover_module(settings)

    data_dir = settings.falkordb.data_dir or settings.paths.graph_dir
    data_dir.mkdir(parents=True, exist_ok=True)

    args = build_args(settings, redis_server, module)
    os.execvp(args[0], args)  # noqa: S606  # intentional: replace process with redis-server
    raise AssertionError("execvp returned; this is unreachable")  # pragma: no cover
