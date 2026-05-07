# Artefact Packages And Provenance

Artefacts are the durable outputs of ephemeral agent work. A prose report is not
enough. Later agents and humans may need the code, configs, prompts, evals,
datasets, logs, plots, failed attempts, and reproduction notes that made the
result possible.

The current code implements structured artefact pointers. The design target is
a richer artefact package.

## Why This Exists

Fab should make agent research cumulative. That requires more than summaries:

- What claim does this artefact support?
- What run produced it?
- Which code, dataset, prompt, model, eval, or scaffold was involved?
- What failed before this result appeared?
- What would be needed to reproduce it?
- Was it produced independently of related workstreams?
- Is it local evidence, or can later work safely build on it?

The artefact package is the research output. It is the thing a later contract or
workstream can reference.

## Current Pointer Shape

```json
{
  "id": "art_001",
  "kind": "report",
  "path": "runs/ws_001/baseline-report.md",
  "description": "Baseline eval summary",
  "produced_by": "agent-a",
  "created_at": "2026-05-07T10:00:00Z",
  "provenance": {
    "code": ["src/evals/refusal_eval.py"],
    "datasets": ["data/refusal-benign-v1.jsonl"],
    "models": ["qwen-8b-lora-run-003"],
    "prompts": ["prompts/refusal-eval-v2.md"],
    "evals": ["evals/refusal-fp-v1"]
  },
  "review": {
    "local_only": true,
    "safe_to_reuse": false,
    "notes": null
  }
}
```

Defaults:

- `id` is generated if omitted.
- `kind` defaults to `artifact`.
- `produced_by` defaults to the packet source.
- `created_at` defaults to the packet timestamp.
- provenance lists default to empty.
- `review.local_only` defaults to `true`.
- `review.safe_to_reuse` defaults to `false`.

## Target Package Shape

A future artefact package should be able to include:

- claims;
- evidence;
- code and patches;
- configs and dependency notes;
- datasets and data generation scripts;
- prompts and eval definitions;
- model identifiers and checkpoints;
- run logs;
- tables and plots;
- failed attempts;
- uncertainty and caveats;
- reproduction instructions;
- suggested follow-up.

This can be represented as a directory, manifest, database record, or external
object. Fab should care about the protocol shape, not one storage backend.

## CLI

For a simple path-only artefact:

```bash
uv run fab packet ws_001 \
  --source agent-a \
  --artifact runs/ws_001/baseline-report.md
```

For a structured artefact pointer:

```bash
uv run fab packet ws_001 \
  --source agent-a \
  --artifact-json '{"kind":"report","path":"runs/ws_001/baseline-report.md","description":"Baseline eval summary","provenance":{"code":["src/evals/refusal_eval.py"],"datasets":["data/refusal-benign-v1.jsonl"],"models":["qwen-8b-lora-run-003"],"prompts":["prompts/refusal-eval-v2.md"],"evals":["evals/refusal-fp-v1"]}}'
```

Multiple `--artifact` and `--artifact-json` flags can be used in one packet.

## Reuse Semantics

Artefacts are local by default. Producing a report, plot, or code patch does not
mean later workstreams should depend on it.

Changing `safe_to_reuse` should require human judgment and a scope note. Full
promotion is a later layer.
