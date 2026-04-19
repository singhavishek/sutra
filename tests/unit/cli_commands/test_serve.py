"""Tests for sutra.cli_commands.serve (the falkordb-serve subcommand)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from sutra.cli_commands import serve
from sutra.core.settings import FalkorDBSettings, NetworkSettings, PathsSettings, SutraSettings

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path


# --- fixtures ---------------------------------------------------------------


def _settings(tmp_path: Path, **overrides: object) -> SutraSettings:
    paths = PathsSettings(data_home=tmp_path / "data")
    network = NetworkSettings(falkordb_port=16379, bolt_port=17687)
    falkordb = FalkorDBSettings(**overrides)  # type: ignore[arg-type]
    return SutraSettings(paths=paths, network=network, falkordb=falkordb)


@pytest.fixture
def fake_redis(tmp_path: Path) -> Path:
    binary = tmp_path / "bin" / "redis-server"
    binary.parent.mkdir(parents=True, exist_ok=True)
    binary.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    binary.chmod(0o755)
    return binary


@pytest.fixture
def fake_module(tmp_path: Path) -> Path:
    module = tmp_path / "lib" / "falkordb.so"
    module.parent.mkdir(parents=True, exist_ok=True)
    module.write_bytes(b"\x7fELF")
    return module


@pytest.fixture
def captured_exec(monkeypatch: pytest.MonkeyPatch) -> Iterator[list[tuple[str, list[str]]]]:
    calls: list[tuple[str, list[str]]] = []

    def fake_execvp(file: str, args: list[str]) -> None:
        calls.append((file, list(args)))
        raise SystemExit(0)

    monkeypatch.setattr(serve.os, "execvp", fake_execvp)
    return calls


# --- discovery -------------------------------------------------------------


def test_discover_redis_server_returns_explicit_setting(tmp_path: Path, fake_redis: Path) -> None:
    settings = _settings(tmp_path, redis_server_binary=fake_redis)
    assert serve.discover_redis_server(settings) == fake_redis


def test_discover_redis_server_falls_back_to_path(
    tmp_path: Path, fake_redis: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = _settings(tmp_path)
    monkeypatch.setattr(serve.shutil, "which", lambda _name: str(fake_redis))
    assert serve.discover_redis_server(settings) == fake_redis


def test_discover_redis_server_raises_when_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = _settings(tmp_path)
    monkeypatch.setattr(serve.shutil, "which", lambda _name: None)
    with pytest.raises(serve.FalkorDBSetupError, match="redis-server"):
        serve.discover_redis_server(settings)


def test_discover_module_returns_explicit_setting(tmp_path: Path, fake_module: Path) -> None:
    settings = _settings(tmp_path, module_path=fake_module)
    assert serve.discover_module(settings) == fake_module


def test_discover_module_scans_standard_locations(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    candidate = tmp_path / "homebrew" / "lib" / "falkordb.so"
    candidate.parent.mkdir(parents=True, exist_ok=True)
    candidate.write_bytes(b"\x7fELF")

    settings = _settings(tmp_path)
    monkeypatch.setattr(serve, "_DEFAULT_MODULE_LOCATIONS", (candidate,))
    assert serve.discover_module(settings) == candidate


def test_discover_module_raises_with_install_hint_when_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = _settings(tmp_path)
    monkeypatch.setattr(serve, "_DEFAULT_MODULE_LOCATIONS", ())
    with pytest.raises(serve.FalkorDBSetupError, match="falkordb"):
        serve.discover_module(settings)


def test_discover_module_skips_explicit_setting_when_file_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bogus = tmp_path / "missing.so"
    settings = _settings(tmp_path, module_path=bogus)
    monkeypatch.setattr(serve, "_DEFAULT_MODULE_LOCATIONS", ())
    with pytest.raises(serve.FalkorDBSetupError, match=str(bogus)):
        serve.discover_module(settings)


# --- argv assembly ----------------------------------------------------------


def test_build_args_includes_port_and_bolt_and_dir_and_module(
    tmp_path: Path, fake_redis: Path, fake_module: Path
) -> None:
    settings = _settings(tmp_path)
    args = serve.build_args(settings, fake_redis, fake_module)
    assert args[0] == str(fake_redis)
    assert "--port" in args
    assert args[args.index("--port") + 1] == "16379"
    assert "--dir" in args
    assert args[args.index("--dir") + 1] == str(settings.paths.graph_dir)
    assert "--loadmodule" in args
    load_idx = args.index("--loadmodule")
    assert args[load_idx + 1] == str(fake_module)
    assert "BOLT_PORT" in args[load_idx + 2 :]
    assert "17687" in args


def test_build_args_uses_falkordb_data_dir_override(
    tmp_path: Path, fake_redis: Path, fake_module: Path
) -> None:
    custom = tmp_path / "custom-rdb"
    settings = _settings(tmp_path, data_dir=custom)
    args = serve.build_args(settings, fake_redis, fake_module)
    assert args[args.index("--dir") + 1] == str(custom)


def test_build_args_disables_protected_mode(
    tmp_path: Path, fake_redis: Path, fake_module: Path
) -> None:
    """Loopback-only deployment, but we set --bind 127.0.0.1 explicitly anyway."""
    settings = _settings(tmp_path)
    args = serve.build_args(settings, fake_redis, fake_module)
    assert "--bind" in args
    assert args[args.index("--bind") + 1] == "127.0.0.1"


# --- run ---------------------------------------------------------------------


def test_run_creates_data_dir_before_exec(
    tmp_path: Path,
    fake_redis: Path,
    fake_module: Path,
    captured_exec: list[tuple[str, list[str]]],
) -> None:
    settings = _settings(tmp_path, redis_server_binary=fake_redis, module_path=fake_module)
    assert not settings.paths.graph_dir.exists()

    with pytest.raises(SystemExit) as exc:
        serve.run(settings)
    assert exc.value.code == 0

    assert settings.paths.graph_dir.is_dir()
    assert captured_exec, "execvp should have been called"


def test_run_execs_redis_with_built_args(
    tmp_path: Path,
    fake_redis: Path,
    fake_module: Path,
    captured_exec: list[tuple[str, list[str]]],
) -> None:
    settings = _settings(tmp_path, redis_server_binary=fake_redis, module_path=fake_module)
    with pytest.raises(SystemExit):
        serve.run(settings)

    file, args = captured_exec[0]
    assert file == str(fake_redis)
    assert args == serve.build_args(settings, fake_redis, fake_module)
