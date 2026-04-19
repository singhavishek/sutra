"""Shared test fixtures.

Test isolation note: `SutraSettings` reads `SUTRA_CONFIG_TOML` from the
environment to locate `~/.sutra/config.toml`. We force this to a guaranteed-
missing per-test path so no test ever picks up the developer's real config
file. Individual tests can still override by calling `monkeypatch.setenv`
before constructing `SutraSettings`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture(autouse=True)
def _isolate_sutra_config_toml(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("SUTRA_CONFIG_TOML", str(tmp_path / "_isolated_missing.toml"))
