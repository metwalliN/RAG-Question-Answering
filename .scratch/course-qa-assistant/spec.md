# Spec: Course Q&A Assistant

Status: ready-for-agent

## Problem Statement

A student studying from a university course's slide decks has a question, such as "what's the difference between bias and variance?" or "when do we use a paired t-test?". Finding the answer means scrolling through dozens of Lectures and hundreds of Slides, guessing at keywords that might not match how the Slides phrase things. General chatbots answer fluently but can't be trusted: they don't know what this course actually taught, and they can't point to where an answer came from.

The developer also wants a portfolio project whose claims hold up under questioning. Every headline number (Recall@5, MRR, faithfulness, latency) has to be produced by a script anyone can re-run, against a Baseline fixed in advance, on questions that weren't used for tuning.

## Solution

A question-answering assistant over the course's Course Material:
- **Asking:** a student types a question into a simple web interface.
- **Answering:** they get a short answer whose every claim carries a Citation ("Lecture 4 — Slide 12"). Clicking the Citation shows the supporting Passage.
- **Refusing:** when the Course Material doesn't answer the question, the assistant gives a Refusal instead of guessing.

Behind it is a measured retrieval pipeline. It combines keyword (BM25) and dense search, then reranks with a cross-encoder.

An evaluation harness scores each Retrieval Configuration on an Evaluation Set of about 227 pairs (197 answerable, 30 Unanswerable), split into a Dev Split for tuning and a held-out Test Split for reported results:
- **Configurations scored:** the Baseline, then tuned chunking, then hybrid retrieval, then reranking.
- **Reported:** Recall@5, MRR, Refusal accuracy, false Refusal rate, Faithfulness Verdicts and latency.

The whole system runs locally with one `docker compose` command.

## User Stories

### Asking and answering

1. As a student, I want to type a question in plain English and get an answer, so that I don't have to search through slide decks myself.
2. As a student, I want the answer to be short (a few sentences), so that I can read it quickly while studying.
3. As a student, I want every claim in the answer to carry a numbered Citation marker, so that I know which part of the answer came from where.
4. As a student, I want each Citation to name the Lecture and Slide, so that I can open the original slide deck at the right place.
5. As a student, I want to click a Citation and see the Passage it refers to, so that I can verify the answer without leaving the page.
6. As a student, I want the assistant to give a Refusal when the Course Material doesn't cover my question, so that I'm never misled by an invented answer.
7. As a student, I want a Refusal to be clearly worded and visually distinct from an answer, so that I don't mistake it for one.
8. As a student, I want answers to arrive in about two seconds, so that the tool feels responsive.
9. As a student, I want the assistant to understand my question even when I phrase it differently from the Slides, so that I don't have to guess the lecturer's exact wording.
10. As a student, I want the answer to use only the Course Material and not outside knowledge, so that it matches what will be examined.
11. As a student, I want Citations never to point at a Slide that wasn't actually used, so that every Citation I click is relevant.

### Retrieval transparency (demo and debugging)

12. As a developer, I want an expandable "Retrieval details" panel under each answer, so that I can see which Passages were retrieved.
13. As a developer, I want that panel to show each Passage's BM25, dense and rerank scores, so that I can explain why a Passage ranked where it did.
14. As a developer, I want each response to include a timing breakdown (retrieve, rerank, generate, total), so that I can see where the latency goes.
15. As a portfolio reviewer, I want to watch the retrieval details during a demo, so that I can see the system is doing real retrieval, not just prompting an LLM.

### Ingest

16. As a developer, I want a single ingest command that reads every Lecture PDF in a folder, so that indexing the Course Material is one step.
17. As a developer, I want each PDF page to become one Slide, so that Citations match what students see in the deck.
18. As a developer, I want each Passage prefixed with its Lecture title and Slide title, so that short bullet-point Slides keep their context.
19. As a developer, I want near-identical Slides within a Lecture (progressive builds) deduplicated, keeping the most complete version, so that duplicates don't crowd the top-5 results.
20. As a developer, I want duplicates across different Lectures (for example recap slides) kept, so that dedupe never removes legitimate content from a Lecture.
21. As a developer, I want ingest to report how many Slides it read, how many Duplicate Slides it removed, and how many Slides were near-empty, so that I know how much of the material is actually searchable.
22. As a developer, I want ingest to list the near-empty Slides by Lecture and Slide number, so that I can check whether important content is trapped in images.
23. As a developer, I want ingest to build the Passages for a chosen Retrieval Configuration, so that each configuration is indexed the way it will be searched.
24. As a developer, I want the built indexes written to a data directory that the API loads at startup, so that the service starts fast and never re-indexes on a request.
25. As a developer, I want the raw PDFs and built indexes kept out of git and out of the Docker image, so that copyrighted material is never published.

