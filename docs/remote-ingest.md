# Remote Execution And Ingest

Fab should not be bundled into every research agent.

The Maestro branch was a useful short circuit: an agent cloned Fab, wrote
artifacts into `runs/`, and called `fab packet`. That proved the protocol loop,
but it is not the intended boundary for real execution.

## Decision

External agents need the contract, their execution environment, and the output
protocol. They do not need the Fab repo or write access to the Fab store.

The intended shape is:

```text
contract + context
-> external execution platform
-> agent run bundle
-> Fab ingest adapter
-> Fab registry
-> brief
-> human judgment
```

An execution platform such as Podium owns execution, sandboxing, tool access,
compute, logs, and artifact storage. Fab owns validation, registration,
briefing, and human judgment.

## Run Bundle

A completed run should be emitted as a bundle in a local directory, object-store
prefix, or other inbox:

```text
<inbox>/<program>/<workstream_id>/<run_id>/
  manifest.json
  artifacts/
    report.md
    results.json
    plot.png
    script.py
  logs/
    stdout.txt
    tool-calls.jsonl
  READY
```

The `READY` marker means the bundle is complete and safe to ingest. Without
that marker, Fab should assume the run may still be writing files.

The manifest is the packet-level contract between the execution platform and
Fab:

```json
{
  "workstream_id": "ws_001",
  "contract": {
    "id": "contract_pilot_a3_false_positive",
    "version": 1
  },
  "source": "podium/remote-agent-maestro/run-abc123",
  "tried": "...",
  "result": "...",
  "failed": "...",
  "next_action": "...",
  "rationale": "...",
  "blockers": [],
  "deviations": [],
  "flags": ["..."],
  "artifacts": [
    {
      "id": "art_external_001",
      "kind": "report",
      "uri": "s3://fab-inbox/program/ws_001/run-abc123/artifacts/report.md",
      "description": "...",
      "claims": [],
      "evidence": [],
      "failed_attempts": [],
      "uncertainty": "...",
      "reproduction": {
        "commands": [],
        "environment": [],
        "notes": null
      },
      "suggested_follow_up": [],
      "provenance": {
        "code": [],
        "configs": [],
        "datasets": [],
        "models": [],
        "prompts": [],
        "evals": [],
        "logs": [],
        "outputs": []
      }
    }
  ]
}
```

For the current file-backed MVP, artifact `uri` may be a local path, object-store
URI, or stable content-addressed reference. Fab should record pointers and
metadata; it should not assume artifacts live inside the Fab framework repo.

## Ingest Adapter

The first implementation should be explicit:

```bash
uv run fab ingest-run --from /path/to/run-bundle
```

That command should:

- require `READY`;
- parse and validate `manifest.json`;
- check that the workstream exists;
- check that the manifest contract matches the workstream contract;
- normalize artifact pointers;
- append a state packet;
- update live state;
- record ingest status and errors.

The later implementation can watch an inbox:

```bash
uv run fab watch-inbox s3://fab-inbox/
```

The watcher should be a convenience over the same validation path, not a second
protocol.

## Non-Goals

Remote ingest is not:

- an agent runner;
- a scheduler;
- a sandbox;
- a compute allocator;
- a replacement for Podium or another execution platform;
- a durable knowledge-base promotion layer.

Fab receives completed research output. It does not manage the agent lifecycle.

## Open Questions

- Should Fab copy small artifacts into a managed store, or always record URIs?
- What is the minimum manifest schema needed before agents can use this without
  cloning Fab?
- How should duplicate bundles be detected: run id, content hash, packet id, or
  all three?
- Where should ingest errors live so a failed bundle can be repaired without
  losing traceability?
- How much artifact existence checking should Fab do for object-store URIs?
