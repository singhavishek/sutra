"""Tests for sutra.core.launchd.bootstrap (launchctl integration)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from sutra.core import launchd
from sutra.core.settings import SutraSettings

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path


@pytest.fixture
def fake_uid(monkeypatch: pytest.MonkeyPatch) -> int:
    monkeypatch.setattr(launchd.os, "getuid", lambda: 501, raising=False)
    return 501


@pytest.fixture
def captured_subprocess(
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[list[tuple[list[str], int]]]:
    """Records subprocess calls. Each entry: (argv, returncode_to_yield)."""
    calls: list[tuple[list[str], int]] = []
    queue: list[int] = []

    def fake_run(
        argv: list[str], *, check: bool = False, capture_output: bool = True, **_: object
    ) -> object:
        rc = queue.pop(0) if queue else 0
        calls.append((list(argv), rc))

        class _Result:
            returncode = rc
            stdout = b""
            stderr = b""

        return _Result()

    monkeypatch.setattr(launchd.subprocess, "run", fake_run)
    return calls


def _settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> SutraSettings:
    monkeypatch.setenv("SUTRA_PATHS__LAUNCH_AGENTS_DIR", str(tmp_path / "launchagents"))
    monkeypatch.setenv("SUTRA_CONFIG_TOML", str(tmp_path / "missing.toml"))
    monkeypatch.delenv("SUTRA_PATHS__LAUNCHD_LABEL", raising=False)
    monkeypatch.setattr(launchd.sys, "platform", "darwin")
    settings = SutraSettings()
    launchd.write_plist(settings)
    return settings


def test_bootstrap_skips_when_not_darwin(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(launchd.sys, "platform", "linux")
    settings = SutraSettings()
    result = launchd.bootstrap(settings)
    assert result.skipped is True
    assert result.action == "skipped-non-darwin"


def test_bootstrap_loads_plist_when_not_yet_loaded(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    captured_subprocess: list[tuple[list[str], int]],
    fake_uid: int,
) -> None:
    settings = _settings(tmp_path, monkeypatch)
    # 1st call: list (rc=113 = "not loaded"), 2nd: bootstrap (rc=0)
    captured_subprocess.extend([])  # ensure fixture
    monkeypatch.setattr(launchd, "_is_loaded", lambda _settings: False)

    result = launchd.bootstrap(settings)

    assert result.action == "bootstrap"
    assert result.skipped is False
    cmd = captured_subprocess[-1][0]
    assert cmd[0] == "/bin/launchctl"
    assert "bootstrap" in cmd
    assert f"gui/{fake_uid}" in cmd
    assert str(settings.paths.launchd_plist) in cmd


def test_bootstrap_kickstarts_when_already_loaded(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    captured_subprocess: list[tuple[list[str], int]],
    fake_uid: int,
) -> None:
    settings = _settings(tmp_path, monkeypatch)
    monkeypatch.setattr(launchd, "_is_loaded", lambda _settings: True)

    result = launchd.bootstrap(settings)

    assert result.action == "kickstart"
    cmd = captured_subprocess[-1][0]
    assert cmd[0] == "/bin/launchctl"
    assert "kickstart" in cmd
    assert any(arg.startswith(f"gui/{fake_uid}/") for arg in cmd)
    assert any(arg.endswith(settings.paths.launchd_label) for arg in cmd)


def test_bootstrap_raises_when_launchctl_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    captured_subprocess: list[tuple[list[str], int]],
    fake_uid: int,
) -> None:
    settings = _settings(tmp_path, monkeypatch)
    monkeypatch.setattr(launchd, "_is_loaded", lambda _settings: False)

    def failing_run(
        argv: list[str], *, check: bool = False, capture_output: bool = True, **_: object
    ) -> object:
        captured_subprocess.append((list(argv), 5))

        class _Result:
            returncode = 5
            stdout = b""
            stderr = b"boom"

        return _Result()

    monkeypatch.setattr(launchd.subprocess, "run", failing_run)

    with pytest.raises(launchd.LaunchctlError, match="bootstrap"):
        launchd.bootstrap(settings)


def test_is_loaded_parses_launchctl_print_output(
    monkeypatch: pytest.MonkeyPatch,
    fake_uid: int,
) -> None:
    monkeypatch.setattr(launchd.sys, "platform", "darwin")

    def fake_run(
        argv: list[str], *, check: bool = False, capture_output: bool = True, **_: object
    ) -> object:
        class _Result:
            returncode = 0
            stdout = b"some output"
            stderr = b""

        return _Result()

    monkeypatch.setattr(launchd.subprocess, "run", fake_run)
    settings = SutraSettings()
    assert launchd._is_loaded(settings) is True


def test_is_loaded_returns_false_on_print_failure(
    monkeypatch: pytest.MonkeyPatch,
    fake_uid: int,
) -> None:
    monkeypatch.setattr(launchd.sys, "platform", "darwin")

    def fake_run(
        argv: list[str], *, check: bool = False, capture_output: bool = True, **_: object
    ) -> object:
        class _Result:
            returncode = 113
            stdout = b""
            stderr = b"Could not find service"

        return _Result()

    monkeypatch.setattr(launchd.subprocess, "run", fake_run)
    settings = SutraSettings()
    assert launchd._is_loaded(settings) is False
