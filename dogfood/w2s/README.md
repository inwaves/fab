# Weak-to-Strong Fab Dogfood

A real end-to-end exercise of Fab's MVP loop on a real research contract with
real agent-produced artefacts. **Status: run end-to-end for 5 agents.**

This lives in the Fab repo because it *is* a Fab dogfood — it directly serves
the roadmap's current focus ("dogfood the MVP loop on real contracts and
tighten what breaks"). It drives external systems (Podium, agentlib/agents,
Ensemble/Anthropic) which are **not** part of Fab; the harness expects those
as sibling checkouts (see Prerequisites). See
[`fab/docs/dogfood-w2s.md`](../../docs/dogfood-w2s.md) for the run report and
the concrete breakages + recommended hardening.

```
contract (fab) + per-workstream seed idea
  -> agentlib coding-generic agent on the LIVE Podium gateway
  -> agent does bounded synthetic W2S research, builds a Fab bundle in its
     Modal sandbox ($HOME/fab_out)
  -> HARVEST: the agent emits the bundle as one base64 blob from a single
     run_command; Podium's FabricBridge surfaces that stdout as a
     `tool_result` block on the WebSocket stream, captured mid-stream
     (single committer, no agent git creds, no RPC)
  -> orchestrator writes the bundle into the local Alexandria checkout
     (artifacts/<program>/<ws>/<run>/{manifest.json,artifact/,READY})
  -> fab `services.alexandria_ingester` ingests it into the w2s store
  -> `fab brief` / `fab attention` digest the batch for a human
```

## Result of the dogfood run

- Program `weak-to-strong-pilot`, contract `contract_w2s_generalization` v1,
  5 workstreams (ws_001..ws_005), each seeded with a distinct W2S idea.
- All 5 agents ran on the live gateway, produced artefact bundles harvested
  into Alexandria, and were ingested into the Fab store.
- `fab brief` digested the batch: 5 artifacts, **21 claims**, deterministic
  contract review (shared `weak-to-strong-generalization.md` reference),
  reference reconciliation, and an attention queue (4 workstreams flagged
  `limited`; ws_002 produced a thin artefact — itself a useful Fab signal).
- The artefacts themselves are in the Alexandria repo under
  `artifacts/weak-to-strong-pilot/` (separate PR).

## Layout

- `store/contracts/contract_w2s_generalization/v001.md` — the immutable W2S
  research contract (read-only once attached). The rest of `store/` is
  regenerable runtime state (git-ignored).
- `seeds.py` — the five distinct, literature-grounded seed ideas.
- `orchestrate.py` — the harness (fab-init / deploy / run / ingest / brief).
- `dist/`, `logs/`, `state.json`, runtime `store/*` — git-ignored.

## Prerequisites

- Multi-repo sibling checkouts at one parent dir: `agentlib/ agents/ fabric/
  podium/ ensemble/ alexandria/ fab/`. `orchestrate.py` auto-detects that
  parent (the dir containing `alexandria/`, `fab/`, `agents/`); override with
  `W2S_ROOT=/path/to/parent`. Each cloned repo needs a `.git/` marker dir so
  `agents deploy`'s repo probe resolves.
- Envs: `cd agents && uv sync`; `cd fab && uv sync`.
- Activated env creds: `PODIUM_GATEWAY`, `PODIUM_API_KEY`, `ENSEMBLE_URL`,
  `ENSEMBLE_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`.
- Run `orchestrate.py` with an interpreter that has `requests` +
  `websockets` installed.

## Usage

```bash
python3 fab/dogfood/w2s/orchestrate.py smoke            # one agent, e2e
python3 fab/dogfood/w2s/orchestrate.py fab-init         # store+sources+5 ws
python3 fab/dogfood/w2s/orchestrate.py deploy           # bundle+deploy+secrets
python3 fab/dogfood/w2s/orchestrate.py run --ws ws_003  # one ws (3 retries)
python3 fab/dogfood/w2s/orchestrate.py ingest           # Alexandria -> fab
python3 fab/dogfood/w2s/orchestrate.py brief            # digest
python3 fab/dogfood/w2s/orchestrate.py stop-all         # terminate instances
```

The five workstreams were run **sequentially** (`run --ws ...` per ws) to
avoid concurrency-induced provider 400s; each `run_one` retries up to 3×
with a fresh instance.

## Resolved unknowns

- **How do agents write to Alexandria?** They do not. The agent builds the
  bundle in its own Podium/Modal sandbox and emits it as base64 from one
  `run_command`; the orchestrator captures that `tool_result` from the WS
  stream and is the sole committer to Alexandria. (Podium's
  sandbox-capability RPC over `process_message` proved unreliable from an
  external client; the streamed `tool_result` channel is reliable.)
- **The contract.** None existed; `store/contracts/.../v001.md` is a new Fab
  contract distilled from the Alexandria W2S notes. The task prompt sent to
  agents is a *compact distillation* (embedding the full contract blew the
  model context limit).
- **Inference engine.** Default is **first-party Anthropic**
  (`AGENTLIB_FIRST_PARTY=1`, `ANTHROPIC_API_KEY`). Routing through Ensemble
  (`W2S_FIRST_PARTY=0`, `model.name` config override) is implemented but the
  **staging Ensemble *streaming* endpoint rejects the agent model id** even
  though non-streaming and the gateway config-validator accept
  `claude-sonnet-4-6` — an upstream agentlib↔staging-Ensemble streaming
  issue, kept selectable.
- **`agents deploy`** needs `iGentAI/fabric`; built `--local-deps` against
  sibling `fabric/` + `agentlib/`, `--source working`.
- **RunCommand truncation.** Token-dense base64 exceeds `RunCommand`'s
  default 20k-token output cap; the agent is told to call it with a large
  `max_tokens` tool arg so the bundle is not corrupted.

## Cost / safety bounding

The contract forbids LLM training, paid external inference, web search, and
large downloads; agents stay in synthetic / small-model regimes with a
per-attempt wall budget (`--max-seconds`, default 1800).