### Retrieval Configurations

26. As a developer, I want each Retrieval Configuration to be a named config file, so that every experiment is reproducible and comparable.
27. As a developer, I want the Baseline fixed as one Slide per Passage, dense-only search with bge-small, top-5, no BM25 and no reranker, so that every improvement is measured against a pre-registered configuration.
28. As a developer, I want the chunking step to compare four options, so that "tuned chunking" means something measurable:
    - one Slide per Passage;
    - a 2-Slide window (the Anchor Slide plus the previous Slide as context);
    - a 3-Slide window (the Anchor Slide plus one neighbour on each side as context);
    - long Slides split into several Passages that share the same Anchor Slide.
29. As a developer, I want every Passage to have exactly one Anchor Slide, so that wider windows can't win just by covering more Slides.
30. As a developer, I want a hybrid configuration that fuses BM25 and dense results, so that I can measure what keyword matching adds.
31. As a developer, I want a reranking configuration that reranks the top 20 hybrid results down to 5 with a cross-encoder, so that I can measure what reranking adds.
32. As a developer, I want the embedding model, the reranker, the fusion weights and the candidate depth all set in the config, not the code, so that tuning never needs code changes.

### Refusal

33. As a developer, I want the assistant to give a Refusal without calling the LLM when the best rerank score is below a threshold, so that unanswerable questions are fast and don't use up the free tier's rate limit.
34. As a developer, I want the LLM told to answer only from the supplied Passages, and to signal a Refusal through a structured `refused` field when they don't contain the answer, so that there's a second line of defence against invented answers that never relies on matching phrases in the answer text.
35. As a developer, I want the Refusal threshold tuned automatically on the Dev Split, so that it's chosen from data, not by hand.
36. As a developer, I want the threshold tuning to weigh correct Refusals against False Refusals, so that it can't "win" by refusing everything.

### Evaluation Set

37. As a developer, I want the Evaluation Set stored as a plain versioned file in the repo, so that anyone can inspect the questions.
38. As a developer, I want each Evaluation Pair to record a question, a reference answer, one or more Gold Slides, and whether it's an Unanswerable Question, so that every metric can be computed from it.
39. As a developer, I want a plan of target Slides spread across every Lecture in proportion to its size, with candidate questions drafted for each target by my AI coding assistant in-session, so that building 150 pairs is practical without paying for an API.
39a. As a developer, I want some drafted questions to need two neighbouring Slides to answer, so that the Evaluation Set tests retrieval across Slide boundaries.
40. As a developer, I want drafted questions to paraphrase rather than copy Slide wording, so that BM25 isn't rewarded for word overlap real students wouldn't produce.
41. As a developer, I want to review, edit or reject every drafted question on a page that shows the Gold Slide's text and a rendered image of the Slide, and lets me add extra Gold Slides, so that I can review it quickly.
42. As a developer, I want about 30 Unanswerable Questions, mostly near misses on topics the decks name but never explain, each checked against the whole Course Material, so that Refusal behaviour can be measured. I may also add hand-written hard questions through the review page.
43. As a developer, I want Gold Slides labelled after ingest, against Slides that survived dedupe, so that no label points at a removed Slide.
44. As a developer, I want an Evaluation Pair to allow several Gold Slides, so that content repeated across Lectures is labelled correctly.
45. As a developer, I want the Evaluation Set split once, with a fixed seed, two-thirds into the Dev Split and one third into the Test Split, so that the split never changes between runs.
46. As a developer, I want Unanswerable Questions spread across both splits, so that Refusal behaviour is both tunable and reportable.

### Scoring and reporting

