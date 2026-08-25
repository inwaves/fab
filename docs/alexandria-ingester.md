# Alexandria Ingester Service

The Alexandria ingester is a thin service around Fab's existing ingest boundary.
It is not an agent runner and it is not a new research protocol.

It does four jobs:

- find completed bundles in Alexandria;
- skip bundles already ingested successfully;
- call Fab's `ingest_run_bundle` validation path;
- append an ingest ledger entry with packet id or error details.

## Run Once

```bash
uv run python -m fab.services.alexandria_ingester \
  --alexandria ../alexandria \
  --store .fab
```

With JSON output:

```bash
uv run python -m fab.services.alexandria_ingester \
  --alexandria ../alexandria \
  --store .fab \
  --json
```

The default ledger path is:

```text
<fab-store>/ingest-ledger/alexandria.jsonl
```

## Polling Mode

```bash
uv run python -m fab.services.alexandria_ingester \
  --alexandria ../alexandria \
  --store .fab \
  --pull \
  --poll-interval 60
```

`--pull` runs `git pull --ff-only` before each scan. Without `--pull`, the
service scans the checkout exactly as it is on disk.

## Bundle Discovery

For now the service only scans:

```text
artifacts/<program>/<workstream_id>/<run_id>/READY
```

The bundle root is the parent directory of `READY`. The service leaves the raw
agent bundle untouched.

## Ledger Semantics

The ledger is append-only JSONL. Successful entries block re-ingest by bundle
relative path. Error entries do not block retry, so a repaired bundle can be
picked up on the next scan.

Successful entries include:

- Alexandria repo path;
- current Alexandria head commit;
- dirty status;
- bundle relative path;
- last commit touching the bundle;
- manifest path and SHA-256;
- Fab packet id;
- workstream id;
- manifest source.

Error entries include the same bundle metadata plus `error_type` and `error`.

The service exits non-zero if any bundle fails unless `--allow-errors` is set.

## Durable Smoke Fixture

Alexandria contains a fixture at:

```text
artifacts/safety-finetuning-pilot/ws_001/fab-ingest-smoke-001/
```

The Fab test suite uses it to prove the service can ingest a real Alexandria
bundle and then skip it on the next run from the ledger.

## Remaining Hardening

- decide where the service runs in production;
- expose ledger status to a human/operator;
- add an error repair workflow;
- decide whether bundle identity should be only path-based or also include
  manifest hash and commit;
- add locking if multiple ingester instances may run at once.
