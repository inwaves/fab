# Pilot Fixture

The pilot fixture simulates a small black-box-agent research batch without
building an execution harness. It is meant to test the first Fab protocol loop:

```text
contract
-> workstreams
-> artefact packages
-> brief
-> human judgment
```

## What It Creates

Run:

```bash
uv run fab --store /tmp/fab-pilot pilot-fixture
```

The command seeds an empty registry with:

- one immutable research contract;
- five workstreams in the `safety-finetuning-pilot` programme;
- simulated packets from external agents;
- structured artefact packages with claims, evidence, provenance,
  uncertainty, reproduction notes, and follow-up;
- mixed attention states:
  - one clean workstream;
  - one blocked workstream;
  - one flagged possible-shortcut workstream;
  - one deviated OOD-transfer workstream;
  - one unscoped workstream with no contract or packets.

It refuses to run in a non-empty registry so it does not mingle sample data with
real work.

## How To Inspect It

Start with the attention queue:

```bash
uv run fab --store /tmp/fab-pilot attention
```

Include the clean workstream too:

```bash
uv run fab --store /tmp/fab-pilot attention --all
```

Read the pilot brief:

```bash
uv run fab --store /tmp/fab-pilot brief --program safety-finetuning-pilot
```

Inspect a flagged workstream:

```bash
uv run fab --store /tmp/fab-pilot show ws_003 --brief
```

Record a human judgment:

```bash
uv run fab --store /tmp/fab-pilot judge ws_003 \
  --target-type claim \
  --target-id art_001/claim_filter_tradeoff \
  --action needs-replication \
  --rationale "Promising but currently depends on one public eval and may be a shortcut"
```

## What We Are Testing

The fixture is intentionally small. It is not a benchmark for agents. It tests
whether the protocol objects carry the right information:

- can the human see which outputs need attention?
- does the inspection view recover enough context from contract, packets, and
  artefacts?
- do artefact/provenance refs make claims more inspectable?
- can a human judgment attach to a specific claim without pretending the whole
  workstream is accepted or rejected?
- does the fixture show where brief comparison and loop closure need to improve
  next?