47. As a developer, I want Recall@5 and MRR computed by collapsing ranked Passages to distinct Anchor Slides and scoring the first five, so that every Retrieval Configuration is scored by the same rule.
48. As a developer, I want Unanswerable Questions excluded from Recall@5 and MRR, so that they don't count as retrieval misses.
49. As a developer, I want Refusal accuracy and the false Refusal rate reported separately, so that Refusal behaviour is visible.
50. As a developer, I want one command that runs every Retrieval Configuration in the improvement ladder on a chosen split and writes a results table, so that the before/after story is reproducible.
51. As a developer, I want the Test Split run only when I explicitly ask for it, so that I don't accidentally tune against it.
52. As a developer, I want each answer given a Faithfulness Verdict (Supported, Partially Supported or Unsupported) against its own Citations, judged by my AI coding assistant in-session rather than through an API, so that I can report faithfulness without any paid service.
53. As a developer, I want 20 of those verdicts exportable for my own hand-checking, with the agreement rate reported, so that I can say how far the judge can be trusted.
54. As a developer, I want median and 95th-percentile `/ask` latency measured over the Test Split's questions, with the hardware recorded, so that the latency claim is reproducible.
55. As a portfolio reviewer, I want the README to show the results table and explain how each number was produced, so that I can trust the claims.

### Serving and running

56. As a developer, I want a `POST /ask` endpoint that takes a question and returns the answer, Citations, a Refusal flag and the timing breakdown, so that the UI and the latency measurement use the same contract.
57. As a developer, I want a `GET /health` endpoint, so that Docker and the UI can tell when the service is ready.
58. As a developer, I want `docker compose up` to start the API and the UI, so that the whole system runs with one command.
59. As a developer, I want the Groq API key (`GROQ_API_KEY` in `.env`) and every other setting read from environment variables, with an example env file, so that no secrets are committed.
59a. As a developer, I want to switch answering to a local Ollama model with one setting, so that the system works offline and without any account.
60. As a developer, I want the API to fail fast at startup with a clear message if the index is missing, so that I don't get confusing errors on the first question.

## Implementation Decisions

### Modules

**Ingest**
- Extracts text from each Lecture PDF page by page (PyMuPDF), so that one page is one Slide.
- Detects each Slide's title.
- Deduplicates near-identical Slides within a Lecture, keeping the most complete version. It never deduplicates across Lectures.
- Counts and lists near-empty Slides. "Near-empty" means very little extractable text beyond the title; the exact character threshold is a config setting.
- Builds Passages for a Retrieval Configuration. Each Passage carries its Anchor Slide and is prefixed with the Lecture and Slide titles.
- Writes the dense index (FAISS), the BM25 index and the Slide metadata to the data directory.
- Returns an ingest report: Slides read, Duplicate Slides removed, the near-empty count and the near-empty list.

**Retrieval**
- Takes a question and a Retrieval Configuration, and returns ranked Passages with their per-method scores: BM25, dense and rerank, where present.
- Hybrid mode fuses BM25 and dense rankings with weights from the config.
- Rerank mode reranks the top-N fused candidates with the cross-encoder and keeps the top 5.
- LangChain supplies only building blocks: loaders, the FAISS and BM25 retrievers, and fusion. The orchestration is the project's own code.

**Model boundaries**
- Three small interfaces sit between the project and its models: the embedder, the reranker, and the answering LLM.
- The real implementations are, all free to run:
  - `BAAI/bge-small-en-v1.5` for embeddings, running locally;
  - `cross-encoder/ms-marco-MiniLM-L-6-v2` for reranking, running locally;
  - an open-weight model on **Groq's free tier** for answers: `openai/gpt-oss-120b` with low reasoning effort, falling back to `openai/gpt-oss-20b` if the primary model errors, is rate-limited or returns malformed output. The key lives in `.env` as `GROQ_API_KEY`;
  - a local **Ollama** model (default `llama3.1:8b`) as an optional offline fallback, chosen with `COURSE_QA_LLM_PROVIDER=ollama`.
- Each one can be swapped through config or environment variables.
- The project pays for no API. Two jobs that would otherwise need a paid LLM are done instead by the developer's AI coding assistant (Claude Code), in-session: drafting candidate questions for the Evaluation Set, and judging Faithfulness Verdicts. Neither job is part of the running system.
- Groq's free tier is rate-limited. Clients retry on rate-limit errors, and `--answer` runs over the whole Evaluation Set are paced to stay within the limits.

**Answering**
- Applies the Refusal threshold to the best rerank score. Below the threshold it returns a Refusal without calling the LLM.
- Otherwise it prompts the LLM with the numbered Passages. The prompt says to answer only from them, cite with `[n]` markers, and set `refused` if they don't contain the answer.
- Afterwards it removes markers that point at no supplied Passage and logs that it did.
- It builds Citations from the markers that remain.
- The LLM returns structured output with two fields: `refused: bool` and `answer: string`.
- The LLM signals a Refusal only by setting `refused` to true. When it does, the response is a Refusal, Citations are empty, and the Refusal text is standard.
- The answer text is never phrase-matched to detect a Refusal.
- If the structured output is malformed, the request fails with an error rather than guessing.

