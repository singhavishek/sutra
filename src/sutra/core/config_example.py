"""Render `config.example.toml` from the live `SutraSettings` schema.

The example file is regenerated on every `sutra init` run (idempotent overwrite).
It documents every overridable key with its current default and one-line
description. Users copy it to `config.toml` and uncomment what they want to
change. The live `config.toml` is never written by sutra.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

if TYPE_CHECKING:
    from pydantic.fields import FieldInfo

    from sutra.core.settings import SutraSettings

_HEADER = (
    "# sutra configuration example. Copy to config.toml and uncomment to override.\n"
    "# Source precedence (highest wins): env vars > config.toml > coded defaults.\n"
)


def render_example_toml(settings: SutraSettings) -> str:
    """Render a commented TOML example from the live settings schema."""
    sections: list[str] = [_HEADER]
    for section_name, section_field in type(settings).model_fields.items():
        section_value = getattr(settings, section_name)
        if not isinstance(section_value, BaseModel):
            continue
        sections.append(_render_section(section_name, section_value, section_field))
    return "\n".join(sections).rstrip() + "\n"


def _render_section(name: str, model: BaseModel, field_info: FieldInfo) -> str:
    lines: list[str] = []
    if field_info.description:
        lines.append(f"# {field_info.description}")
    lines.append(f"[{name}]")
    for key, info in type(model).model_fields.items():
        value = getattr(model, key)
        comment = f"  # {info.description}" if info.description else ""
        if value is None:
            lines.append(f"# {key} = <unset>{comment}")
        else:
            lines.append(f"# {key} = {_format_value(value)}{comment}")
    return "\n".join(lines) + "\n"


def _format_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, Path):
        return _toml_quote(str(value))
    if isinstance(value, str):
        return _toml_quote(value)
    return _toml_quote(str(value))


def _toml_quote(s: str) -> str:
    escaped = s.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'
