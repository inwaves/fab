# Alignment Fab

MVP tooling for supervising many parallel automated alignment-research workstreams.

The first component is a file-backed workstream registry. It keeps stable workstream identity separate from the research contract and from the live state produced by ongoing updates.

## Quick Start

This repo is pinned to Python 3.14 via `.python-version` and `pyproject.toml`.

```bash
uv run alignment-fab init
uv run alignment-fab create --title "A3 false-positive reduction" --program safety-finetuning --owner human
uv run alignment-fab list
uv run alignment-fab packet ws_001 --source agent-a --changed "Ran baseline eval" --next "Try narrower data filter" --continue-reason "Baseline exposes a measurable false-positive cluster"
uv run alignment-fab show ws_001
```

By default the registry lives in `.alignment-fab/` under the current directory. Pass `--store path/to/store` before the command to use another location.

## Current Scope

Alignment Fab is currently the registry MVP only. It does not run agents, schedule jobs, or define research contracts yet. It gives workstreams stable handles and keeps ongoing state separate from the contract/spec side.

## Project Context

The roadmap and research notes from the old KB workspace are now copied into this repo:

- [Roadmap](docs/roadmap.md)
- [Alignment Factory research note](docs/research/alignment-factory.md)
- [Strategic context](docs/research/strategic-context.md)
- [KB source map](docs/research/kb-source-map.md)

## Registry Model

- **Workstream registry entry**: stable identity, owner, parent program, status, relationships, visibility, and pointers.
- **Research contract pointer**: the current contract id/version. Contract authoring comes next.
- **Live state**: current hypothesis, plan, blockers, next action, and reason for continuing.
- **State packets**: append-only updates from agents or humans.
- **Decision log**: append-only human steering decisions.

## Commands

```bash
uv run alignment-fab init
uv run alignment-fab create --title "..." --program "..." --owner "..."
uv run alignment-fab list
uv run alignment-fab show ws_001
uv run alignment-fab attach-contract ws_001 --contract-id contract_001 --version 1
uv run alignment-fab packet ws_001 --source agent-a --changed "..." --next "..." --continue-reason "..."
uv run alignment-fab decide ws_001 --action continue --rationale "..."
uv run alignment-fab link ws_001 ws_002 --relationship related
```

## Test

```bash
uv run python -m unittest discover -s tests
```

## Next Build

The next component should be the research contract object and editor. The registry already has a contract pointer; the contract tool should define the human-approved rules for a workstream before agent work begins.
