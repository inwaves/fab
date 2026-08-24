# Brief And Human Judgment

The brief is the human-facing view over a batch of external agent work. It is
not the whole product, and it is not a final report. It is the point in the Fab
protocol where many emitted packets and artefacts become inspectable by a scarce
human researcher.

The current CLI exposes this through `brief`, `attention`, `show --brief`, and
`judge`.
The product concept is:

```text
agent packets and artefact packages
-> concise brief
-> human judgment
-> revised contract or programme state
```

## What A Brief Should Do

A useful brief should answer:

- what the contract asked for;
- which workstreams ran under it;
- what each workstream tried;
- what artefacts and code support the reported results;
- where independent work converged;
- where outputs contradict each other;
- which assumptions, evals, datasets, prompts, or methods are shared;
- which results look shortcutty, fragile, unsupported, or local-only;
- which gaps remain untested;
- what deserves the researcher's attention.

The brief should allocate attention. It should not ask the human to read every
packet in order.

## Deterministic Contract Review

The current brief includes a deterministic `contract_review` section. This is a
substrate for comparison, not a replacement for a researcher's synthesis.

It currently rolls up:

- artifact statuses across the selected contract/program scope;
- repeated claims by normalized exact text;
- shared limitations;
- shared `used_refs`;
- claims and artifacts without human judgment;
- targets already marked `needs-replication`, `needs-critique`,
  `do-not-propagate`, `safe-as-context`, or `trusted-local`.

The pass is intentionally humble. It does not infer semantic agreement, deep
contradiction, or importance. If two artifacts phrase the same claim
differently, this deterministic pass may not group them. If two artifacts
conflict implicitly, this pass may not see the conflict.

The deferred design choice is a reviewer/comparison agent that reads the
contract-scoped corpus and emits its own synthesis artifact. That agent should
make the human's reading problem smaller, but its output should still be
ingested, inspectable, and judged like any other artifact.

## Human Judgment

Often the agent that produced the work is gone. Human judgment attaches to the
research output and feeds the next contract, batch, or programme state.

Useful judgment states include:

- trusted as local evidence;
- rejected;
- interesting but unsupported;
- needs replication;
- needs critique;
- escalate to human/manual review;
- do not propagate;
- safe to reference in a later contract;
- candidate for later promotion.

The current `judge` command records append-only human actions with rationale.
Judgments can target a workstream, artifact, or claim. Lifecycle actions still
update workstream status only when the judgment target is the workstream.

### Lifecycle transitions

The lifecycle actions map to statuses: `continue` -> `running`, `pause` ->
`paused`, `stop` -> `stopped`, `complete` -> `completed`, `quarantine` ->
`quarantined`. Moves are checked against a small transition table:

| From          | Allowed to                                    |
|---------------|-----------------------------------------------|
| `planned`     | `running`, `paused`, `stopped`, `quarantined` |
| `running`     | `paused`, `stopped`, `completed`, `quarantined` |
| `paused`      | `running`, `stopped`, `completed`, `quarantined` |
| `quarantined` | `running`, `paused`, `stopped`                |
| `stopped`     | none (terminal)                               |
| `completed`   | none (terminal)                               |

Repeating the current status is always allowed, so a second `continue` on a
running workstream is a no-op for status and still records the judgment. A
judgment that would make a disallowed move is rejected before anything is
written. To correct a mistaken terminal status, use the explicit status command
with `--force`:

```bash
uv run fab status ws_001 running --force
```

Judgment target ids:

- workstream: `ws_001`
- artifact: `art_001` or `ws_001/art_001`
- claim: `claim_001`, `art_001/claim_001`, or `ws_001/art_001/claim_001`

## Current Commands

List workstreams that need attention:

```bash
uv run fab attention
```

Produce the current human-facing brief:

```bash
uv run fab brief
uv run fab brief --program safety-finetuning-pilot
uv run fab brief --contract-id contract_pilot_a3_false_positive
```

Filter by reason:

```bash
uv run fab attention --reason flagged
uv run fab attention --reason stale
uv run fab attention --reason no_contract
```

Show the current brief-shaped state for one workstream:

```bash
uv run fab show ws_001 --brief
```

Record a human judgment:

```bash
uv run fab judge ws_001 \
  --action replicate \
  --rationale "The result is promising but depends on one public eval and one scaffold"
```

Record judgment on a specific claim:

```bash
uv run fab judge ws_003 \
  --target-type claim \
  --target-id art_001/claim_filter_tradeoff \
  --action needs-replication \
  --rationale "Tradeoff may be a shortcut; do not carry forward before replication"
```

Mark a claim as usable in the next context:

```bash
uv run fab judge ws_001 \
  --target-type claim \
  --target-id art_001/claim_ambiguous_refusal_cluster \
  --action safe-as-context \
  --rationale "Safe to cite as a candidate cluster if the missing labels caveat is preserved"
```

These commands support JSON output with `--json`.

## Current Attention Reasons

- `no_contract`: the workstream is not attached to a contract.
- `missing_contract_file`: the workstream points at a contract version file that
  is missing.
- `invalid_contract_pointer`: the stored contract pointer is not a safe path id.
- `no_state_packet`: no agent or human update has been recorded yet.
- `missing_rationale`: live state has no current rationale.
- `blocked`: live state has blockers.
- `flagged`: live state has flags.
- `deviated`: live state has deviations.
- `review_due`: the next attention date is due.
- `stale`: last state update is older than the stale threshold.
- `paused`: the workstream is paused and awaiting attention.
- `quarantined`: the workstream is quarantined and awaiting attention.
- `invalid_review_due_at`: the attention due date cannot be parsed.
- `invalid_last_state_update_at`: the last state update timestamp cannot be
  parsed.

By default, stale means more than 7 days since the last state update. Override it
with `--stale-days`.
