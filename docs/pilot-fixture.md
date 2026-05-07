# Pilot Fixture

The pilot fixture simulates a small black-box-agent research batch without
building an execution harness. It is meant to test the first Fab protocol loop:

```text
contract
-> workstreams
-> artefact pointers
-> attention queue
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
- structured artefact/provenance refs;
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

Inspect a flagged workstream:

```bash
uv run fab --store /tmp/fab-pilot show ws_003 --brief
```

Record a human judgment:

```bash
uv run fab --store /tmp/fab-pilot judge ws_003 \
  --action replicate \
  --rationale "Promising but currently depends on one public eval and may be a shortcut"
```

## What We Are Testing

The fixture is intentionally small. It is not a benchmark for agents. It tests
whether the protocol objects carry the right information:

- can the human see which outputs need attention?
- does the inspection view recover enough context from contract, packets, and
  artefacts?
- do artefact/provenance refs make claims more inspectable?
- does the fixture show where batch comparison and richer artefact packages are
  needed next?
