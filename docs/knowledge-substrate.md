# Knowledge Substrate Interface

Fab needs prior knowledge, but it should not impose an ontology on the
substrate. For the MVP, the substrate is `inwaves/Alexandria`.

Alexandria is the public boundary Fab can assume: agents write artifact bundles
there, humans can write notes there, and Fab can read from it or write
transformed outputs back to it. It has the practical qualities we wanted from a
research substrate without binding public Fab to a private repository.

## Decision

The MVP should be lighter than a reference ontology.

The researcher writes the research contract in natural language. If a specific
Alexandria item matters, the researcher should mention it directly in the
contract:

```md
Use the A3 paper note in `alexandria://papers/a3-an-automated-alignment-agent-for-safety-finetun.md`
as background for the safety-finetuning loop. Pay particular attention to the
false-positive objective and the risk that false-positive reduction hides target
failure regressions.
```

Fab should not require the researcher to fill out `role`, `why`, or any other
structured reference fields before the contract is useful.

## Markdown Shape

For the basic Alexandria Markdown adapter, Fab should expect almost nothing:

```text
some/path.md
```

Useful optional frontmatter:

```yaml
---
title: "A3: An Automated Alignment Agent for Safety Finetuning"
url: "https://alignment.anthropic.com/2026/automated-alignment-agent/"
created: 2026-04-04
---
```

Fab may also use the first H1 as a title. It should not require tags, authors,
engaged fields, insightful fields, backlinks, paper categories, or local
Alexandria conventions.

## What Fab Records

Fab records how a contract or run resolved prior context. This bookkeeping lives
in Fab's registry and can later be written back to Alexandria if useful. It does
not need to live in the Alexandria document itself.

For an explicit reference in a contract, Fab can record a resolution snapshot:

```json
{
  "contract": {
    "id": "contract_pilot_a3_false_positive",
    "version": 1
  },
  "mention": "alexandria://papers/a3-an-automated-alignment-agent-for-safety-finetun.md",
  "resolved": {
    "source": "alexandria",
    "uri": "alexandria://papers/a3-an-automated-alignment-agent-for-safety-finetun.md",
    "title": "A3: An Automated Alignment Agent for Safety Finetuning",
    "content_hash": "sha256:...",
    "git_commit": "1a2b3c..."
  }
}
```

This says: when Fab checked or built context for this contract version, this is
the document and version it resolved.

The contract text remains the place where the researcher says how to use that
document. Fab does not need to duplicate that instruction as a structured
`role` or `why` field.

## Natural Language First

The contract can mention prior context in ordinary prose:

```md
The A3 safety-finetuning note is the motivating example. Treat it as background,
not as a source of truth. The Last Human-Written Paper is relevant for artifact
shape. The automated weak-to-strong researcher result is useful evidence that
bounded, outcome-gradable alignment work can be accelerated by agents.
```

An agent with Alexandria access may search or grep Alexandria to find those
files. That is acceptable for the MVP. If the researcher needs exact context,
they should write an exact URI or path in the contract.

Fab's job is not to infer a perfect context graph from prose. Fab's job is to:

- preserve the contract text;
- resolve explicit references when present;
- warn about unresolved explicit references;
- record which references were actually used by the agent;
- surface mismatches to the human reviewer.

## Agent-Used References

Run manifests should report what the agent actually used:

```json
{
  "used_refs": [
    "alexandria://papers/a3-an-automated-alignment-agent-for-safety-finetun.md"
  ]
}
```

This closes the loop without requiring the researcher to pre-structure every
reference. The brief can then show:

```text
Contract mentioned A3. Agent used alexandria://papers/a3...
Contract mentioned automated weak-to-strong researcher. Agent did not cite a matching ref.
Agent used alexandria://papers/or-bench... which was not in the contract.
```

That is more useful than pretending Fab knows the intended role of every source.

## Commands

Initial commands should stay small:

```bash
uv run fab sources add alexandria ../alexandria --uri-prefix alexandria://
uv run fab refs check --scope contract:contract_pilot_a3_false_positive/v1
uv run fab context show ws_001
```

`refs check` should not infer a full bibliography. It should:

- scan the contract and live references for explicit `alexandria://`, `fab://`,
  `s3://`, local Markdown, and HTTP references;
- resolve the ones it can;
- record title, content hash, and revision if available;
- warn about unresolved explicit references;
- warn if a configured source is dirty or unpinned;
- warn if a referenced Fab claim is marked `needs-replication`,
  `do-not-propagate`, or similar.

`context show` should show the contract plus resolved explicit references. It
can also show agent-used references after ingest.

## Alexandria Layout

The only layout Fab should assume for the first Alexandria adapter is the
incoming artifact area:

```text
artifacts/<program>/<workstream_id>/<run_id>/
  manifest.json
  artifact/
  READY
```

Other Alexandria folders can evolve separately. A useful split is:

- raw agent artifact bundles;
- Fab-transformed findings or attention notes;
- human-maintained research notes.

Fab should not require that split before ingest works.

## Writing Back

If an agent thinks an Alexandria note should change, it should say that in the
report or `next`. Fab may later write transformed findings or attention notes to
Alexandria after a human judgment.

## Non-Goals

The knowledge substrate interface is not:

- a general note app;
- a paper-note manager;
- a citation graph as the core data model;
- an ontology of all research concepts;
- a requirement to classify every reference by role;
- a guarantee that agent suggestions are true;
- a requirement that deployments use a private repository.

The cheapest useful interface is: natural-language contracts, optional explicit
URIs, resolution snapshots, agent-used references, Alexandria artifact ingest,
and human-approved write-back.
