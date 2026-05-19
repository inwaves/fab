# Dogfood: Weak-to-Strong Generalization Pilot

A real end-to-end run of the MVP protocol loop on a fresh contract with five
externally-executed agents. Harness, seeds, and the contract live in
[`dogfood/w2s/`](../dogfood/w2s/README.md).

## Setup

- **Contract:** `contract_w2s_generalization` v1 (authored from the
  Alexandria W2S notes), program `weak-to-strong-pilot`, 5 workstreams each
  seeded with a distinct, literature-grounded idea (PGR/imitation regime map,
  auxiliary confidence loss, bootstrapping through intermediate capacities,
  Goodhart/held-out-leakage audit, bias-variance early-warning signals).
- **Execution:** `igentai/agents` `coding.generic.v2` deployed to the live
  Podium staging gateway; inference via first-party Anthropic
  (`claude-sonnet-4-6`).
- **Egress:** agents never touch Alexandria. Each builds a Fab bundle in its
  Podium/Modal sandbox and emits it as base64 from one `run_command`;
  FabricBridge surfaces that stdout as a `tool_result` block on the WS
  stream, which the harness captures mid-stream and commits to the local
  Alexandria checkout (single committer). `services.alexandria_ingester`
  then ingests into a dedicated store.

## Result (does the loop produce a useful human-facing digest?)

`fab brief --program weak-to-strong-pilot`: 5 workstreams, 5 artifacts,
**21 claims**, deterministic `contract_review` (detected the shared
`weak-to-strong-generalization.md` reference across workstreams), reference
reconciliation (explicit vs used `alexandria://` refs), and an attention
queue flagging 4 workstreams `limited` from honestly-recorded limitations.
One workstream (ws_002) produced a thin artefact (no `artifact/` subtree);
Fab surfaced it rather than hiding it — a useful signal, exactly the kind of
triage the brief/attention loop exists for. The protocol loop
(contract → workstreams → remote ingest → artefact packages → brief →
attention) held end to end. Artefacts are in `inwaves/alexandria` under
`artifacts/weak-to-strong-pilot/`.

## What broke, and recommended hardening

These are concrete findings for the "tighten what breaks" roadmap item.
Several are upstream (Podium / agentlib / Ensemble), not Fab itself, but they
directly shape what a Fab-facing execution platform must guarantee.

1. **Agent→substrate egress is the crux.** Podium's sandbox-capability RPC
   (`igent.evals.sandbox.request` over `process_message`) was unreliable
   from an external client (no response while the agent turn was busy). The
   reliable channel was the agent emitting the bundle as base64 in one
   `run_command` whose stdout returns as a `tool_result` block. *Fab
   implication:* the remote-ingest design should specify a robust,
   turn-state-independent egress (durable bundle write the platform
   guarantees), not depend on live RPC.
2. **Bundle-size vs tool output cap.** agentlib `RunCommand` truncates
   stdout above ~20k tokens; token-dense base64 corrupts silently. Mitigated
   by instructing a large `max_tokens` tool arg + a compact bundle. *Fab
   implication:* manifests/bundles should be size-bounded or chunked at the
   protocol boundary.
3. **Context-limit 400.** Embedding the full contract in the agent prompt
   exceeded the model context window (`invalid_request_error`). Fixed with a
   compact contract distillation. *Fab implication:* contracts are
   natural-language first, but the execution platform must summarize/segment
   them for the model, not pass them whole.
4. **Inference routing.** Staging Ensemble's *streaming* endpoint rejected
   the model id that non-streaming and the gateway config-validator both
   accept (`claude-sonnet-4-6`). First-party Anthropic was the working path.
   Upstream agentlib↔Ensemble issue; kept selectable via `W2S_FIRST_PARTY`.
5. **Deploy ergonomics.** `agents deploy` needs an `iGentAI/fabric` checkout
   and a git repo probe; built via `--local-deps --source working` with
   `.git` marker dirs.
6. **Orphaned instances.** Podium gateway `DELETE /api/v1/instances/{id}`
   returned 200/000 but did not reap some instances even after the agent had
   shut down (`shutdown` tag present, sandbox channel closed). One instance
   (`w2s-ws_001-...`) remained a stale registry record ~17h later, not
   client-deletable. *Operational:* requires coordinator-side cleanup; a Fab
   ingester operating against such a platform must not assume instance
   teardown is synchronous or guaranteed.

## Takeaway

The Fab protocol objects (contract, workstreams, remote ingest, artefact
packages, brief, attention, deterministic contract review, references) were
sufficient to make a real 5-agent batch human-reviewable. The friction was
entirely in the *execution/egress* layer outside Fab — which validates Fab's
scoping decision (own the protocol, not the platform) while showing the
remote-ingest contract needs a hardened, turn-state-independent egress and
size discipline.