**API**
- FastAPI provides `POST /ask` and `GET /health`.
- The indexes load once at startup and are read-only from then on.

**UI**
- Streamlit shows a question box, the answer with clickable Citations that reveal their Passages, a distinct Refusal state, and an expandable "Retrieval details" panel.
- It talks only to the API.

**Evaluation**
- **Question drafting:** a planning command picks target Slides across all Lectures in proportion to their size, skipping near-empty Slides; about 20% of targets are two neighbouring Slides whose answer spans both. Claude Code writes a paraphrased question and reference answer for each target in-session, with no API call. A check command flags drafts whose wording overlaps too much with their Slides.
- **Review:** a Streamlit review page shows one draft at a time: the question, the reference answer, each Gold Slide's text and a rendered image of the Slide, with Accept, Edit and Reject buttons and a way to add extra Gold Slides. Progress is saved, so a review can stop and resume.
- **Split:** one fixed-seed split into the Dev Split and the Test Split.
- **Scoring:** a pure scoring function.
- **Threshold tuning:** a pure threshold-tuning function.
- **Ladder runner:** runs the configs in order and writes the results table.
- **Faithfulness judging:** an export of the answers and their cited Passages, judged by Claude Code in-session into a committed verdicts file; the developer hand-checks 20 of them, and a command reports the agreement rate. The verdict shares are recomputed from the committed file by script, but re-judging needs a new session.
- **Latency measurement:** median and p95 for `/ask`.

### API contract

`POST /ask`
- **Request:** `{ question: string }`
- **Response:**
  - `answer: string`. On a Refusal, this holds the Refusal text.
  - `refused: bool`
  - `citations: [{ marker: int, lecture: string, slide: int, passage: string }]`. This list is empty on a Refusal.
  - `retrieval: [{ lecture, slide, passage, scores: { bm25?, dense?, rerank? } }]`, for the Retrieval details panel.
  - `timings_ms: { retrieve, rerank, generate, total }`. `generate` is 0 when the Refusal happens before the LLM call.

`GET /health` reports `ok` once the indexes are loaded.

### Evaluation Pair record

Each Evaluation Pair has these fields:
- an id;
- the question;
- the reference answer;
- the Gold Slides, as a list of one or more (Lecture, Slide) pairs, or an empty list for an Unanswerable Question;
- whether it is an Unanswerable Question;
- its origin: drafted-and-reviewed, hand-written, or sample (unreviewed smoke-check pairs that are never reported);
- its split: Dev or Test.

### Scoring function (pure)

- **Input:** for each Evaluation Pair, the ranked Passages with their Anchor Slides, the Gold Slides, the Unanswerable flag and whether a Refusal was given.
- **Collapsing:** ranked Passages are collapsed to distinct Anchor Slides in rank order, and only the first 5 are kept.
- **Recall@5:** the share of answerable pairs with at least one Gold Slide among those 5.
- **MRR:** the mean, over answerable pairs, of 1/rank of the first Gold Slide among the collapsed Slides, or 0 if none is found.
- **Refusal accuracy:** the share of Unanswerable Questions that got a Refusal.
- **False Refusal rate:** the share of answerable pairs that got a Refusal.
- Unanswerable Questions never enter Recall@5 or MRR.

### Threshold-tuning function (pure)

- **Input:** for each Dev Split pair, the best rerank score and the Unanswerable flag.
- **Candidates:** the midpoints between adjacent observed scores, plus the two extremes.
- **Choice:** it picks the threshold that maximises the mean of Refusal accuracy and (1 − false Refusal rate). Ties go to the lower threshold, which means fewer Refusals.
- **Output:** the threshold and the two rates achieved on the Dev Split.
- The chosen threshold is written into the reranking Retrieval Configuration.

### Retrieval Configurations (the improvement ladder)

1. **Baseline:** one Slide per Passage, dense-only bge-small, top-5, no BM25, no reranker.
2. **Chunking variants:** the four Passage-building options from user story 28, all dense-only. The best on the Dev Split goes forward.
3. **Hybrid:** the best chunking option with BM25 and dense fusion.
4. **Rerank:** hybrid top-20 reranked down to the top 5, plus the tuned Refusal threshold.

