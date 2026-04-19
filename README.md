# sutra

**A thread (सूत्र) connecting your code, decisions, and sessions into a graph that Claude Code can query.**

Personal knowledge graph for code and engineering memory. Remembers what you worked on, what changed, and what worked. 100% local, zero monthly cost.

> **Status:** Pre-alpha. Scaffolded 2026-04-18, no implementation yet.

## What sutra does

Developers don't just write code. You make decisions, write runbooks, track tech debt, remember which approaches failed, and carry tribal knowledge across projects. Only about 40% of the work lives in the repo. The rest lives in your head.

Sutra is a graph-backed memory layer for the 60%.

- **Code graph** — every function, class, call, import, inheritance as nodes and edges
- **Memory graph** — decisions, runbooks, tech debt, insights, and sessions as first-class nodes
- **Bridge edges** — `Session-TOUCHED-Symbol`, `Decision-ABOUT-Module`, `Person-OWNS-Community`. This is where the compounding value lives.

Claude Code queries all of it via MCP. Obsidian gives you a comfortable text view of the same data.

## Design principles

1. Explicit registration — nothing is indexed until you say so
2. Strict project isolation — work, personal, and client code stay separate
3. Local-first, zero cloud — no external AI APIs
4. Graph is the spine — files are artifacts the graph points to
5. Hybrid retrieval — BM25 + vector + graph traversal with local reranking
6. Memory-aware from day 1 — session nodes accumulate even before memory tools ship
7. Manual controls always available — every automation has a CLI override

## Stack

| Layer | Choice |
|-------|--------|
| Graph DB | FalkorDB (Apache 2.0, multigraph, GraphBLAS) |
| Vector store | LanceDB (embedded, file-backed HNSW) |
| Metadata | SQLite WAL (audit, telemetry) |
| Parser | tree-sitter (100+ languages) |
| Embeddings | nomic-embed-text-v1.5 via MLX (~500 MB, local) |
| Reranker | BAAI/bge-reranker-v2-m3 Q4 (~300 MB, local) |
| LLM reasoning | Claude Code itself (no external API) |
| Language | Python 3.12+ |

## Cost footprint

- Disk: ~1.2-1.5 GB for 1-2 active projects (includes models)
- Ambient RAM: ~80 MB (FalkorDB only, when not in session)
- Active RAM: ~400-600 MB during Claude sessions
- Monthly cost: $0

## Installation

Phase 0 HEAD-only install. A tagged release will follow once the first Phase 0 slice stabilises.

```bash
brew tap singhavishek/sutra
brew install --HEAD sutra
```

The formula installs the `sutra` CLI plus `redis` (sutra invokes `redis-server` to supervise FalkorDB). The FalkorDB Redis module (`falkordb.so`) is not in homebrew-core; install it via the FalkorDB tap:

```bash
brew tap falkordb/falkordb
brew install falkordb
```

Then initialise sutra on the machine:

```bash
sutra init                                   # create dirs, load launchd plist, register MCP
sutra register ~/Work/your-project --scope work   # Phase 0 deliverable #2 (not yet shipped)
```

Tap source: [singhavishek/homebrew-sutra](https://github.com/singhavishek/homebrew-sutra).

## Development

```bash
# Clone and enter
git clone git@github.com:singhavishek/sutra.git
cd sutra

# Install dependencies (Python 3.12+ required)
uv sync --extra dev --extra mlx

# Install pre-commit hooks
uv run pre-commit install

# Run checks
uv run ruff check
uv run mypy src/
uv run pytest
```

## License

Apache 2.0. See `LICENSE`.

## Contributing

Pre-alpha. Open an issue to start a conversation.
