# 01: Tracer bullet: ask a question, get a cited answer

**What to build:** A developer drops Lecture PDFs into a folder, runs ingest, starts the API and the Streamlit page, types a question, and gets a short answer with numbered Citations ("Lecture 4 — Slide 12"). Clicking a Citation shows its Passage. This is the Baseline Retrieval Configuration end to end: one Slide per Passage, dense-only bge-small, top-5, no BM25 and no reranker. It also sets up the project skeleton (Python 3.12, uv, package layout, pytest, `.gitignore` that excludes PDFs and indexes) and the model boundaries everything later builds on. See the spec (`.scratch/course-qa-assistant/spec.md`), GLOSSARY.md and ADR-0001.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [x] Ingest reads every Lecture PDF in a folder page by page, so that one page is one Slide, and detects each Slide's title
- [x] Each Passage has exactly one Anchor Slide and is prefixed with the Lecture title and Slide title
- [x] Ingest writes the FAISS index and Slide metadata to the data directory, and the API loads them once at startup
- [x] The Baseline is a named Retrieval Configuration file; the model, top-k and passage-building settings come from config, not code
- [x] Embedder interface, with the real bge-small and a deterministic fake
- [x] LLM interface returning structured output `{refused: bool, answer: string}`, with a real implementation and a scripted fake. Originally Claude Haiku 5.5; replaced on 2026-11-14 by Groq's free tier (now openai/gpt-oss-120b, falling back to openai/gpt-oss-20b), with Ollama as an offline fallback, under ADR-0002
- [x] The prompt tells the LLM to answer only from the numbered Passages, cite with `[n]`, and set `refused` when the Passages don't contain the answer
- [x] `refused: true` produces a Refusal with empty Citations and the standard Refusal text. The answer text is never phrase-matched. Malformed structured output produces an error
- [x] Markers that point at no supplied Passage are removed and logged
- [x] `POST /ask` returns `answer`, `refused`, `citations [{marker, lecture, slide, passage}]`, `retrieval` and `timings_ms {retrieve, rerank, generate, total}`, as in the spec contract
- [x] `GET /health` reports `ok` once the indexes are loaded
- [x] The Streamlit page has a question box and shows the answer with clickable Citations that reveal their Passages
- [x] Seam 1 tests generate tiny fixture PDFs, run ingest, call `/ask` through FastAPI's test client with the fakes, and assert on the contract, Anchor Slides, marker removal, `refused: true`, "refused-sounding" text with `refused: false` not being a Refusal, and malformed output
- [x] Default tests need no network and no model downloads

## Comments

**2026-11-14:** Built test-first. 8 Seam 1 tests pass with the fakes; the opt-in slow test passes with the real bge-small embedder. A real ingest of the Course Material read 542 Slides from 6 Lectures. **Not yet verified live:** a real LLM answer and the Streamlit page in a browser. (Answering now runs on Groq's free tier; see ADR-0002. It needs `GROQ_API_KEY` in `.env`, or `COURSE_QA_LLM_PROVIDER=ollama` with Ollama running.) Follow-ups noticed: symbol-font bullets extract as `�` (cosmetic, worth cleaning in ticket 02); page numbers and deck footers sit inside Slide text; bge-small's query instruction prefix isn't used yet (a candidate setting for ticket 05).

**2026-11-15:** Verified live through `course-qa serve` on Groq's free tier (`openai/gpt-oss-120b`, low reasoning effort; no fallback was triggered). "Which wavelengths of light can the human eye see?" returned a cited answer ([1] L04 Vision — Slide 6) in 823 ms total (retrieve 24, generate 798). "What does Fitts' Law predict?" returned a correct Refusal in 1,004 ms: the decks only mention Fitts' Law in topic lists (L04 Vision Slide 3, L03 Slide 107), and the Motor Skills lecture that covers it isn't in the Course Material. The Streamlit page has still not been opened in a browser.
