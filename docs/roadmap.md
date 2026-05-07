# Fab Roadmap

## Status Checklist

Last updated: 2026-05-07.

Legend: `[x] done`, `[~] in progress`, `[ ] not started`.

- [x] Environment: Python 3.14 configured via `.python-version` and `.venv`;
  tests pass with `uv run python -m unittest discover -s tests`.
- [x] Rename: public command, package, docs, and default store now use `fab`.
- [x] Registry skeleton: file-backed workstreams, live state, packets, human
  judgments, links, and contract pointers.
- [x] Contract skeleton: immutable Markdown version files, read-only attachment
  lock, template, pointer validation, and tests.
- [x] Artefact pointer skeleton: structured links to reports, logs, code,
  datasets, prompts, model versions, and eval runs.
- [x] Pilot fixture: simulated black-box-agent packets for a small
  multi-workstream alignment programme.
- [~] Research Protocol MVP: make the current skeleton express
  `contract -> workstreams -> artefact packages -> brief -> human judgment`.
- [ ] Workstream batch plan: represent coverage, diversity, replication,
  critique, validation, and exploration.
- [ ] Rich artefact package: claims, evidence, code, datasets, configs, logs,
  uncertainty, failures, suggested follow-up, and provenance.
- [ ] Batch comparison: surface convergence, contradictions, shared assumptions,
  eval shortcuts, gaps, and replication needs.
- [ ] Brief: produce the concise batch view a human researcher actually reads.
- [ ] Human judgment record: capture what the researcher trusts, rejects, wants
  replicated, escalates, prevents from propagating, or feeds into a revised
  contract.
- [ ] Knowledge substrate interface: allow contracts and workstreams to reference
  prior knowledge and artefacts without turning Fab into a generic KB.

Deferred:

- [ ] Promotion layer: controlled reuse of validated results across workstreams.
- [ ] Full consolidation system: large-scale duplicate, contradiction, lineage,
  and dependency analysis across many programmes.
- [ ] UI/dashboard: only after the protocol loop is valuable in local form.

Current focus: Research Protocol MVP.

## Product Target

Fab helps human alignment researchers oversee many thousands of autonomous agent
contributions without owning the agent execution platform.

Fab owns the research protocol:

```text
contract
-> workstreams
-> artefact packages
-> brief
-> human judgment
```

External agent systems execute workstreams. Fab defines what context they
receive, what outputs they must emit, how their outputs are compared, and how
human judgment feeds the next contract or programme state.

## Current State

The repo contains a local, file-backed skeleton:

- stable workstream records under `.fab/workstreams/`;
- separate live-state records under `.fab/live-state/`;
- append-only packets under `.fab/state-packets/`;
- append-only human judgments under `.fab/decisions/`;
- immutable Markdown contract versions under `.fab/contracts/`;
- structured artefact references in packets and live state;
- a simulated pilot fixture.

The current code exposes `attention`, `show --brief`, and `judge` commands.
They are still thin local skeletons for the protocol objects.

## Build Sequence

### 0. Registry Skeleton

Status: present.

The registry gives durable identity to workstreams and preserves append-only
history. It is the local substrate for the protocol objects.

Useful hardening:

- JSON schema or validation for persisted records;
- stable JSON output for scripts and future UI;
- migration story before persisted shapes change;
- fixtures that demonstrate complete protocol loops.

### 1. Research Contracts

Status: skeleton present.

Contracts are versioned delegation briefs. They should be brief enough that a
busy research manager can write them, while giving external agents enough
orientation to do useful autonomous work.

Required shape:

- research question;
- why it matters;
- free-form brief;
- desired output;
- optional programme shape;
- optional context links to prior knowledge and artefacts;
- optional attention boundaries known in advance.

The contract should not try to precompute all methods, assumptions, traps, or
failure criteria. Agents should investigate those and report what they find.

### 2. Workstream Batch Plan

Status: next.

A contract should be able to produce a batch of workstreams with deliberate
coverage:

- exploratory attempts;
- independent replications;
- critique workstreams;
- validation workstreams;
- extensions of prior artefacts;
- intentionally diverse method families or scaffolds.

This is not execution scheduling. It is the research shape Fab asks an external
agent system to instantiate.

### 3. Artefact Packages

Status: pointers present; packages next.

A workstream output should be a research artefact package, not just a report.
The package should include:

- claims;
- evidence;
- code, configs, scripts, notebooks, and patches;
- datasets, prompts, evals, model identifiers, and run logs;
- failed attempts;
- uncertainty;
- reproduction notes;
- suggested follow-up;
- provenance.

This is where agent work becomes durable.

### 4. Batch Comparison

Status: not started.

Before a human reads the batch, Fab should compare workstreams and surface:

- independent convergence;
- contradictions;
- shared assumptions;
- repeated failures;
- likely shortcuts;
- eval leakage risk;
- untested branches;
- artefacts needing replication or critique.

This should be useful before a formal consolidation layer exists.

### 5. Brief And Human Judgment

Status: early placeholder present.

The brief is the concise human-facing account of a batch. It should allocate
attention and preserve enough evidence for inspection.

Human judgment records what the researcher makes of the output:

- trusted as local evidence;
- rejected;
- interesting but unsupported;
- needs replication;
- needs critique;
- escalate to human/manual review;
- do not propagate;
- usable as context for a later contract;
- candidate for later promotion.

This judgment feeds the next contract version or programme state. It is not
primarily a command to a specific agent.

### 6. Knowledge Substrate Interface

Status: design only.

Fab needs access to prior knowledge: previous experiments, artefacts, code,
human judgments, papers, and research notes. The local `inwaves/kb` repo is a
useful design reference, but Fab should not assume that all future deployments
look like that repo.

The interface should let contracts and workstreams reference prior knowledge,
and let agent outputs propose updates, while leaving durable understanding under
human judgment.

## Design Warnings

- Clean structure can make shallow work look real.
- Agents can optimize for easy-to-measure proxy progress.
- A prose report can erase the dead ends and code details needed for replication.
- A graph can become bookkeeping rather than knowledge.
- Local results can become shared assumptions before their scope is understood.
- Many agents can converge on the same fragile method family.
- Too many proposed actions can turn human judgment into rubber-stamping.

## Immediate Next Actions

1. Add the workstream batch plan object.
2. Expand artefact references toward artefact packages.
3. Build a batch brief over the pilot fixture.
4. Record human judgment on artefacts/claims rather than only workstream status.
