# Fab

We are building for a near-future setting, perhaps 6 months out, perhaps 12,
perhaps 18, where agent autonomy is implied. Agents do not stop for interim
feedback and do not need handholding. They do useful work autonomously. Their
contributions are real, in the same way a human researcher's contributions are
real: not necessarily correct, not necessarily useful, but real.

There are hundreds of these agents running in parallel, and later thousands.
They read research briefs, design experiments, run them, and return outputs.
Those outputs come back to humans, who are now the bottleneck to progressing
alignment. There may only be a few hundred human alignment researchers. Assume
they are all working in the same organisation, with access to the same systems,
data, and institutional context.

Fab exists to widen that bottleneck: to let more alignment research
through while keeping the rigour and quality bar high. The bar is high because
errors can be catastrophic. Whatever this system does, it has one goal: help
humans make sense of agent-driven alignment research.

This system is one level up from agent harnessing. It is not about how agents
are executed, what their lifecycle looks like, what platform runs them, or where
they get compute. It is also not a control plane. We do not bank on having to
steer agents into useful work; we mostly assume that they can do useful work.
Later refinements may help encourage diversity and prevent mode collapse, but
Fab does not intervene in individual runs to correct them.

In this framing, the core problem is almost a pure information-flow problem.
There is a research contract. Agents read it, design work, run experiments, and
generate outputs. Those outputs are a data transform over the research
organisation's state of understanding. The ultimate goal is better updating and
eventual consolidation of that understanding.

There are many adjacent literatures we could draw from: agent swarms,
multi-agent systems, high-performance research teams, research management, and
more. We do not need to read all of that to build a good MVP. The MVP should
prove that the information flow is useful to human researchers.

## What Exists Now

This repo currently contains a local, file-backed skeleton for the Fab research
protocol. It does not run agents. It assumes external agent systems execute the
work, while Fab defines the research interface those systems participate in.

The stable protocol shape is:

```text
contract
-> workstreams
-> artefact packages
-> brief
-> human judgment
```

Fab can own the shape of the research programme without owning the execution
platform:

- how a contract becomes a batch of workstreams;
- what agents must emit while working;
- how artefacts, claims, evidence, code, failures, and provenance are packaged;
- how outputs are compared across a batch;
- how human attention is allocated;
- how human judgment feeds back into the next contract or programme state.

The implemented pieces are still modest:

- **Research contracts**: immutable Markdown briefs under
  `.fab/contracts/<contract_id>/vNNN.md`.
- **Workstreams**: stable IDs for lines of work under a contract. Agents are
  ephemeral; the research is not.
- **State packets**: append-only updates emitted by external agents or humans.
- **Live state**: the latest known hypothesis, result, blocker, intended next
  step, flag, and rationale.
- **Artefact and provenance pointers**: structured references to reports, logs,
  plots, code, datasets, prompts, models, and evals.
- **Attention queue**: a mechanical list of workstreams that look blocked,
  flagged, deviated, stale, unscoped, or due for human attention.
- **Pilot fixture**: a simulated batch of black-box agent outputs for testing
  the human inspection workflow.

The current MVP is intentionally modest. It is a substrate for asking whether
the protocol objects are useful enough before building a larger system.

## Knowledge And Graphs

Fab needs access to prior knowledge: previous experiments, results, artefacts,
code, human judgments, and research notes. A knowledge base shaped like
`inwaves/kb` is a useful local example, but Fab is not a general-purpose KB and
does not end at writing notes. The point is to help a researcher consolidate
their view from agent work without turning agents into librarians.

Graph structure is useful, but it is not the atomic unit of Fab. Lineage,
dependency, contradiction, replication, critique, and follow-up all naturally
form graphs. Fab should be able to project those relationships as a graph. The
durable protocol objects remain contracts, workstreams, artefact packages,
briefs, and human judgments.

## What This Is Not

Fab is not currently:

- an agent runner;
- a scheduler;
- a sandbox;
- an experiment platform;
- an inference harness;
- a dashboard for steering individual agents;
- a paper queue;
- a consolidated institutional knowledge base.

Execution stays external. Consolidation and promotion are deferred until the
basic protocol loop is useful.

## Quick Start

This repo is pinned to Python 3.14 via `.python-version` and `pyproject.toml`.

```bash
uv run fab init
uv run fab pilot-fixture
uv run fab attention
uv run fab show ws_003 --brief
```

By default the registry lives in `.fab/` under the current directory.
Pass `--store path/to/store` before the command to use another location.

For an isolated pilot store:

```bash
uv run fab --store /tmp/fab-pilot pilot-fixture
uv run fab --store /tmp/fab-pilot attention
uv run fab --store /tmp/fab-pilot show ws_003 --brief
```

## Common Commands

```bash
uv run fab init
uv run fab pilot-fixture
uv run fab create --title "..." --program "..." --owner "..."
uv run fab list
uv run fab attention
uv run fab show ws_001
uv run fab show ws_001 --brief
uv run fab attach-contract ws_001 --contract-id contract_001 --version 1
uv run fab packet ws_001 --source agent-a --changed "..." --next "..." --rationale "..."
uv run fab packet ws_001 --source agent-a --artifact-json '{"kind":"report","path":"runs/ws_001/baseline-report.md"}'
uv run fab judge ws_001 --action replicate --rationale "..."
uv run fab judge ws_001 --action escalate --rationale "..." --next-attention-due-at 2026-05-10
uv run fab link ws_001 ws_002 --relationship related
```

`attach-contract` expects an existing Markdown contract version, e.g.
`.fab/contracts/contract_001/v001.md`, and locks it read-only. See
[Research contracts](docs/contracts.md).

## Repository Map

- [Roadmap](docs/roadmap.md)
- [Research contracts](docs/contracts.md)
- [Research protocol](docs/research-protocol.md)
- [Brief and human judgment](docs/brief-and-judgment.md)
- [Artefact and provenance pointers](docs/artifacts.md)
- [Pilot fixture](docs/pilot-fixture.md)
- [Strategic context](docs/research/strategic-context.md)
- [KB source map](docs/research/kb-source-map.md)

## Test

```bash
uv run python -m unittest discover -s tests
```

## Next Build

The next build target is the Research Protocol MVP: represent a workstream batch
plan, accept richer artefact packages, produce a batch brief, and record human
judgment in a way that can feed the next contract version.
