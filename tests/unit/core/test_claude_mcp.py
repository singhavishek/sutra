"""Tests for sutra.core.claude_mcp."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from sutra.core.claude_mcp import (
    DEFAULT_ARGS,
    DEFAULT_COMMAND,
    SUTRA_SERVER_NAME,
    is_registered,
    register,
    unregister,
)
from sutra.core.paths import SutraPaths

if TYPE_CHECKING:
    from pathlib import Path


def _paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> SutraPaths:
    monkeypatch.setenv("SUTRA_CLAUDE_MCP_CONFIG_PATH", str(tmp_path / ".claude.json"))
    return SutraPaths()


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))  # type: ignore[no-any-return]


def test_is_registered_false_when_file_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths = _paths(tmp_path, monkeypatch)
    assert paths.claude_mcp_config_path.exists() is False
    assert is_registered(paths) is False


def test_is_registered_false_when_no_mcp_servers_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths = _paths(tmp_path, monkeypatch)
    _write_json(paths.claude_mcp_config_path, {"projects": {}})
    assert is_registered(paths) is False


def test_is_registered_false_when_sutra_absent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths = _paths(tmp_path, monkeypatch)
    _write_json(
        paths.claude_mcp_config_path,
        {"mcpServers": {"other": {"command": "x", "args": []}}},
    )
    assert is_registered(paths) is False


def test_is_registered_true_when_sutra_present(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths = _paths(tmp_path, monkeypatch)
    _write_json(
        paths.claude_mcp_config_path,
        {"mcpServers": {SUTRA_SERVER_NAME: {"command": "sutra", "args": ["serve-mcp"]}}},
    )
    assert is_registered(paths) is True


def test_register_creates_missing_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    paths = _paths(tmp_path, monkeypatch)
    assert not paths.claude_mcp_config_path.exists()

    register(paths)

    config = _read_json(paths.claude_mcp_config_path)
    entry = config["mcpServers"][SUTRA_SERVER_NAME]  # type: ignore[index]
    assert entry == {"command": DEFAULT_COMMAND, "args": list(DEFAULT_ARGS)}


def test_register_adds_sutra_without_touching_other_servers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths = _paths(tmp_path, monkeypatch)
    _write_json(
        paths.claude_mcp_config_path,
        {"mcpServers": {"serena": {"command": "serena", "args": ["mcp"]}}},
    )

    register(paths)

    config = _read_json(paths.claude_mcp_config_path)
    servers = config["mcpServers"]
    assert set(servers) == {"serena", SUTRA_SERVER_NAME}  # type: ignore[arg-type]
    assert servers["serena"] == {"command": "serena", "args": ["mcp"]}  # type: ignore[index]


def test_register_preserves_unrelated_top_level_keys(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths = _paths(tmp_path, monkeypatch)
    _write_json(
        paths.claude_mcp_config_path,
        {
            "projects": {"/some/path": {"mcpServers": {"p": {"command": "p"}}}},
            "someOtherKey": 42,
        },
    )

    register(paths)

    config = _read_json(paths.claude_mcp_config_path)
    assert config["projects"] == {"/some/path": {"mcpServers": {"p": {"command": "p"}}}}
    assert config["someOtherKey"] == 42
    assert SUTRA_SERVER_NAME in config["mcpServers"]  # type: ignore[operator]


def test_register_is_idempotent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    paths = _paths(tmp_path, monkeypatch)
    register(paths)
    first = paths.claude_mcp_config_path.read_text(encoding="utf-8")
    register(paths)
    second = paths.claude_mcp_config_path.read_text(encoding="utf-8")
    assert first == second


def test_register_custom_command_and_args(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    paths = _paths(tmp_path, monkeypatch)
    register(paths, command="/opt/homebrew/bin/sutra", args=["serve-mcp", "--verbose"])
    config = _read_json(paths.claude_mcp_config_path)
    entry = config["mcpServers"][SUTRA_SERVER_NAME]  # type: ignore[index]
    assert entry == {
        "command": "/opt/homebrew/bin/sutra",
        "args": ["serve-mcp", "--verbose"],
    }


def test_unregister_returns_true_when_removed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths = _paths(tmp_path, monkeypatch)
    register(paths)
    assert unregister(paths) is True
    config = _read_json(paths.claude_mcp_config_path)
    assert SUTRA_SERVER_NAME not in config["mcpServers"]  # type: ignore[operator]


def test_unregister_returns_false_when_file_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths = _paths(tmp_path, monkeypatch)
    assert unregister(paths) is False


def test_unregister_returns_false_when_sutra_absent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths = _paths(tmp_path, monkeypatch)
    _write_json(
        paths.claude_mcp_config_path,
        {"mcpServers": {"other": {"command": "x"}}},
    )
    assert unregister(paths) is False


def test_unregister_preserves_other_servers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths = _paths(tmp_path, monkeypatch)
    _write_json(
        paths.claude_mcp_config_path,
        {
            "mcpServers": {
                "serena": {"command": "serena"},
                SUTRA_SERVER_NAME: {"command": "sutra", "args": ["serve-mcp"]},
            }
        },
    )

    assert unregister(paths) is True

    config = _read_json(paths.claude_mcp_config_path)
    assert config["mcpServers"] == {"serena": {"command": "serena"}}


def test_register_writes_file_with_mode_0o600(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths = _paths(tmp_path, monkeypatch)
    register(paths)
    assert (paths.claude_mcp_config_path.stat().st_mode & 0o777) == 0o600


def test_invalid_json_raises_value_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    paths = _paths(tmp_path, monkeypatch)
    paths.claude_mcp_config_path.write_text("not-json{", encoding="utf-8")
    with pytest.raises(ValueError, match="Invalid JSON"):
        is_registered(paths)


def test_non_object_root_raises_value_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths = _paths(tmp_path, monkeypatch)
    paths.claude_mcp_config_path.write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError, match="JSON object"):
        is_registered(paths)


def test_non_dict_mcp_servers_raises_on_register(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths = _paths(tmp_path, monkeypatch)
    _write_json(paths.claude_mcp_config_path, {"mcpServers": ["not", "a", "dict"]})
    with pytest.raises(ValueError, match="mcpServers"):
        register(paths)
