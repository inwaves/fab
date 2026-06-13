# Podium Shim

The Podium shim is a test bridge, not a Fab execution layer.

Fab should not know how to deploy agents, schedule work, allocate sandboxes, or
read Podium state. For the full MVP dogfood run, the shim only translates a Fab
workstream into a message that can be sent to an already-running Podium agent.
The return path remains the existing Alexandria run-bundle ingest path.

```text
Fab workstream + contract
-> services.podium_shim prepare
-> podium send <instance-id> --json-input podium-send.json
-> Podium-hosted agent does the work
-> agent writes artifacts/<program>/<workstream>/<run>/... in its execution workspace
-> execution platform exports that bundle to Alexandria or another durable inbox
-> services.alexandria_ingester
-> Fab brief / judgment
```

## Why This Shape

Podium already owns the lifecycle of agents. Fab only needs to say:

- what contract and workstream the agent is answering;
- what relative bundle path the completed run should use;
- what `manifest.json` must contain;
- that `READY` is written last.

That keeps Fab decoupled from Podium. The same request could be sent through
another execution platform if it can deliver the prompt and export the finished
run bundle.

## Prepare A Request

```bash
uv run python -m services.podium_shim prepare \
  --store .fab \
  --workstream-id ws_001 \
  --alexandria ../alexandria \
  --run-id podium-smoke-001 \
  --out /tmp/fab-podium/ws_001
```

This writes:

```text
/tmp/fab-podium/ws_001/
  fab-execution-request.json
  prompt.md
  podium-send.json
```

`fab-execution-request.json` is the platform-neutral request. `prompt.md` is the
human-readable instruction for a generic research/coding agent. `podium-send.json`
is the Podium WebSocket payload shape accepted by:

```bash
podium send <instance-id> --json-input /tmp/fab-podium/ws_001/podium-send.json
```

The shim can also call the CLI:

```bash
uv run python -m services.podium_shim send \
  --instance-id <instance-id> \
  --message-json /tmp/fab-podium/ws_001/podium-send.json
```

Use `FAB_PODIUM_COMMAND` if the local Podium CLI is not simply `podium`, for
example:

```bash
FAB_PODIUM_COMMAND="python3 -m podium_cli.cli" \
  uv run python -m services.podium_shim send \
  --instance-id <instance-id> \
  --message-json /tmp/fab-podium/ws_001/podium-send.json
```

Podium gateway configuration and credentials should stay in Podium's usual
environment variables or CLI options.

The `--alexandria` path is local operator bookkeeping. It is not sent to the
agent as a sandbox path, because a remote Podium sandbox cannot see a local
`/Users/.../alexandria` checkout. The request tells the agent to create the
bundle at the same relative path inside its execution workspace:

```text
artifacts/<program>/<workstream_id>/<run_id>/
```

If Podium, another execution platform, or the researcher provides a writable
Alexandria checkout, object-store prefix, or git credentials, the agent can also
copy or commit the completed bundle there. Otherwise the platform/operator must
retrieve the workspace bundle and land it in Alexandria before Fab ingests it.

## Agent Output

The agent should create exactly one run bundle, normally relative to its
execution workspace:

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

The agent does not call Fab. Once the bundle is exported to Alexandria or a
durable inbox, the existing Alexandria ingester handles validation and
registration.

## Podium Deployment Pinning

For local dogfooding, treat `agent_type:version` as the behavior identity. Local
inspection of Podium shows that instance creation parses
`agent_type:version@hash`, but coordinator-side `ensure_deployment` resolves and
caches deployments by `agent_type + version`. If that version already exists on
a coordinator, the hash suffix alone does not force that coordinator to replace
its local copy.

Practical rule: every behavior change to a Podium-hosted Fab research agent gets
a version bump, or the operator must explicitly purge/retire the cached
deployment before running a smoke. For the current research agent, the pinned
smoke target is `fab-research` `0.1.1`, which keeps Sonnet 4.6 and routes it
through Ensemble with `target_provider=vertex`.

## Non-Goals

The shim is not:

- a `fab podium` command;
- a scheduler;
- a Podium deployment manager;
- a log collector;
- a replacement for the Alexandria ingester;
- a permanent execution abstraction.

It exists so the MVP can be dogfooded with Podium while preserving the boundary:
execution outside Fab, sense-making inside Fab.
