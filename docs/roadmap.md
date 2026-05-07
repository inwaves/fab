# Alignment Fab Roadmap

This roadmap merges the current repository state with the project research note
that lived in `kb/research/alignment-factory/README.md`. The repo currently
contains the registry MVP; the research note supplies the larger product shape.

## Current State

Alignment Fab is a local, file-backed control layer for human-supervised
automated alignment research. The current code implements only the workstream
registry and live-state loop:

- stable workstream records under `.alignment-fab/workstreams/`;
- separate live-state records under `.alignment-fab/live-state/`;
- append-only state packets under `.alignment-fab/state-packets/`;
- append-only human decisions under `.alignment-fab/decisions/`;
- contract pointers on workstreams, but no contract object or editor yet.

The useful invariant is separation of concerns:

- the registry says what the workstream is;
- the contract says what evidence and methods are admissible;
- live state says what is happening now and why the workstream should continue;
- packets and decisions explain how the state changed.

## Product Target

The system should let one human researcher lead many AI-assisted alignment
workstreams without losing observability, judgment, or agenda control.

It is not trying to be the agent runtime, the paper queue, or the experiment
runner. Agent runtimes can remain external as long as they emit state packets,
artifact links, and enough provenance for review.

The control surface should help answer:

- What is each workstream trying to establish?
- What changed since the last review?
- Why is this workstream still worth running?
- Which workstreams duplicate, contradict, block, or depend on each other?
- Which outputs are local observations and which are safe to reuse?
- What should continue, stop, merge, split, narrow, replicate, escalate, or be
  promoted?

## Build Sequence

### 0. Registry MVP

Status: present.

Keep this small and durable. The registry is the substrate every later layer
points at.

Useful hardening:

- JSON schema or validation for workstream, live-state, packet, and decision
  files;
- stable CLI output for scripts and future UI;
- migration story before persisted files start changing shape;
- fixtures that demonstrate a small multi-workstream research program.

### 1. Research Contracts

Status: next build.

Contracts are the upstream primitive. A contract defines the rules of the
workstream before results exist:

- research question and why it matters;
- prior claims and assumptions;
- allowed methods and disallowed shortcuts;
- progress criteria, failure criteria, and result criteria;
- expected intermediate artifacts;
- known traps and invalid evidence;
- escalation triggers and stop conditions;
- relationship to other workstreams.

Implementation shape:

- store contracts under `.alignment-fab/contracts/`;
- give each contract an id, version, status, and human approval fields;
- support `create`, `show`, `validate`, `revise`, and `attach` flows;
- keep workstreams pointing at a specific contract version.

### 2. Supervisor Review Loop

Status: after contracts.

The first useful loop is not automation. It is a scan-and-decide workflow:

- list stale, blocked, suspicious, or review-due workstreams;
- show contract, live state, recent packets, decisions, deviations, and
  artifacts together;
- record human actions with rationale;
- update status and review due dates from decisions.

This is where `reason_for_continuing` becomes load-bearing. A workstream that
cannot justify another unit of compute should be flagged for review.

### 3. Artifact And Provenance Pointers

Status: after the review loop.

The system should link to evidence without becoming an artifact warehouse:

- reports, logs, code, plots, datasets, prompts, model versions, and eval runs;
- provenance for generated data and changed code;
- snapshots before private or sealed evaluation;
- explicit references from claims to supporting artifacts.

### 4. Consolidation Pass

Status: first agent-assisted layer.

A consolidation pass compares workstreams before final reports exist. It should
surface:

- duplicated effort;
- contradictory results;
- shared weak assumptions;
- repeated method failures;
- promising methods;
- orphaned results;
- claims with weak evidence;
- areas with too much or too little activity.

The output should be proposed interventions for human review, not automatic
managerial action.

### 5. Promotion Layer

Status: later.

Promotion controls what becomes reusable outside a local workstream. A promoted
result should include:

- producing workstream and contract version;
- prior claims it bears on;
- replication or critique status;
- assumptions and scope;
- downstream workstreams allowed to depend on it;
- what is explicitly not licensed by the result.

Keep three decisions separate:

- Did the agent do valid local work?
- Should this workstream continue?
- Can others safely build on this result?

### 6. Pilot Evaluation

Status: target experiment.

The first derisking experiment:

> Can one researcher use contracts, consolidation, and a supervisor interface to
> manage 50 parallel agent workstreams better than ordinary reports from 5-10
> workstreams?

Measure whether the researcher can:

- kill weak workstreams;
- redirect confused ones;
- identify duplicated effort;
- catch invalid results;
- select useful intermediate results;
- decide what should be exposed to other agents or humans.

Candidate pilot areas:

- A3-style safety finetuning;
- automated weak-to-strong experiments;
- model-organism studies;
- control-protocol experiments;
- frontier-relative monitorability experiments.

## Design Warnings

These came up repeatedly in the KB research and should stay visible while
building:

- Managerial illusion: clean dashboards over shallow work.
- Contract Goodharting: agents optimize for the contract rather than the
  research need.
- Self-certified progress: the same optimization process proposes, validates,
  and narrates the claim.
- Consolidation loss: compression hides the ambiguity that mattered.
- Promotion laundering: local results become shared assumptions before their
  scope is understood.
- Research monoculture: parallel agents converge on easy-to-measure directions.
- Human rubber-stamping: too many proposed interventions turn oversight
  ceremonial.
- Capability acceleration: automated alignment work may accelerate general AI
  R&D more than alignment.

## Immediate Next Actions

1. Add contract data structures and validation.
2. Add contract CLI commands and attach contract versions to workstreams.
3. Create a sample `.alignment-fab` fixture with a small research program.
4. Add review-oriented list filters: stale, blocked, flagged, review-due.
5. Add a supervisor-oriented `show` view that puts contract, live state,
   packets, decisions, and artifacts in one place.
