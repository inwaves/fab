# Fab

Fab is a "factory" for making sense of AI safety research done by agents. It aims to solve the information flow problem that occurs when there are thousands of agents running in parallel, and far fewer human researchers who can review their work.

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
-> remote ingest
-> artefact packages
-> brief
-> human judgment
```

Fab can own the research protocol without owning the execution platform:

- which contract a workstream is answering;
- what agents must emit while working;
- how artefacts, claims, evidence, code, limitations, and used references are packaged;
- how outputs are summarized for human review;
- how completed remote-agent bundles are ingested;
- how human attention is allocated;
- how human judgment feeds back into the next contract or programme state.

The implemented pieces are still modest:

- **Research contracts**: immutable Markdown briefs under
  `.fab/contracts/<contract_id>/vNNN.md`.
- **Workstreams**: stable IDs for lines of work under a contract. Agents are
  ephemeral; the research is not.
- **State packets**: append-only updates emitted by external agents or humans.
- **Live state**: the latest known hypothesis, result, blocker, intended next
  step, and rationale.
- **Remote ingest boundary**: `ingest-run` accepts completed local bundles from
  execution systems without requiring agents to clone Fab.
- **Alexandria ingester service**: a thin service under `services/` scans
  Alexandria for completed bundles, calls Fab's ingest boundary, and records an
  append-only ingest ledger.
- **Artefact packages**: one bundle per run containing the report, code,
  results, logs, claims, evidence, limitations, and suggested follow-up.
- **Brief**: a compact human-facing view over workstreams, attention reasons,
  artifacts, claims, deterministic contract review, judgments, and context that
  is safe or unsafe to carry forward.
- **Human judgments**: append-only rationale records that can target a
  workstream, artifact, or claim.
- **Attention queue**: a mechanical list of workstreams that look blocked,
  stale, limited, unscoped, or due for human attention.
- **Knowledge substrate interface**: explicit `alexandria://` references can be
  resolved, checked, and compared with agent-reported `used_refs`.
- **Pilot fixture**: a simulated batch of black-box agent outputs for testing
  the human inspection workflow.

The current MVP is intentionally modest. It is a substrate for asking whether
the protocol objects are useful enough before building a larger system.

## Knowledge And Graphs

Fab needs access to prior knowledge: previous experiments, results, artefacts,
code, human judgments, and research notes. `inwaves/Alexandria` is the public
MVP substrate: agents can commit artifact bundles there, humans can keep notes
there, and Fab can read from it or later write transformed findings back to it.
Alexandria has the same practical qualities we want from the research substrate,
but is the public boundary for Fab. Contracts remain natural-language first. The
point is to help a researcher consolidate their view from agent work without
turning agents into librarians.

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
- a consolidated institutional knowledge substrate.

Execution stays external. Consolidation and promotion are deferred until the
basic protocol loop is useful.

Agents do not need Fab itself. In the intended remote-execution design, an
agent receives a contract, workstream context, an execution platform, and an
output manifest schema. It writes a completed run bundle to a local or
Alexandria-backed inbox. Fab ingests that bundle and records packet metadata,
artifact bundle pointers, claims, evidence, limitations, and used references.

## Quick Start

This repo is pinned to Python 3.14 via `.python-version` and `pyproject.toml`.

```bash
uv run fab init
uv run fab pilot-fixture
uv run fab attention
uv run fab brief --program safety-finetuning-pilot
uv run fab show ws_003 --brief
```

By default the registry lives in `.fab/` under the current directory.
Pass `--store path/to/store` before the command to use another location.

For an isolated pilot store:

```bash
uv run fab --store /tmp/fab-pilot pilot-fixture
uv run fab --store /tmp/fab-pilot attention
uv run fab --store /tmp/fab-pilot brief --program safety-finetuning-pilot
uv run fab --store /tmp/fab-pilot show ws_003 --brief
```

## Common Commands

```bash
uv run fab init
uv run fab pilot-fixture
uv run fab create --title "..." --program "..." --owner "..."
uv run fab list
uv run fab attention
uv run fab brief
uv run fab brief --program safety-finetuning-pilot
uv run fab show ws_001
uv run fab show ws_001 --brief
uv run fab attach-contract ws_001 --contract-id contract_001 --version 1
uv run fab packet ws_001 --source agent-a --changed "..." --next "..." --rationale "..."
uv run fab packet ws_001 --source agent-a --artifact runs/ws_001/baseline-report.md
uv run fab ingest-run --from ../alexandria/artifacts/program/ws_001/run-abc123
uv run python -m services.alexandria_ingester --alexandria ../alexandria --store .fab
uv run fab sources add alexandria ../alexandria --uri-prefix alexandria://
uv run fab refs check --contract-id contract_pilot_a3_false_positive --version 1
uv run fab judge ws_001 --action replicate --rationale "..."
uv run fab judge ws_001 --target-type claim --target-id art_001/claim_001 --action needs-replication --rationale "..."
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
- [Remote execution and ingest](docs/remote-ingest.md)
- [Alexandria ingester service](docs/alexandria-ingester.md)
- [Knowledge substrate interface](docs/knowledge-substrate.md)
- [Brief and human judgment](docs/brief-and-judgment.md)
- [Artefact packages](docs/artifacts.md)
- [Pilot fixture](docs/pilot-fixture.md)
- [Strategic context](docs/research/strategic-context.md)
- [Alexandria source map](docs/research/alexandria-source-map.md)

## Test

Install the dev extra (adds pytest) into an editable environment, then run the
suite with either runner:

```bash
uv pip install -e ".[dev]"
pytest
```

Or, without a manual install step:

```bash
uv run --extra dev pytest
uv run python -m unittest discover -s tests
```

The `[tool.pytest.ini_options]` config and the root `conftest.py` put `src/`
(the `fab` package) and the repo root (the `services` sidecar) on the path, so
collection works whether or not the project is installed.

If the sibling Alexandria checkout is present, the test suite also ingests the
durable smoke fixture at
`../alexandria/artifacts/safety-finetuning-pilot/ws_001/fab-ingest-smoke-001/`.
Set `FAB_ALEXANDRIA_REPO=/path/to/alexandria` to point the integration test at
another checkout.

## MVP Status

The MVP protocol loop is present: contracts, workstreams, remote ingest,
artifact packages, deterministic contract review, human judgment, and explicit
Alexandria reference checks. The next useful work is dogfooding the loop on real
contracts and tightening what breaks.
