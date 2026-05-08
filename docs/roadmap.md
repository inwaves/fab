# Fab Roadmap

## Status Checklist

Last updated: 2026-05-08.

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
- [x] Research Protocol MVP skeleton: make the current local skeleton express
  `contract -> workstreams -> artefact packages -> brief -> human judgment`.
- [x] Rich artefact package skeleton: claims, evidence, code, results, logs,
  limitations, suggested follow-up, and used references.
- [x] Brief skeleton: produce a concise batch view with attention reasons,
  artifacts, claims, judgments, and next-context buckets.
- [x] Human judgment record: capture what the researcher trusts, rejects, wants
  replicated, escalates, prevents from propagating, or feeds into a revised
  contract, with targets on workstreams, artifacts, and claims.
- [~] Remote execution ingest boundary: `ingest-run` accepts completed local
  bundles; Alexandria commit monitoring is not started.
- [ ] Batch comparison: surface convergence, contradictions, shared assumptions,
  eval shortcuts, gaps, and replication needs.
- [ ] Knowledge substrate interface: allow contracts and workstreams to reference
  prior knowledge and artefacts through adapters without turning Fab into a
  generic knowledge substrate.

Deferred:

- [ ] Workstream fan-out / programme shape: figure out only after the local MVP
  brief and judgment loop is useful.
- [ ] Promotion layer: controlled reuse of validated results across workstreams.
- [ ] Full consolidation system: large-scale duplicate, contradiction, lineage,
  and dependency analysis across many programmes.
- [ ] UI/dashboard: only after the protocol loop is valuable in local form.

Current focus: connect the local ingest primitive to the Alexandria substrate,
then make the brief useful for comparison and loop closure.

## Product Target

Fab helps human alignment researchers oversee many thousands of autonomous agent
contributions without owning the agent execution platform.

Fab owns the research protocol:

```text
contract
-> workstreams
-> remote ingest
-> artefact packages
-> brief
-> human judgment
```

External agent systems execute workstreams. Fab defines what context agents
receive, what output bundles they must emit, how those bundles are ingested, how
their outputs are compared, and how human judgment feeds the next contract or
programme state.

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

The current code exposes `attention`, `brief`, `show --brief`, `judge`, and
`ingest-run` commands. They are still local skeletons for the protocol objects.

The current code can ingest one completed local run bundle. The next boundary is
watching Alexandria commits so agents can publish bundles without cloning Fab.

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
- code when code produced the result;
- results and logs;
- limitations;
- suggested follow-up.

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

### 4. Remote Execution Ingest

Status: local ingest primitive present; Alexandria watcher not started.

The Maestro branch proved that an external agent can produce useful Fab-shaped
work: claims, evidence, limitations, follow-up, and an artifact bundle. It did
so by cloning Fab and calling `fab packet` directly. That should remain a test
shortcut, not the production boundary.

For the MVP, the intended boundary is:

```text
contract + context
-> Podium or another execution platform
-> Alexandria commit containing a completed run bundle
-> Fab ingest adapter
-> Fab registry
-> brief / attention
-> optional Alexandria write-back
```

The agent should not need the Fab repo. It should receive:

- the contract;
- workstream context;
- execution tools and environment;
- the Fab output manifest schema.

It should return:

- `manifest.json` with summary, status, claims, evidence, limitations, next
  steps, and used references;
- one artifact bundle containing report, code, results, and logs when present;
- a completion marker such as `READY`.

Implemented:

- `fab ingest-run --from <bundle>` for local bundle paths.

Next build target:

- `fab watch-alexandria <repo>` for new bundles committed under
  `artifacts/<program>/<workstream_id>/<run_id>/`.

The watcher should reuse the same validation path as manual ingest. Fab should
record the artifact bundle root and manifest metadata; it should not assume
research artifacts live inside the Fab framework repo.

### 5. Batch Comparison

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

### 6. Knowledge Substrate Interface

Status: design only.

Fab needs access to prior knowledge: previous experiments, artefacts, code,
human judgments, papers, and research notes. Alexandria is the public MVP
substrate for that exchange.

The interface should let contracts and workstreams reference prior knowledge,
while leaving write-back and durable understanding under human judgment.

Fab should define source adapters and lightweight resolution records, not a
heavy ontology over Alexandria. Public Fab can assume Alexandria for the MVP
without making Alexandria's folder conventions the permanent product boundary.

The MVP should keep research contracts natural-language first. If a researcher
cares about exact context, they should put an exact URI or path in the contract.
Fab should resolve explicit references, record what version was used, and later
compare that with the references an agent says it used.

Initial build target:

- source registry with aliases such as `alexandria://`, `fab://`, and `s3://`;
- resolution snapshots for explicit references in contracts and workstreams;
- `refs check` for unresolved, dirty, unpinned, or unsafe explicit references;
- `context show` for the contract plus resolved explicit references;
- ingest support for `used_refs`;
- brief surface for missing, stale, unresolved, or unreviewed references.

Later build target:

- adapter-driven export of human-approved Alexandria updates.

## Design Warnings

- Clean structure can make shallow work look real.
- Agents can optimize for easy-to-measure proxy progress.
- A prose report can erase the dead ends and code details needed for replication.
- A graph can become bookkeeping rather than knowledge.
- Local results can become shared assumptions before their scope is understood.
- Many agents can converge on the same fragile method family.
- Too many proposed actions can turn human judgment into rubber-stamping.

## Immediate Next Actions

1. Add `fab watch-alexandria <repo>` over the same validation path as
   `ingest-run`.
2. Improve comparison inside `fab brief`: convergence, contradictions, shared
   assumptions, repeated failures, shortcut risk, and replication needs.
3. Turn `next_context` into a clearer bridge from judgments to the next contract
   or context package.
4. Add a thin prior-knowledge/reference interface with Alexandria as the public
   adapter target.
5. Leave workstream fan-out/programme shape as a later design problem.
