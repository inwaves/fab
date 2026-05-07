# Brief And Human Judgment

The brief is the human-facing view over a batch of external agent work. It is
not the whole product, and it is not a final report. It is the point in the Fab
protocol where many emitted packets and artefacts become inspectable by a scarce
human researcher.

The current CLI exposes this through `attention`, `show --brief`, and `judge`.
The product concept is:

```text
agent packets and artefact packages
-> batch comparison
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

The current `judge` command is a thin placeholder for this layer. It records
append-only human actions with rationale, and lifecycle actions still update
workstream status mechanically. The next pass should make human judgment attach
to artefacts and claims directly.

## Current Commands

List workstreams that need attention:

```bash
uv run fab attention
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
