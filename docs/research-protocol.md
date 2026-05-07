# Research Protocol

Fab defines the research protocol for agent-driven alignment work. External
agent systems execute the work; Fab defines the durable handoffs that let many
ephemeral agents add up to cumulative research.

The core protocol is:

```text
contract
-> workstreams
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

Each workstream should emit enough structure for later agents and humans to
understand what happened:

- claims and uncertainty;
- evidence pointers;
- code, configs, scripts, notebooks, and patches;
- datasets, prompts, evals, model identifiers, and run logs;
- failed attempts and dead ends;
- surprising observations;
- reproduction notes;
- suggested follow-up.

A prose report alone is not enough. The artefact package is the research output.

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
human judgments, papers, and research notes. The local `inwaves/kb` repo is a
useful example of the kind of substrate Fab may need to interoperate with, but
Fab is not itself a general-purpose knowledge base.

Agents should build on prior findings without becoming librarians. They should
use prior context, produce artefact packages, and propose updates. Humans decide
what enters durable understanding.

## Graphs

Research naturally creates graph structure: lineage, dependency, contradiction,
replication, critique, and follow-up. Fab should preserve and project those
relationships.

The graph is not the atomic unit of the system. It is a view over the protocol
objects: contracts, workstreams, artefact packages, briefs, and human judgments.
