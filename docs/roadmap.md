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
- [x] Research Protocol MVP skeleton: make the current skeleton express
  `contract -> workstreams -> artefact packages -> brief -> human judgment`.
- [x] Rich artefact package skeleton: claims, evidence, code, datasets, configs, logs,
  uncertainty, failures, suggested follow-up, and provenance.
- [x] Brief skeleton: produce a concise batch view with attention reasons,
  artifacts, claims, judgments, and next-context buckets.
- [x] Human judgment record: capture what the researcher trusts, rejects, wants
  replicated, escalates, prevents from propagating, or feeds into a revised
  contract, with targets on workstreams, artifacts, and claims.
- [ ] Batch comparison: surface convergence, contradictions, shared assumptions,
  eval shortcuts, gaps, and replication needs.
- [ ] Knowledge substrate interface: allow contracts and workstreams to reference
  prior knowledge and artefacts without turning Fab into a generic KB.

Deferred:

- [ ] Workstream fan-out / programme shape: figure out only after the local MVP
  brief and judgment loop is useful.
- [ ] Promotion layer: controlled reuse of validated results across workstreams.
- [ ] Full consolidation system: large-scale duplicate, contradiction, lineage,
  and dependency analysis across many programmes.
- [ ] UI/dashboard: only after the protocol loop is valuable in local form.

Current focus: make the MVP loop genuinely useful, especially comparison in the
brief and loop closure into the next context or contract.

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
receive, what outputs agents must emit, how their outputs are compared, and how
human judgment feeds the next contract or programme state.

## Current State

The repo contains a local, file-backed skeleton:

- stable workstream records under `.fab/workstreams/`;
- separate live-state records under `.fab/live-state/`;
- append-only packets under `.fab/state-packets/`;
- append-only human judgments under `.fab/decisions/`;
- immutable Markdown contract versions under `.fab/contracts/`;
- structured artefact package references in packets and live state;
- `brief` summaries over workstreams, artifacts, claims, judgments, attention
  reasons, and next-context buckets;
- a simulated pilot fixture.

The current code exposes `attention`, `brief`, `show --brief`, and `judge`
commands. They are still local skeletons for the protocol objects.

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

### 2. Artefact Packages

Status: skeleton present.

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

### 3. Brief And Human Judgment

Status: skeleton present.

The brief is the concise human-facing account of a batch. It should allocate
attention and preserve enough evidence for inspection.

The current skeleton summarizes:

- workstream status, results, rationale, and next actions;
- attention reasons;
- artifacts and their claim/evidence counts;
- claims and attached judgments;
- targets that are trusted locally, safe as context, need replication, need
  critique, or should not propagate.

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

This should be useful before a formal consolidation layer exists. It should stay
inside the brief path for now rather than becoming a separate fan-out or
programme-shape component.

### 5. Knowledge Substrate Interface

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

1. Improve comparison inside `fab brief`: convergence, contradictions, shared
   assumptions, repeated failures, shortcut risk, and replication needs.
2. Turn `next_context` into a clearer bridge from judgments to the next contract
   or context package.
3. Add a thin prior-knowledge/reference interface, using `inwaves/kb` as an
   example but not as the product boundary.
4. Leave workstream fan-out/programme shape as a later design problem.
