# Evaluation methodology: Slide-level gold labels, fixed dev/test split, pre-registered Baseline

Every headline number (Recall@5, MRR, faithfulness, Refusal accuracy) must be reproducible by a script and defensible under questioning. Gold labels are therefore attached to Slides rather than Passages, so that changing passage-splitting never invalidates them. The Evaluation Set is split once, with a fixed seed, into a 100-pair Dev Split used for all tuning and a 50-pair Test Split run only for reported results. The Baseline was fixed before any tuning: one Slide per Passage, dense-only search with `BAAI/bge-small-en-v1.5`, top-5, no BM25 and no reranker. Improvements are measured against a configuration chosen in advance, not one picked afterwards.

Faithfulness Verdicts are the one exception to "produced by a script": they are judged in-session and committed as a file, and only their shares and agreement rate are recomputed by script (ADR-0002).

## Considered Options

- **Passage-level gold labels**: more precise, but every chunking change would need relabelling, and tuning the chunking is one of the measured improvement steps.
- **Tuning and reporting on all 150 pairs**: simpler, but it inflates the reported scores through overfitting to the evaluation questions.
- **Counting a hit whenever any Slide covered by a multi-Slide Passage is gold**: rejected, because wider windows would raise Recall@5 just by covering more Slides per result, not by retrieving better.

## Consequences

- **Anchor Slides:** every Passage has exactly one Anchor Slide. Multi-Slide windows attach neighbouring Slides' text as context only. Recall@5 and MRR rank Passages, collapse them to distinct Anchor Slides in rank order, and score the first 5 distinct Slides. A hit means one of those is a Gold Slide. This rule is the same for every Retrieval Configuration.
- **The chunking step:** "tuned chunking" compares four options:
  - one Slide per Passage (the Baseline);
  - the Anchor Slide plus 1 neighbour on each side as context (a 3-Slide window);
  - the Anchor Slide plus the previous Slide (a 2-Slide window);
  - one Slide per Passage, with long Slides split into several Passages that share the same Anchor Slide.
- **Several Gold Slides:** an Evaluation Pair may have more than one Gold Slide, for example when the same content appears in two Lectures.
- **Deduplication:** near-identical Slides within a Lecture (progressive builds) are deduplicated at ingest, keeping the most complete version. Duplicates across Lectures are kept. Gold Slides are labelled after ingest, so they only reference Slides that survived deduplication.
- **Unanswerable Questions:** they are excluded from Recall@5 and MRR, and reported as Refusal accuracy and false Refusal rate instead.
- **Question wording:** drafted questions must paraphrase rather than copy Slide wording, and hand-written questions deliberately use different vocabulary from the Slides. Otherwise BM25 is rewarded for exact word overlap that real students wouldn't produce.
