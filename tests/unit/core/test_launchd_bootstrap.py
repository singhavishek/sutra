"""Tests for sutra.core.launchd.bootstrap (launchctl integration)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import pytest

from sutra.core import launchd
from sutra.core.settings import SutraSettings

if TYPE_CHECKING:
    from pathlib import Path


@dataclass
class _LaunchctlStub:
    """Records argvs and yields a queued returncode (or 0) per invocation."""

    calls: list[list[str]] = field(default_factory=list)
    queue: list[int] = field(default_factory=list)

    def seed(self, *returncodes: int) -> None:
        self.queue.extend(returncodes)


@pytest.fixture
def fake_uid(monkeypatch: pytest.MonkeyPatch) -> int:
    monkeypatch.setattr(launchd.os, "getuid", lambda: 501, raising=False)
    return 501


@pytest.fixture
def launchctl(monkeypatch: pytest.MonkeyPatch) -> _LaunchctlStub:
    stub = _LaunchctlStub()

    def fake_run(
        argv: list[str], *, check: bool = False, capture_output: bool = True, **_: object
    ) -> object:
        rc = stub.queue.pop(0) if stub.queue else 0
        stub.calls.append(list(argv))

        class _Result:
            returncode = rc
            stdout = b""
            stderr = b"boom" if rc != 0 else b""

        return _Result()

    monkeypatch.setattr(launchd.subprocess, "run", fake_run)
    return stub


def _settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> SutraSettings:
    monkeypatch.setenv("SUTRA_PATHS__LAUNCH_AGENTS_DIR", str(tmp_path / "launchagents"))
    monkeypatch.delenv("SUTRA_PATHS__LAUNCHD_LABEL", raising=False)
    monkeypatch.setattr(launchd.sys, "platform", "darwin")
    settings = SutraSettings()
    launchd.write_plist(settings)
    return settings


def test_bootstrap_skips_when_not_darwin(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(launchd.sys, "platform", "linux")
    settings = SutraSettings()
    result = launchd.bootstrap(settings)
    assert result.skipped is True
    assert result.action == "skipped-non-darwin"


def test_bootstrap_loads_plist_when_not_yet_loaded(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    launchctl: _LaunchctlStub,
    fake_uid: int,
) -> None:
    settings = _settings(tmp_path, monkeypatch)
    launchctl.seed(113, 0)  # print → not loaded, bootstrap → success

    result = launchd.bootstrap(settings)

    assert result.action == "bootstrap"
    assert result.skipped is False
    assert [c[1] for c in launchctl.calls] == ["print", "bootstrap"]
    bootstrap_cmd = launchctl.calls[1]
    assert bootstrap_cmd[0] == "/bin/launchctl"
    assert f"gui/{fake_uid}" in bootstrap_cmd
    assert str(settings.paths.launchd_plist) in bootstrap_cmd


def test_bootstrap_kickstarts_when_already_loaded(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    launchctl: _LaunchctlStub,
    fake_uid: int,
) -> None:
    settings = _settings(tmp_path, monkeypatch)
    launchctl.seed(0, 0)  # print → loaded, kickstart → success

    result = launchd.bootstrap(settings)

    assert result.action == "kickstart"
    assert [c[1] for c in launchctl.calls] == ["print", "kickstart"]
    kick_cmd = launchctl.calls[1]
    assert kick_cmd[0] == "/bin/launchctl"
    assert any(arg.startswith(f"gui/{fake_uid}/") for arg in kick_cmd)
    assert any(arg.endswith(settings.paths.launchd_label) for arg in kick_cmd)


def test_bootstrap_raises_when_launchctl_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    launchctl: _LaunchctlStub,
    fake_uid: int,
) -> None:
    settings = _settings(tmp_path, monkeypatch)
    launchctl.seed(113, 5)  # print → not loaded, bootstrap → failure

    with pytest.raises(launchd.LaunchctlError, match="bootstrap"):
        launchd.bootstrap(settings)


def test_is_loaded_returns_true_when_launchctl_print_succeeds(
    monkeypatch: pytest.MonkeyPatch,
    launchctl: _LaunchctlStub,
    fake_uid: int,
) -> None:
    monkeypatch.setattr(launchd.sys, "platform", "darwin")
    launchctl.seed(0)
    settings = SutraSettings()
    assert launchd._is_loaded(settings) is True


def test_is_loaded_returns_false_when_launchctl_print_fails(
    monkeypatch: pytest.MonkeyPatch,
    launchctl: _LaunchctlStub,
    fake_uid: int,
) -> None:
    monkeypatch.setattr(launchd.sys, "platform", "darwin")
    launchctl.seed(113)
    settings = SutraSettings()
    assert launchd._is_loaded(settings) is False
