# 01: Tracer bullet: ask a question, get a cited answer

**What to build:** A developer drops Lecture PDFs into a folder, runs ingest, starts the API and the Streamlit page, types a question, and gets a short answer with numbered Citations ("Lecture 4 — Slide 12"). Clicking a Citation shows its Passage. This is the Baseline Retrieval Configuration end to end: one Slide per Passage, dense-only bge-small, top-5, no BM25 and no reranker. It also sets up the project skeleton (Python 3.12, uv, package layout, pytest, `.gitignore` that excludes PDFs and indexes) and the model boundaries everything later builds on. See the spec (`.scratch/course-qa-assistant/spec.md`), GLOSSARY.md and ADR-0001.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] Ingest reads every Lecture PDF in a folder page by page, so that one page is one Slide, and detects each Slide's title
- [ ] Each Passage has exactly one Anchor Slide and is prefixed with the Lecture title and Slide title
- [ ] Ingest writes the FAISS index and Slide metadata to the data directory, and the API loads them once at startup
- [ ] The Baseline is a named Retrieval Configuration file; the model, top-k and passage-building settings come from config, not code
- [ ] Embedder interface, with the real bge-small and a deterministic fake
- [ ] LLM interface returning structured output `{refused: bool, answer: string}`, with real Claude Haiku 5.5 and a scripted fake
- [ ] The prompt tells the LLM to answer only from the numbered Passages, cite with `[n]`, and set `refused` when the Passages don't contain the answer
- [ ] `refused: true` produces a Refusal with empty Citations and the standard Refusal text. The answer text is never phrase-matched. Malformed structured output produces an error
- [ ] Markers that point at no supplied Passage are removed and logged
- [ ] `POST /ask` returns `answer`, `refused`, `citations [{marker, lecture, slide, passage}]`, `retrieval` and `timings_ms {retrieve, rerank, generate, total}`, as in the spec contract
- [ ] `GET /health` reports `ok` once the indexes are loaded
- [ ] The Streamlit page has a question box and shows the answer with clickable Citations that reveal their Passages
- [ ] Seam 1 tests generate tiny fixture PDFs, run ingest, call `/ask` through FastAPI's test client with the fakes, and assert on the contract, Anchor Slides, marker removal, `refused: true`, "refused-sounding" text with `refused: false` not being a Refusal, and malformed output
- [ ] Default tests need no network and no model downloads
