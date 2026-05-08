# Research Protocol

Fab defines the research protocol for agent-driven alignment work. External
agent systems execute the work; Fab defines the durable handoffs that let many
ephemeral agents add up to cumulative research.

The core protocol is:

```text
contract
-> workstreams
-> remote ingest
-> artefact packages
-> brief
-> human judgment
```

This is the middle layer between a human research question and external agent
execution. It is not a platform, scheduler, sandbox, or harness.

## Contract To Workstreams

A contract states what the human wants investigated and why it matters. Fab
then represents the resulting lines of work as workstreams.

Later Fab may need a better answer for workstream fan-out and programme shape:

- exploration width;
- desired mix of exploratory, replication, critique, validation, and extension
  workstreams;
- prior knowledge and artefacts the batch should start from;
- areas that should remain independent to preserve diverse evidence;
- outputs that should be comparable across workstreams.

That is deliberately not part of the current MVP skeleton. First Fab needs the
local loop to work: contract, emitted artefacts, brief, and human judgment.

## Workstreams To Artefact Packages

Agents are temporary. Workstreams and artefacts are durable.

Agents do not need the Fab repo in order to participate in the protocol. The
normal path should be that an execution platform gives an agent the contract,
workstream context, tools, and output schema. The agent returns a completed run
bundle with a manifest and artifacts. Fab ingests that bundle and registers the
packet.

Each workstream should emit enough structure for later agents and humans to
understand what happened:

- a short summary;
- claims;
- evidence;
- code when code produced the result;
- results and logs;
- limitations;
- suggested follow-up;
- references the agent actually used.

A prose report alone is not enough. The artefact package is the research output.

## Remote Ingest

The execution boundary is:

```text
agent / execution platform
-> run bundle in Alexandria or another inbox
-> Fab ingest adapter
-> state packet and live-state update
```

The Maestro branch proved the loop by letting an agent clone Fab and call
`fab packet` directly. That is a useful test path, but not the intended
architecture. In production, agents should write a Fab-compatible manifest and
one artifact bundle somewhere durable. For the MVP, that durable substrate is
the public `inwaves/Alexandria` repo. A small ingester service should watch or
ingest completed bundles from there and then call Fab's ingest boundary.

The current implementation is an explicit command:
`fab ingest-run --from <bundle>`. A later ingester can monitor Alexandria
commits, object-store inboxes, shared directories, or execution-platform APIs.
It should reuse the same validation path rather than becoming a second
protocol. See
[Remote execution and ingest](remote-ingest.md).

## Artefact Packages To Brief

The current MVP summarizes workstreams, artifacts, claims, attention reasons,
judgments, and next-context buckets. As the brief improves, it should also
surface:

- convergence across independent workstreams;
- contradictions;
- shared assumptions, datasets, prompts, code paths, evals, or scaffolds;
- likely shortcuts or eval leakage;
- missing branches of the research space;
- artefacts that deserve replication or critique;
- results that appear local-only;
- results that may deserve future reuse.

The brief is an attention-allocation surface. It is not the endpoint of the
research.

## Brief To Human Judgment

The human judgment step decides what the researcher makes of the batch:

- trust as local evidence;
- reject;
- mark as interesting but unsupported;
- request replication;
- request critique;
- escalate to human/manual review;
- prevent propagation;
- allow as context for a later contract;
- mark as a candidate for later promotion.

This judgment feeds the next contract version, future workstreams, or programme
state. It is not primarily a command to an agent. The agents that produced the
work may already be gone.

## Knowledge Substrate

Fab needs access to prior knowledge: previous experiments, artefacts, code,
human judgments, papers, and research notes. The public MVP substrate is
`inwaves/Alexandria`: raw agent artifacts, Fab-transformed findings, and human
notes can coexist there. The
contract remains natural-language first. Fab resolves explicit references when
they are present, records resolution snapshots, records what references an agent
actually used, and leaves write-back under human judgment.

Agents should build on prior findings without becoming librarians. They should
use prior context and produce artefact packages. Humans decide what enters
durable understanding.

See [Knowledge substrate interface](knowledge-substrate.md).

## Graphs

Research naturally creates graph structure: lineage, dependency, contradiction,
replication, critique, and follow-up. Fab should preserve and project those
relationships.

The graph is not the atomic unit of the system. It is a view over the protocol
objects: contracts, workstreams, artefact packages, briefs, and human judgments.
