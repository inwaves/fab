# Research Contracts

Research contracts are immutable Markdown delegation briefs. They capture what a
human research manager wants a workstream to be about without requiring the
manager to pre-specify methods, assumptions, traps, or eval criteria before the
research has happened.

## Storage Convention

Contracts live under the registry store:

```text
.fab/contracts/contract_001/v001.md
.fab/contracts/contract_001/v002.md
```

Contract ids must be simple path-safe ids such as `contract_001`:
letters, numbers, underscores, and hyphens only.

Once a version is attached to a workstream, do not edit it. Create a new version
instead. The registry makes attached versions read-only as a guardrail, but the
real invariant is conceptual: a workstream points at the exact contract version
it was delegated under.

The workstream stores only the pointer:

```json
{
  "contract": {
    "id": "contract_001",
    "version": 1
  }
}
```

## Human Workflow

1. Copy `docs/templates/research-contract.md` somewhere under version control.
   This repository keeps contract sources in `contracts/<contract_id>/vNNN.md`,
   since the registry store itself (`.fab/`) is not committed.
2. Fill out the Markdown directly.
3. Register the version, which copies it into the registry path and locks it
   read-only:

```bash
uv run fab contract add contract_001 --version 1 --from contracts/contract_001/v001.md
```

4. Attach the version to a workstream, or pass `--contract-id` and
   `--contract-version` to `fab create`:

```bash
uv run fab attach-contract ws_001 --contract-id contract_001 --version 1
```

Attachment validates that the version file exists and locks it read-only.
`fab contract show contract_001 --version 1` prints the registered text.

There is intentionally no contract authoring CLI: `contract add` registers a
file you wrote, it does not draft one. Later, a coordinator agent or product UI
can help draft these files, but the durable primitive is the versioned Markdown
file.

## Contract Philosophy

The contract should be brief enough that a busy research manager can actually
write it. The agent executing the workstream is expected to investigate missing
background, surface hidden assumptions, propose methods, and report discovered
traps.

The contract should include:

- the research question;
- why it matters;
- a free-form brief;
- desired output shape;
- optional programme shape;
- optional prior knowledge and artefact references;
- optional attention boundaries;
- optional context links.

Programme shape is about research coverage, not execution scheduling. It can
say, for example, that the external agent system should instantiate a broad
exploratory batch, include independent replications, include critique
workstreams, or separate exploration from validation.

How Fab should represent programme shape and workstream fan-out is a later
design question. It should not become another MVP component before the basic
contract, artefact, brief, and judgment loop is useful.

The contract should not include:

- live state;
- current hypothesis;
- current plan;
- latest results;
- blockers;
- current rationale;
- agent runtime permissions;
- exhaustive lists of allowed methods or forbidden shortcuts.

Those belong in packets, live state, artefact provenance, human judgment, or the
external execution system.
