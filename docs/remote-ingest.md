# Remote Execution And Ingest

Fab should not be bundled into every research agent.

The Maestro branch was a useful short circuit: an agent cloned Fab, wrote
artifacts into `runs/`, and called `fab packet`. That proved the protocol loop,
but it is not the intended boundary for real execution.

## Decision

External agents need the contract, their execution environment, and the output
protocol. They do not need the Fab repo or write access to the Fab store.

For the MVP, the concrete substrate is the public `inwaves/Alexandria` repo. An
agent can write a completed run bundle into Alexandria, commit it, and push. Fab
then an ingester service watches commits or Fab is invoked manually against a
bundle path. The local `ingest-run` command is the inner validation path that
the ingester service will call.

The intended shape is:

```text
contract + context
-> external execution platform
-> Alexandria commit containing an agent run bundle
-> Alexandria ingester service
-> Fab ingest boundary
-> Fab registry
-> brief
-> human judgment
-> optional Alexandria write-back
```

An execution platform such as Podium owns execution, sandboxing, tool access,
compute, logs, and artifact storage. Fab owns validation, registration,
briefing, and human judgment.

## Run Bundle

A completed run should be emitted as a bundle in Alexandria, a local directory,
object-store prefix, or another inbox. The Alexandria MVP can use:

```text
artifacts/<program>/<workstream_id>/<run_id>/
  manifest.json
  artifact/
    report.md
    code/
    results/
    logs/
  READY
```

The artifact is the bundle. Code, results, logs, plots, and prose all belong
inside that bundle when they exist. Fab should not require separate artifact
types such as `code` or `plot`.

Example:

```text
artifact/
    report.md
    code/
      analysis.py
    results/
      cluster-audit.json
      tradeoff.png
    logs/
      stdout.txt
      tool-calls.jsonl
```

The `READY` marker means the bundle is complete and safe to ingest. Without
that marker, Fab should assume the run may still be writing files.

The manifest is the minimal contract between the execution platform and Fab:

```json
{
  "workstream_id": "ws_001",
  "contract": {
    "id": "contract_pilot_a3_false_positive",
    "version": 1
  },
  "source": "podium/remote-agent-maestro/run-abc123",

  "summary": "Audited the baseline cluster claim. Current evidence supports seeded decoding-stability only; broader stability is untested.",
  "status": "completed_with_limitations",

  "claims": [
    "The baseline cluster evidence currently supports decoding-RNG stability only."
  ],

  "evidence": [
    {
      "summary": "The prior Fab artifact only recorded stability across three seeded eval passes.",
      "path": "artifact/report.md"
    }
  ],

  "limitations": [
    "Original dataset and model artifacts were not available, so the original scan was not rerun."
  ],

  "next": [
    "Run paraphrase-perturbation stability.",
    "Record the embedding model used for clustering."
  ],

  "used_refs": [
    "fab://ws_001/art_001",
    "alexandria://papers/a3-an-automated-alignment-agent-for-safety-finetun.md"
  ]
}
```

Allowed `status` values for the MVP:

- `completed`
- `completed_with_limitations`
- `failed`

If a run needs attention, the agent writes the reason in `limitations`. Fab can
mechanically surface any non-empty `limitations` list for human review. The MVP
manifest has no separate attention field.

Paths in `manifest.json` are relative to the run-bundle root. For Alexandria,
Fab records the bundle root path and the commit it ingested from. For other
stores, Fab can record the bundle root URI plus relative paths; it does not need
every file to carry its own full URI.

## Fab Ingest Boundary

The current implementation is explicit:

```bash
uv run fab ingest-run --from /path/to/run-bundle
```

That command should:

- require `READY`;
- parse and validate `manifest.json`;
- check that the workstream exists;
- check that the manifest contract matches the workstream contract;
- record the artifact bundle root;
- append a state packet;
- update live state;
- record ingest status.

Fab should keep this boundary small. It is the validation and registration
primitive, not the long-running process that watches a repository or object
store.

## Alexandria Ingester Service

The current implementation is a small service around this boundary, not a Fab
CLI command:

```bash
uv run python -m services.alexandria_ingester \
  --alexandria ../alexandria \
  --store .fab
```

It can run once, or poll:

```bash
uv run python -m services.alexandria_ingester \
  --alexandria ../alexandria \
  --store .fab \
  --pull \
  --poll-interval 60
```

For the Alexandria MVP, the service should:

- keep a local checkout of Alexandria up to date;
- scan `artifacts/<program>/<workstream_id>/<run_id>/` for `READY`;
- ignore incomplete bundles;
- ingest each completed bundle once;
- keep an ingest ledger outside the raw agent bundle;
- record the Alexandria commit, bundle relative path, manifest hash, ingest
  status, packet id, and any error;
- surface errors without rewriting agent output.

The current service implements this as an append-only JSONL ledger under:

```text
<fab-store>/ingest-ledger/alexandria.jsonl
```

Successful ledger entries block re-ingest by bundle relative path. Error entries
do not block retry.

The loop is deliberately boring:

```text
fetch Alexandria
-> find READY bundles under artifacts/
-> skip bundles already in the ingest ledger
-> run Fab ingest validation
-> record packet id or error in the ledger
-> expose status to the human/operator
```

This service is not part of the agent execution lifecycle. It is the bridge
between a durable artifact inbox and Fab's registry.

## Durable Smoke Fixture

Alexandria contains a persistent fixture at:

```text
artifacts/safety-finetuning-pilot/ws_001/fab-ingest-smoke-001/
```

Fab's test suite ingests that fixture into a temporary pilot store when a
sibling Alexandria checkout is present. Set `FAB_ALEXANDRIA_REPO` to run the
test against another checkout. The fixture proves the connection from
Alexandria bundle shape to Fab's ingest boundary; it does not test commit
watching or exactly-once behavior.

## Alexandria Write-Back

Alexandria is also the durable knowledge substrate. Fab may later write
transformed findings, attention notes, or human-approved updates back to
Alexandria. The incoming artifact bundle should remain intact. Write-back should
land somewhere separate from raw agent artifacts so the substrate does not blur
agent output, Fab transformation, and human judgment.

## Non-Goals

Remote ingest is not:

- an agent runner;
- a scheduler;
- a sandbox;
- a compute allocator;
- a replacement for Podium or another execution platform;
- the only writer to Alexandria.

Fab receives completed research output. It does not manage the agent lifecycle.

## Open Questions

- Should Fab copy small artifacts into a managed store, or always record URIs?
- How should duplicate bundles be detected: run id, content hash, packet id, or
  all three?
- Where should ingest errors live so a failed bundle can be repaired without
  losing traceability?
- How much artifact existence checking should Fab do for object-store URIs?
