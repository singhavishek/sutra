"""User-scope Claude Code MCP registration for sutra.

sutra registers as a user-scope MCP server at the top-level `mcpServers.sutra`
key of `~/.claude.json` (overridable via `SUTRA_CLAUDE_MCP_CONFIG_PATH`).
User-scope servers load across every project for this user.

Writes are atomic (temp file + os.replace) so a crash mid-write leaves the
existing config intact.
"""

from __future__ import annotations

import contextlib
import json
import os
import tempfile
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

    from sutra.core.paths import SutraPaths

SUTRA_SERVER_NAME = "sutra"
DEFAULT_COMMAND = "sutra"
DEFAULT_ARGS: tuple[str, ...] = ("serve-mcp",)
_CONFIG_MODE = 0o600


def is_registered(paths: SutraPaths) -> bool:
    """Return True if sutra is registered at the user scope."""
    config = _load(paths.claude_mcp_config_path)
    servers = config.get("mcpServers", {})
    return isinstance(servers, dict) and SUTRA_SERVER_NAME in servers


def register(
    paths: SutraPaths,
    *,
    command: str = DEFAULT_COMMAND,
    args: tuple[str, ...] | list[str] = DEFAULT_ARGS,
) -> None:
    """Add or update the sutra entry. Preserve other keys and servers."""
    path = paths.claude_mcp_config_path
    config = _load(path)
    servers = config.setdefault("mcpServers", {})
    if not isinstance(servers, dict):
        msg = f"Expected 'mcpServers' in {path} to be a JSON object, got {type(servers).__name__}."
        raise ValueError(msg)
    servers[SUTRA_SERVER_NAME] = {"command": command, "args": list(args)}
    _atomic_write(path, config)


def unregister(paths: SutraPaths) -> bool:
    """Remove the sutra entry. Return True if it was present."""
    path = paths.claude_mcp_config_path
    if not path.exists():
        return False
    config = _load(path)
    servers = config.get("mcpServers")
    if not isinstance(servers, dict) or SUTRA_SERVER_NAME not in servers:
        return False
    del servers[SUTRA_SERVER_NAME]
    _atomic_write(path, config)
    return True


def _load(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        msg = f"Invalid JSON in {path}: {exc.msg} at line {exc.lineno}."
        raise ValueError(msg) from exc
    if not isinstance(data, dict):
        msg = f"Expected {path} to contain a JSON object, got {type(data).__name__}."
        raise ValueError(msg)
    return data


def _atomic_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    body = json.dumps(payload, indent=2) + "\n"
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        os.chmod(tmp, _CONFIG_MODE)
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(body)
        os.replace(tmp, path)
    except Exception:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(tmp)
        raise