See ADR-0001 for why gold labels are at Slide level, why Anchor Slides exist, and why the split and the Baseline are fixed.

### Project shape

- Python 3.12, managed with uv.
- One package with ingest, retrieval, answering, API and evaluation modules, a separate Streamlit UI, and an evaluation folder holding the Evaluation Set and the Retrieval Configuration files.
- One compose file with two services, `api` and `ui`. The data directory is mounted as a volume.

## Testing Decisions

**What makes a good test here:** it exercises external behaviour through one of the seams below and asserts on outputs a user or the evaluation report would see. It doesn't assert on internal calls, intermediate data structures or private helpers. Tests must be deterministic, need no network and no model downloads in the default run, and finish in seconds.

**Seam 1: ingest and `POST /ask`, end to end**
- Tests generate 2–3 tiny Lecture PDFs on the fly. The fixtures include:
  - a progressive build (several near-identical Slides);
  - a near-empty Slide;
  - a long Slide;
  - the same Slide repeated in two Lectures.
- Tests run the ingest entry point, then call `POST /ask` through FastAPI's test client.
- **Assertions on the ingest report:** Slide count, Duplicate Slides removed (within a Lecture only, so the cross-Lecture copy survives), and the near-empty count and list.
- **Assertions on `POST /ask`:**
  - the response matches the contract;
  - Citations name Anchor Slides;
  - a marker that points at no Passage is removed;
  - Refusal happens below the threshold, with `generate` timing 0 and the LLM fake not called;
  - when the LLM fake returns `refused: true`, the response is a Refusal with empty Citations;
  - an answer whose text merely contains words like "not in the Passages", with `refused: false`, is **not** a Refusal;
  - malformed structured output produces an error;
  - `timings_ms` is present.
- Run against each chunking option, to show every Passage has exactly one Anchor Slide and that window context doesn't change the Anchor.
- **Test fakes:**
  - **Embedder:** deterministic, for example based on a hash of the words.
  - **Reranker:** returns scores the test sets per question or per Passage. This makes the Refusal threshold case fully deterministic.
  - **LLM:** scripted, returning set structured outputs: normal answers, answers with invalid markers, `refused: true`, and malformed output.

**Seam 2: the scoring function and the threshold-tuning function (pure)**
- Hand-made ranked inputs exercise each rule exactly:
  - collapsing duplicate Anchor Slides before taking the top 5;
  - several Gold Slides, where any one counts;
  - a Gold Slide at rank 6 or lower counts as a miss;
  - MRR ranks are computed after collapsing;
  - Unanswerable Questions are excluded from Recall@5 and MRR;
  - Refusal accuracy and the false Refusal rate.
- Threshold tuning:
  - perfectly separable scores give a threshold between the two groups;
  - overlapping scores give the threshold that maximises the balanced objective;
  - ties break towards the lower threshold;
  - a Dev Split with no Unanswerable Questions is handled without dividing by zero.

**Opt-in slow test:** marked `slow` and excluded by default. It runs the real bge-small and cross-encoder over the fixture Lectures to catch integration drift. No test calls Groq, Ollama or any other LLM service; the LLM is always a fake.

**Prior art:** none, because the repo is new. These tests become the prior art for future work.

## Out of Scope

- Conversation memory and follow-up questions. Every question is one-shot.
- Picking a course before asking, and filtering retrieval by course.
- OCR, images, diagrams and equation understanding. Slides with little extractable text are only counted and listed.
- Streaming answers.
- Login, user accounts and saved question history.
- Public hosting. This is a stretch goal after the system works locally, with rate-limit and abuse controls for the shared free-tier key designed then.
- Non-English Course Material.
- Committing or redistributing the Course Material itself.

## Further Notes

- The CV bullet reports whatever the Test Split run measures. The 62% → 87% and under-2 s figures are targets, not facts, until the scripts produce them.
- The Evaluation Set is the most labour-intensive part. Drafting and a strict second pass were done in-session by Claude Code; the developer reviews the flagged drafts and the Unanswerable Questions.
- The Baseline uses bge-small, so the improvement ladder measures chunking, hybrid retrieval and reranking, not the switch of embedding model.
- Vocabulary follows GLOSSARY.md. The evaluation rules follow ADR-0001. The no-paid-API constraint and its consequences follow ADR-0002.
- Latency is measured against Groq's free tier, so it includes a network round trip and depends on the free tier's current load. The README states the provider and model measured.
