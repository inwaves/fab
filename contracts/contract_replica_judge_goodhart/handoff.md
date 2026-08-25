# Handoff: ws_replica_001

You are being given one workstream from a Fab registry. Everything you need is
in this file and the contract next to it (`v001.md`). You do not need Fab.

## Identity

Put these exact values in your manifest. Fab rejects a bundle whose ids do not
match the workstream it is registered against.

| Field | Value |
|---|---|
| program | `replication-oversight` |
| workstream_id | `ws_replica_001` |
| contract.id | `contract_replica_judge_goodhart` |
| contract.version | `1` |

## What to do

Read `v001.md`. The Research Question, Brief and Attention Boundaries are
binding. Desired Output says what to hand back. Choose your own method within
the Brief's constraints and write it down in `report.md` before you run it.

## What to read first

The contract's Context section lists references as `alexandria://<path>`.
Resolve each one as `<path>` inside a checkout of
https://github.com/inwaves/alexandria. The `https://` references are the paper
itself; it has no Alexandria note yet, so read it from arXiv.

## Where the result goes

Repository: https://github.com/inwaves/alexandria, branch `main`.

Directory: `artifacts/replication-oversight/ws_replica_001/<run-id>/`, where
`<run-id>` is lowercase letters, digits and hyphens, unique under that
workstream, for example `judge-goodhart-001`. One run per directory. Never
modify a directory after you have written `READY`; start a new run id instead.

```text
artifacts/replication-oversight/ws_replica_001/judge-goodhart-001/
  manifest.json
  artifact/
    report.md
    tasks/
    attempts/
    analysis/
  READY
```

Everything you produce goes inside `artifact/`. `READY` is an empty file and
must be written last, after everything else is committed. It is the signal the
ingester waits for: a directory without `READY` is ignored; a directory with it
is ingested once and never re-read.

## manifest.json

All ten fields are required. Extra fields are ignored.

| Field | Type | Rule |
|---|---|---|
| `workstream_id` | string | exactly `ws_replica_001` |
| `contract` | object | exactly `{"id": "contract_replica_judge_goodhart", "version": 1}` (integer version) |
| `source` | string | who produced this; use `alexandria/replication-oversight/ws_replica_001/<run-id>` |
| `summary` | string | one or two sentences: what you did and what you found |
| `status` | string | one of `completed`, `completed_with_limitations`, `failed` |
| `claims` | list of strings | one sentence each; every claim checkable against a named file in `artifact/` |
| `evidence` | list of `{"summary": str, "path": str}` | `path` is relative to the bundle root and must exist; no `..`, no absolute paths, no URLs. The format allows `path` to be omitted; for this workstream put one on every entry, under `artifact/`, so each claim can be checked |
| `limitations` | list of strings | anything a human must know, including any attention boundary you hit |
| `next` | list of strings | what you would do with more budget or approval |
| `used_refs` | list of strings | every `alexandria://` or `https://` source you relied on, as written in the contract where possible |

Example for this workstream (numbers illustrative):

```json
{
  "workstream_id": "ws_replica_001",
  "contract": {"id": "contract_replica_judge_goodhart", "version": 1},
  "source": "alexandria/replication-oversight/ws_replica_001/judge-goodhart-001",
  "summary": "Best-of-N selection by a rubric judge raised rubric scores on all 8 tasks but raised numeric fidelity on only 3; the gap grew with N.",
  "status": "completed_with_limitations",
  "claims": [
    "Across 8 tasks and 6 attempts each, best-of-6 by rubric improved mean rubric score by 0.31 (0-1 scale) but mean fidelity by 0.04.",
    "Spearman correlation between rubric score and fidelity was below 0.3 on 5 of 8 tasks."
  ],
  "evidence": [
    {"summary": "Per-task rubric and fidelity at each N.", "path": "artifact/analysis/best_of_n.csv"},
    {"summary": "Rubric vs fidelity curves.", "path": "artifact/analysis/best_of_n.png"},
    {"summary": "Every attempt's emitted values and judge scores.", "path": "artifact/attempts"}
  ],
  "limitations": [
    "Two of ten candidate tasks were dropped because ground-truth numbers could not be recovered; the pool is ML-only.",
    "Judge model and attempt-generating agent are from the same provider, which may inflate agreement."
  ],
  "next": [
    "Repeat with a judge model from a different provider.",
    "Add the director/executor split from the paper as a second condition."
  ],
  "used_refs": [
    "https://arxiv.org/abs/2608.13331",
    "alexandria://papers/reward-hacking-in-the-era-of-large-models-mechanisms.md"
  ]
}
```

## What gets a bundle rejected

The ingester records a rejection in its ledger and moves on. Nobody tells you,
so check before writing `READY`:

- `READY` or `manifest.json` missing, or either is not a plain file inside the
  bundle (no symlinks pointing out).
- `artifact/` missing, or a symlink pointing outside the bundle.
- Any required manifest field missing, empty, or of the wrong type.
- `status` not one of the three values.
- `workstream_id` or `contract` not matching the table above.
- An evidence `path` that is absolute, contains `..`, contains `://`, does not
  exist, or resolves outside the bundle.

## Self-check before you write READY

Either validate `manifest.json` against the schema:

```bash
pip install check-jsonschema
check-jsonschema --schemafile https://raw.githubusercontent.com/inwaves/fab/main/schemas/run-manifest.schema.json manifest.json
```

or run Fab's own bundle validator without installing anything permanently:

```bash
uvx --from git+https://github.com/inwaves/fab fab validate-bundle <bundle-dir> \
  --workstream-id ws_replica_001 \
  --contract-id contract_replica_judge_goodhart --contract-version 1
```

The second check is the same code the ingester runs. Both checks enforce the
format only. They do not check this handoff's expectations about content (a
`path` on every evidence entry, claims that name their file); a human judges
those from the brief.

## How your output is used

A human reads a brief built from your manifest, not your report. Write `claims`
so each one stands alone and points at a file. Put anything that needs a human
decision in `limitations`; it is the only field that raises attention. Use
`completed` only if you did what the contract asks with no deviations;
`completed_with_limitations` if you stopped early, dropped tasks, or changed
method; `failed` if there is no result. List in `used_refs` what you actually
used; Fab compares it with the contract's Context.

## If you hit an attention boundary

There is no channel back. Stop, write a bundle with status
`completed_with_limitations` (or `failed`), say in `limitations` what you need
approval for, and in `next` what you would do with it.
