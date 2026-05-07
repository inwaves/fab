# Literature index: over-refusal / false-positive benchmarks

External research artifact for `ws_001` (contract `contract_pilot_a3_false_positive` v1).

Author: remote-agent-maestro
Date: 2026-05-07

## Why this exists

The seeded ws_001 baseline scan refers to `pilot/data/benign_refusal_adjacent_v1.jsonl`
without comparators. This makes any reported false-positive rate hard to
interpret. This index lists public benchmarks aimed at the same construct
(refusal of benign / pseudo-harmful prompts), with arxiv pointers and a
leakage-risk note for each.

The leakage-risk note is the load-bearing column. The contract's attention
boundaries say to stop and report if a result depends on private eval leakage;
the dual risk is *public* eval leakage, where the benchmark items have been
plausibly absorbed into the safety-finetuning data of widely deployed models
(including, possibly, the A3-style pilot model). Public eval leakage produces
results that look like generalization but are partly memorization.

## Verified entries

### XSTest

- arXiv: 2308.01263
- venue: NAACL 2024
- authors: Röttger, Kirk, Vidgen, Attanasio, Bianchi, Hovy
- size: 250 safe prompts (10 prompt types) + 200 unsafe contrasts
- what it measures: exaggerated safety — false refusals of safe prompts that
  superficially resemble unsafe ones via lexical overlap or sensitive topics
- public: yes; HF dataset, GitHub repo
- leakage risk: high. XSTest items are short, distinctive, and have circulated
  on HF since 2023. Many open safety-tuned model checkpoints likely saw at
  least the unsafe contrasts during instruction or RLHF mixes. Do not use as
  a primary FP-reduction metric for any model that may have ingested it.

### OR-Bench (Over-Refusal Benchmark)

- arXiv: 2405.20947
- venue: ICLR 2025
- authors: Cui, Chiang, Stoica, Hsieh
- size: 80,000 safe prompts; 1,000-item hard subset; 600 toxic controls;
  10-category taxonomy (harassment, deception, violence, ...)
- public: yes; HF, GitHub, leaderboard
- leakage risk: medium-to-high for the public 1k hard subset by 2026; lower
  for the full 80k pool because of size. Treat the hard subset as known to
  the field.

### PHTest

- arXiv: 2409.00598
- year: 2024
- size: 3,260 prompts (2,069 harmless + 1,191 controversial)
- what it measures: false-refusal rate on pseudo-harmful prompts that look
  benign on plain reading; covers refusal triggered by rule violations or
  intent misinterpretation rather than sensitive lexical content
- public: yes; project site `phtest-frf.github.io`
- leakage risk: medium. Younger than XSTest and OR-Bench. Less time for
  ingestion. Still, public from late 2024.

### SORRY-Bench

- arXiv: 2406.14598
- venue: ICLR 2025
- size: 440 unsafe instructions; 7k human safety judgments released March 2025
- what it measures: refusal behavior across a fine-grained 44-topic taxonomy.
  Note: this is more aimed at characterizing refusal than at over-refusal,
  and its primary use here is as a complementary reference, not a direct FP
  benchmark.
- public: yes; GitHub, HF
- leakage risk: medium. Public since mid-2024.

### OKTest

- referenced in PHTest as a smaller prior dataset for false refusals
- not separately verified here; arxiv id, year, authors, size could not be
  confirmed from open sources during this research session
- leakage risk: unknown
- recommendation: do not cite OKTest from this index until the primary source
  is confirmed by a human researcher.

### WildJailbreak (WJ)

- referenced as a 262k adversarial dataset used as a query pool
- specifically aimed at jailbreak coverage rather than benign-refusal FP, so
  treat it as related rather than direct
- public: yes; HF
- leakage risk: high for any model with broad public-data ingestion

### HEx-PHI

- HF: `LLM-Tuning-Safety/HEx-PHI`
- size: 330 harmful instructions across 11 prohibited categories
- direction: harmful-side, not benign-side. Useful only as a target-failure
  detection check, not as an over-refusal metric. Listed here so a reader
  does not confuse it with an FP benchmark.

## Recommended use for ws_001

For the planned 30-NN labeling pass on `benign_refusal_adjacent_v1.jsonl`:

1. **Do not** import any of the above benchmarks directly into the labeling
   pool of ws_001. The labeling pool should remain the pilot's own
   distribution to keep the cluster claim honest.

2. **Do** run a second, separate eval pass that *also* scores the pilot
   model on a small held-out slice of XSTest unsafe contrasts and OR-Bench
   hard-subset items. Treat the result as orientation, not as a clean
   benchmark — the leakage notes apply.

3. **Do** log overlap between `benign_refusal_adjacent_v1.jsonl` and the
   public benchmarks listed above. Any item that is a paraphrase or near-
   duplicate of an XSTest or OR-Bench prompt is leakage-suspect for any
   model trained on broad open data, and should be excluded from the
   primary FP-rate statistic in the pre-registered labeling plan.

4. **Do not** treat A3 finetuning gains over public benchmarks as evidence of
   real FP reduction without an independent held-out distribution. This is
   the public-metric shortcutting pattern the contract asks us to flag.

## Limits of this index

- `OKTest` is unverified.
- I have not searched for benchmarks published in 2025 that I do not already
  know about. The contract gives a 2026 setting; readers should expect at
  least one further FP benchmark to have appeared between PHTest and now.
- Leakage-risk levels are qualitative. They are not the result of an
  intersection scan against any model's training data — that scan, if any,
  would be the kind of work a follow-up workstream should do.
- The KB references in the original contract
  (`papers/a3-an-automated-alignment-agent-for-safety-finetun.md`,
  `papers/automated-weak-to-strong-researcher.md`,
  `papers/the-last-human-written-paper-agent-native-research-artifacts.md`)
  are not present in this clone of `inwaves/fab`. They presumably live in
  `inwaves/kb`. Cross-referencing them is deferred until the kb substrate is
  attached.