# Artefact Packages And Provenance

Artefacts are the durable outputs of ephemeral agent work. A prose report is not
enough. Later agents and humans may need the code, configs, prompts, evals,
datasets, logs, plots, failed attempts, and reproduction notes that made the
result possible.

The current code implements a small artefact package shape inside state packets
and live state. It is still file-backed and local, but it now captures the parts
needed for the MVP loop: claims, evidence, provenance, uncertainty,
reproduction notes, failures, and follow-up.

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

## Current Package Shape

```json
{
  "id": "art_001",
  "kind": "report",
  "path": "runs/ws_001/baseline-report.md",
  "description": "Baseline eval summary",
  "produced_by": "agent-a",
  "created_at": "2026-05-07T10:00:00Z",
  "claims": [
    {
      "id": "claim_cluster",
      "text": "A baseline cluster is stable enough to inspect.",
      "confidence": "medium",
      "evidence": ["ev_stability"],
      "caveats": ["human labels are missing"]
    }
  ],
  "evidence": [
    {
      "id": "ev_stability",
      "kind": "metric",
      "summary": "Cluster assignments are stable across seeded runs.",
      "path": "runs/ws_001/stability.json",
      "refs": []
    }
  ],
  "failed_attempts": ["unseeded run was too noisy"],
  "uncertainty": "not yet validated",
  "reproduction": {
    "commands": ["uv run python src/evals/refusal_eval.py"],
    "environment": ["python 3.12"],
    "notes": "uses a fixed seed"
  },
  "suggested_follow_up": ["human-label nearest neighbors"],
  "provenance": {
    "code": ["src/evals/refusal_eval.py"],
    "configs": ["configs/refusal_eval.toml"],
    "datasets": ["data/refusal-benign-v1.jsonl"],
    "models": ["qwen-8b-lora-run-003"],
    "prompts": ["prompts/refusal-eval-v2.md"],
    "evals": ["evals/refusal-fp-v1"],
    "logs": [],
    "outputs": ["runs/ws_001/baseline-report.md"]
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
- `claims`, `evidence`, `failed_attempts`, and `suggested_follow_up` default to
  empty lists.
- string claims and evidence are accepted as shorthand and normalized.
- `reproduction.commands` and `reproduction.environment` default to empty lists.
- provenance lists default to empty.
- `review.local_only` defaults to `true`.
- `review.safe_to_reuse` defaults to `false`.

## Later Package Shape

The current package is deliberately simple. Later this may become a directory,
manifest, database record, external object, or a richer bundle with patches,
notebooks, checkpoints, tables, plots, and generated data. Fab should care about
the protocol shape, not one storage backend.

## CLI

For a simple path-only artefact:

```bash
uv run fab packet ws_001 \
  --source agent-a \
  --artifact runs/ws_001/baseline-report.md
```

For a structured artefact package:

```bash
uv run fab packet ws_001 \
  --source agent-a \
  --artifact-json '{"kind":"report","path":"runs/ws_001/baseline-report.md","description":"Baseline eval summary","claims":[{"id":"claim_cluster","text":"A baseline cluster is stable enough to inspect.","confidence":"medium","evidence":["ev_stability"],"caveats":["human labels are missing"]}],"evidence":[{"id":"ev_stability","kind":"metric","summary":"Cluster assignments are stable across seeded runs.","path":"runs/ws_001/stability.json"}],"reproduction":{"commands":["uv run python src/evals/refusal_eval.py"],"environment":["python 3.12"]},"provenance":{"code":["src/evals/refusal_eval.py"],"configs":["configs/refusal_eval.toml"],"datasets":["data/refusal-benign-v1.jsonl"],"models":["qwen-8b-lora-run-003"],"prompts":["prompts/refusal-eval-v2.md"],"evals":["evals/refusal-fp-v1"],"outputs":["runs/ws_001/baseline-report.md"]}}'
```

Multiple `--artifact` and `--artifact-json` flags can be used in one packet.

## Reuse Semantics

Artefacts are local by default. Producing a report, plot, or code patch does not
mean later workstreams should depend on it.

Changing `safe_to_reuse` should require human judgment and a scope note. For
the MVP, use `judge --target-type artifact` or `judge --target-type claim` to
record that judgment. Full promotion is a later layer.
