# Artefact Packages

Artefacts are the durable outputs of ephemeral agent work. A prose report is not
enough. Later agents and humans may need the code, configs, prompts, evals,
datasets, logs, plots, and notes that made the result possible.

The MVP remote-output shape is a single artefact bundle per run. The bundle
contains the report, code, results, logs, and any other files the agent produced.
Its `manifest.json` says what the bundle claims, what supports those claims,
what limited the run, and what should happen next.

For remote execution, artifact contents should usually live outside the Fab
framework repo: in an execution-platform artifact store, a shared filesystem, an
object-store prefix, or a content-addressed store. Fab records pointers and
metadata. It should not assume that `runs/` is inside this repository.

## Why This Exists

Fab should make agent research cumulative. That requires more than summaries:

- What claim does this artefact support?
- What run produced it?
- Which code, dataset, prompt, model, eval, or scaffold was involved?
- What limited the run or result?
- What would be needed to reproduce it?
- Was it produced independently of related workstreams?
- Is it local evidence, or can later work safely build on it?

The artefact package is the research output. It is the thing a later contract,
workstream, or human judgment can reference.

## Remote Bundle Shape

```text
run/
  manifest.json
  artifact/
    report.md
    code/
    results/
    logs/
  READY
```

`manifest.json`:

```json
{
  "workstream_id": "ws_001",
  "contract": {
    "id": "contract_pilot_a3_false_positive",
    "version": 1
  },
  "source": "podium/run-abc123",
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

Fields:

- `summary`: short account of what the run found.
- `status`: `completed`, `completed_with_limitations`, or `failed`.
- `claims`: specific statements the bundle asks humans or later agents to
  consider. Agents do not need to assign IDs; Fab can do that on ingest.
- `evidence`: support for those claims, usually pointing into the artifact
  folder or prior Fab state.
- `limitations`: what blocked, weakened, or scoped the result.
- `next`: suggested next research steps.
- `used_refs`: prior context the agent actually used.

If the run needs attention, put the reason in `limitations`. The MVP manifest
has no separate attention field.

## Local CLI Compatibility

The existing local `fab packet` command can still register path references for
the file-backed skeleton. The remote execution contract is the bundle shape
above. `fab ingest-run` maps that bundle into Fab's internal packet/live-state
records.

## Reuse Semantics

Artefacts are local by default. Producing a bundle does not mean later
workstreams should depend on it. Reuse should come from human judgment, not from
an agent-declared manifest field. Full promotion is a later layer.
