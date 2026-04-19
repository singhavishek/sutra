"""sutra CLI entry point.

Phase 0 scope: `init`, `register`, `list`, `status`, `reindex`, `serve-mcp`,
`falkordb-serve`, `migrate`. Subcommands live in `sutra.cli_commands.*`.

Tool routing:
    sutra                   → this app
    sutra serve-mcp         → MCP server (stdio transport)
    sutra falkordb-serve    → FalkorDB supervised process (launchd child)
"""

from __future__ import annotations

import typer
from rich.console import Console
from rich.markup import escape

from sutra import __version__
from sutra.cli_commands.init import run as _run_init
from sutra.cli_commands.serve import FalkorDBSetupError
from sutra.cli_commands.serve import run as _run_serve
from sutra.core.settings import SutraSettings

app = typer.Typer(
    name="sutra",
    help="Personal knowledge graph for code and engineering memory.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)
console = Console()


@app.callback(invoke_without_command=True)
def _root(
    ctx: typer.Context,
    version: bool = typer.Option(False, "--version", "-V", help="Show version and exit."),
) -> None:
    if version:
        console.print(f"sutra {__version__}")
        raise typer.Exit(0)


@app.command()
def init() -> None:
    """Initialize sutra on this machine (directories, launchd, MCP registration)."""
    result = _run_init()
    for directory in result.created_dirs:
        console.print(f"[green]\u2713[/] Created {escape(str(directory))}")
    for directory in result.existing_dirs:
        console.print(f"[dim]\u2022[/] Exists  {escape(str(directory))}")
    verb = "Wrote" if result.plist_was_new else "Updated"
    console.print(f"[green]\u2713[/] {verb} launchd plist {escape(str(result.plist_path))}")
    if result.launchd_skipped:
        console.print("[dim]\u2022[/] launchctl load skipped (non-Darwin)")
    else:
        console.print(f"[green]\u2713[/] launchctl {result.launchd_action}")
    if result.mcp_was_already_registered:
        console.print("[dim]\u2022[/] Claude Code MCP already registered")
    else:
        console.print("[green]\u2713[/] Registered sutra with Claude Code MCP")
    console.print(
        f"[green]\u2713[/] Wrote config example {escape(str(result.config_example_path))}"
    )
    console.print("\n[bold]sutra initialized.[/]")


@app.command(name="falkordb-serve")
def falkordb_serve() -> None:
    """Exec FalkorDB in the foreground (launchd-supervised in production)."""
    try:
        _run_serve(SutraSettings())
    except FalkorDBSetupError as exc:
        console.print(f"[red]\u2717[/] {escape(str(exc))}")
        raise typer.Exit(1) from exc


@app.command()
def register(
    path: str = typer.Argument(..., help="Path to register as a sutra project."),
    scope: str = typer.Option(..., "--scope", help="Scope: work | personal | client:<name>"),
    kind: str = typer.Option("code", "--kind", help="Project kind: code | memory-only | hybrid"),
    no_hooks: bool = typer.Option(
        False, "--no-hooks", help="Skip installing git hooks (git repos only)."
    ),
    watch: bool = typer.Option(False, "--watch", help="Enable always-on watcher for this project."),
) -> None:
    """Register a directory as a sutra project (explicit, git or non-git)."""
    raise NotImplementedError("Phase 0: implement in src/sutra/cli_commands/register.py")


if __name__ == "__main__":
    app()
