# Fab

Fab is a "factory" for running AI safety research using agents. It aims to solve the information flow problem that occurs when there are thousands of agents running in parallel, and far fewer human researchers who can review their work.

## Building the case for fab

- assume a future where agent autonomy and capability is implied; not unlikely if one believes in straight lines on a graph;
- admit hundreds/thousands of agents running in parallel; a good intro is the [AI 2027](https://ai-2027.com/) framing;
- each agent receives some form of task, designs and runs experiments, interprets the outputs, repeating this as many times as it needs to arrive at an artefact;

The resulting artefacts are still evaluated for correctness by human researchers, whose attention and time is scarce. What helps to widen that bottleneck, while keeping the rigour and correctness bars high?

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
