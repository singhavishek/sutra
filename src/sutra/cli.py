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

from sutra import __version__

app = typer.Typer(
    name="sutra",
    help="Personal knowledge graph for code and engineering memory.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)
console = Console()


@app.callback()
def _root(
    ctx: typer.Context,
    version: bool = typer.Option(
        False, "--version", "-V", help="Show version and exit."
    ),
) -> None:
    if version:
        console.print(f"sutra {__version__}")
        raise typer.Exit(0)


@app.command()
def init() -> None:
    """Initialize sutra on this machine (directories, launchd, MCP registration)."""
    raise NotImplementedError("Phase 0: implement in src/sutra/cli_commands/init.py")


@app.command()
def register(
    path: str = typer.Argument(..., help="Path to register as a sutra project."),
    scope: str = typer.Option(
        ..., "--scope", help="Scope: work | personal | client:<name>"
    ),
    kind: str = typer.Option(
        "code", "--kind", help="Project kind: code | memory-only | hybrid"
    ),
    no_hooks: bool = typer.Option(
        False, "--no-hooks", help="Skip installing git hooks (git repos only)."
    ),
    watch: bool = typer.Option(
        False, "--watch", help="Enable always-on watcher for this project."
    ),
) -> None:
    """Register a directory as a sutra project (explicit, git or non-git)."""
    raise NotImplementedError(
        "Phase 0: implement in src/sutra/cli_commands/register.py"
    )


if __name__ == "__main__":
    app()
