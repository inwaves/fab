# Strategic Context

This is the minimum project context needed to build Fab without reopening the
whole Alexandria-backed research substrate.

## Why Fab Exists

The automated alignment researcher thesis depends on a hard institutional step:
large numbers of AI agents produce alignment work, and a small number of human
researchers still need to decide what is real, fragile, useful, misleading, or
worth pursuing next.

Fab targets that step. It is the protocol layer that turns many agent
contributions into cumulative, reviewable alignment research.

## The Product Shape

The settled protocol is:

```text
contract
-> workstreams
-> remote ingest
-> artefact packages
-> brief
-> human judgment
```

Fab does not own the agent platform. It owns the research interface:

- which contract a workstream is answering;
- what prior knowledge and artefacts agents receive;
- what agents must emit;
- how completed run bundles are ingested from the execution platform;
- how outputs are summarized and, later, compared;
- how human attention is allocated;
- how human judgment feeds the next contract, batch, or programme state.

The agent does not need the Fab repo. The execution platform gives it contract
context and tools; the agent emits a run bundle with a simple manifest and one
artifact bundle containing the report, code, results, logs, claims, evidence,
limitations, and suggested follow-up. For the MVP, that bundle lands in
`inwaves/Alexandria`; Fab validates and registers it.

## Knowledge Substrate

Agents need access to prior experiments, results, artefacts, code, and human
judgments. `inwaves/Alexandria` is the public MVP substrate for that exchange.
Fab should expose source adapters and reference semantics that can work with
Alexandria now and other substrates later.

The important distinction is:

- prior knowledge informs contracts and workstreams;
- agent work produces artefact packages and suggested updates;
- humans decide what changes durable understanding.

Agents should not become librarians. The system should help humans consolidate
their view from agent work.

## Adjacent Work

Recent adjacent work gives useful design pressure:

- Agent-native research artefacts argue that papers are too lossy for agent
  continuation, and that code, traces, evidence, and failed attempts should be
  first-class research outputs.
- Flywheel-like systems show why research often benefits from graph structure:
  lineage, branches, competing hypotheses, replications, and follow-up.

Fab can use those ideas without making the graph the atomic unit. The durable
objects are contracts, workstreams, artefact packages, briefs, and human
judgments. Graphs are views over their relationships.

## Design Warnings

- More agent output does not automatically mean progress.
- Outcome-gradable loops can Goodhart their evals.
- Reports can hide the code and failed attempts needed for replication.
- Agent-generated structure can become busywork.
- Human judgment can become ceremonial if too many low-quality items demand
  attention.
- Local results can become shared assumptions before their scope is understood.

## Alexandria Anchors

Use Alexandria as grounding context when useful. These paths are design anchors
for this workspace, not permanent Fab dependencies:

- `research/alignment-via-ai-assistance.md`
- `research/mitigations-to-automated-alignment/README.md`
- `papers/automated-weak-to-strong-researcher.md`
- `papers/the-last-human-written-paper-agent-native-research-artifacts.md`
- `articles/the-new-age-of-research.md`
