"""Tests for sutra.core.config_example."""

from __future__ import annotations

import tomllib

from sutra.core.config_example import render_example_toml
from sutra.core.settings import SutraSettings


def test_render_includes_header_comment() -> None:
    text = render_example_toml(SutraSettings())
    first_line = text.splitlines()[0]
    assert first_line.startswith("#")
    assert "sutra" in first_line.lower()


def test_render_groups_fields_under_section_headers() -> None:
    text = render_example_toml(SutraSettings())
    assert "[paths]" in text
    assert "[network]" in text


def test_every_leaf_field_appears_commented_out() -> None:
    text = render_example_toml(SutraSettings())
    for key in ("config_home", "data_home", "launchd_label", "falkordb_port", "bolt_port"):
        assert f"# {key} =" in text, f"missing commented entry for {key}"


def test_default_values_are_quoted_or_typed_correctly() -> None:
    text = render_example_toml(SutraSettings())
    assert '# launchd_label = "ai.sutra.falkordb"' in text
    assert "# falkordb_port = 16379" in text
    assert "# bolt_port = 17687" in text


def test_optional_none_fields_render_as_unset_placeholder() -> None:
    text = render_example_toml(SutraSettings())
    assert '"None"' not in text
    assert "# redis_server_binary = <unset>" in text
    assert "# module_path = <unset>" in text
    assert "# data_dir = <unset>" in text


def _activate(text: str) -> str:
    """Mimic a user uncommenting `# k = v` lines, leaving <unset> lines commented."""
    out: list[str] = []
    for line in text.splitlines():
        if line.startswith("# ") and "=" in line and "<unset>" not in line:
            out.append(line[2:])
        else:
            out.append(line)
    return "\n".join(out)


def test_uncommenting_yields_valid_toml_that_parses() -> None:
    text = render_example_toml(SutraSettings())
    parsed = tomllib.loads(_activate(text))
    assert parsed["network"]["falkordb_port"] == 16379
    assert parsed["network"]["bolt_port"] == 17687
    assert parsed["paths"]["launchd_label"] == "ai.sutra.falkordb"


def test_descriptions_emitted_when_field_metadata_present() -> None:
    text = render_example_toml(SutraSettings())
    assert "Redis-protocol port" in text
    assert "Bolt-protocol port" in text


def test_derived_properties_are_excluded() -> None:
    text = render_example_toml(SutraSettings())
    for derived in ("config_toml", "graph_dir", "launchd_plist", "audit_log_dir"):
        assert f"# {derived} =" not in text, f"derived property {derived} leaked into example"
