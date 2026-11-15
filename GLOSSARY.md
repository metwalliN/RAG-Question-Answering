# Course Q&A Assistant

Answers students' questions about university course materials, grounding every answer in cited passages from those materials.

## Language

**Course Material**:
The documents a course provides (lecture slides, notes, handouts) that the assistant answers from. It is the only source of truth for answers.
_Avoid_: Corpus, knowledge base, docs

**Lecture**:
A single document of Course Material, typically one slide deck.
_Avoid_: File, PDF, document

**Slide**:
One page of a Lecture; the smallest location a student can be pointed to.
_Avoid_: Page

**Duplicate Slide**:
A Slide near-identical to another Slide in the same Lecture, such as one step of a progressive build; only the most complete version is kept.
_Avoid_: Repeated page, slide build

**Passage**:
A span of Lecture text that the assistant retrieves and shows as evidence for an answer. Every Passage belongs to exactly one Anchor Slide.
_Avoid_: Chunk, snippet, context

**Anchor Slide**:
The single Slide a Passage belongs to and is cited as; any neighbouring Slides' text in the Passage is context only.
_Avoid_: Source slide, primary slide

**Citation**:
A reference attached to an answer that points to the Lecture and Slide a claim came from, with the supporting Passage available to view.
_Avoid_: Source, reference, link

**Evaluation Set**:
A fixed, reviewed collection of Evaluation Pairs used to measure how well the assistant retrieves and answers.
_Avoid_: Test set, benchmark, golden set

**Evaluation Pair**:
One question together with its reference answer, belonging to the Evaluation Set.
_Avoid_: QA pair, test case, sample

**Gold Slide**:
A Slide labelled as containing the answer to an Evaluation Pair's question; an Evaluation Pair may have several. Retrieving a Passage anchored to it counts as a hit.
_Avoid_: Ground truth, relevant document, label

**Dev Split**:
The part of the Evaluation Set used for tuning Retrieval Configurations.
_Avoid_: Train set, validation set

**Test Split**:
The held-out part of the Evaluation Set, run only to produce reported results.
_Avoid_: Holdout, eval set

**Retrieval Configuration**:
A named, fixed combination of passage-splitting, search and reranking settings whose results can be measured and compared.
_Avoid_: Pipeline, setup, experiment

**Baseline**:
The simplest Retrieval Configuration, fixed in advance, that every improvement is measured against.
_Avoid_: Default, v0

**Refusal**:
A response in which the assistant states that the Course Material does not answer the question, instead of answering.
_Avoid_: Fallback, "I don't know" answer, abstention

**False Refusal**:
A Refusal given to a question the Course Material does answer.
_Avoid_: Over-refusal, false negative

**Unanswerable Question**:
An Evaluation Pair whose question the Course Material does not answer; the correct response is to say so.
_Avoid_: Negative sample, out-of-scope question

**Faithfulness Verdict**:
A judgement of whether an answer is Supported, Partially Supported or Unsupported by its own Citations.
_Avoid_: Groundedness score, hallucination rate
