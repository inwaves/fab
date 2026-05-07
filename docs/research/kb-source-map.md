# KB Source Map

This repo now carries the core product context, but the broader research graph
still lives in `/Users/inwaves/ghq/github.com/inwaves/kb`. Use this map when
pulling more context across.

## Imported Here

- `kb/research/alignment-factory/README.md` -> `docs/research/alignment-factory.md`
  - Source state: latest working tree version, including uncommitted edits.
  - Why it matters: defines the product target, workstream supervision,
    consolidation, promotion, and failure modes.

## Strategic Context

- `kb/research/alignment-via-ai-assistance.md`
  - The critique of the automated alignment researcher thesis.
  - Key takeaway: the research production system becomes the object of study
    once AI assistance dominates alignment work.
- `kb/research/mitigations-to-automated-alignment/README.md`
  - The bridge question: whether containment, monitoring, auditing, research
    epistemics, and governance can safely carry us to useful AI-assisted
    alignment research.
  - Key takeaway: AI-assisted research epistemics is the least developed crux,
    and Alignment Fab is directly aimed at it.

## Adjacent Research Directions

- `kb/research/ai-control/README.md`
  - Use for control-protocol experiments, trusted/untrusted model patterns,
    synchronous review, collusion concerns, and CoT monitoring dependence.
- `kb/research/alignment-auditing/README.md`
  - Use for audit-agent lessons, especially the tool-to-agent gap and
    hypothesis-formation failures.
- `kb/research/harness-search/README.md`
  - Use when workstream contracts need to record scaffold or harness details as
    a safety-relevant experimental variable.
- `kb/research/frontier-relative-monitorability/README.md`
  - A candidate pilot area. It already has an experimental design and a
    concrete monitorability research program.
- `kb/research/cot-faithfulness/README.md`
  - Background for CoT monitorability and faithfulness questions.
- `kb/research/alignment-faking/README.md`
  - Threat model context for strategic compliance and hidden objectives.
- `kb/research/benchmark-landscape/README.md`
  - Useful when choosing pilot benchmarks and avoiding low-signal evals.
- `kb/research/personas/README.md`
  - Background for persona/vector/behavioral-generalization monitoring work.
- `kb/research/recursive-self-improvement/README.md`
  - Broader automated AI R&D context; useful for capability-externality review.

## Paper Notes To Pull When Needed

- `kb/papers/automated-weak-to-strong-researcher.md`
  - Evidence that agents can make real progress on a bounded, outcome-gradable
    alignment task, and a warning that eval design becomes more important.
- `kb/papers/a3-an-automated-alignment-agent-for-safety-finetun.md`
  - Example of an automated safety-finetuning loop and a candidate pilot domain.
- `kb/papers/automated-researchers-can-subtly-sandbag.md`
  - Threat model for automated research labor that appears useful while
    distorting progress.
- `kb/papers/trustworthy-agents-in-practice.md`
  - Operational trust and agent-supervision context.
- `kb/papers/ai-control-improving-safety-despite-intentional-sub.md`
  - Foundational AI control paper.
- `kb/papers/when-can-we-trust-untrusted-monitoring.md`
  - Collusion and untrusted-monitoring safety-case context.
- `kb/papers/shade-arena-evaluating-sabotage-and-monitoring-in.md`
  - Multi-step sabotage and monitoring benchmark; useful for agentic control
    pilot design.
- `kb/papers/monitorbench-a-comprehensive-benchmark-for-chain.md`
  - Monitorability benchmark behind the frontier-relative monitorability line.
- `kb/papers/building-and-evaluating-alignment-auditing-agents.md`
  - Petri-style auditing agents.
- `kb/papers/auditbench-evaluating-alignment-auditing-technique.md`
  - Tool-to-agent gap evidence.
- `kb/papers/natural-emergent-misalignment-from-reward-hacking.md`
  - Threat model for broad behavioral shifts from narrow training.
- `kb/papers/alignment-faking-in-large-language-models.md`
  - Alignment-faking model-organism evidence.

## Earlier Alignment Factory Draft

The committed KB version at commit `4a72d02` framed the factory more as an
evidence pipeline. It emphasized:

- evidence packages before narrative reports;
- "no research claim should be certified by the same optimization process that
  produced it";
- proposal, implementation, critique, replication, judge, and curator role
  separations;
- public/dev, private validation, sealed final, transfer, and adversarial eval
  stages;
- preservation of failed hypotheses, failed hyperparameters, shortcuts, bugs,
  negative transfer, eval patches, human decisions, and later reversals.

Those ideas are not in the current MVP code yet, but they should shape the
contract, artifact, consolidation, and promotion layers.
