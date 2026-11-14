# 07: Reranking and Refusal

**What to build:** A reranking Retrieval Configuration reranks the top 20 hybrid candidates down to 5 with a cross-encoder. When the best rerank score is below a threshold, the assistant gives a Refusal without calling the LLM. The threshold is tuned on the Dev Split by a pure function. The results table gains a rerank row with Refusal accuracy and the false Refusal rate. The UI shows Refusals in a clearly distinct state.

**Blocked by:** 06 (Hybrid retrieval and the Retrieval details panel)

**Note:** build and test this on the small sample of Evaluation Pairs from ticket 03, which should include a few Unanswerable Questions. The real Refusal threshold is tuned on the Dev Split, and real ladder numbers are recorded, only after ticket 04 delivers the full Evaluation Set. A threshold or numbers from the sample are smoke checks and must not be reported or frozen.

**Status:** ready-for-agent

- [ ] Reranker interface, with the real `cross-encoder/ms-marco-MiniLM-L-6-v2` and a fake whose scores the test sets per question or per Passage
- [ ] The rerank configuration reranks the hybrid top-N (N set in config, default 20) and keeps the top 5. Rerank scores appear in the `retrieval` list
- [ ] When the best rerank score is below the threshold, the response is a Refusal, the LLM isn't called, and `timings_ms.generate` is 0
- [ ] The pure threshold-tuning function takes each Dev Split pair's best rerank score and Unanswerable flag, tries the midpoints between adjacent scores plus the two extremes, and maximises the mean of Refusal accuracy and (1 − false Refusal rate), with ties going to the lower threshold
- [ ] The tuned threshold is written into the reranking Retrieval Configuration
- [ ] The results table rows include Refusal accuracy and the false Refusal rate
- [ ] The Streamlit page shows Refusals in a distinct state, without Citations
- [ ] Seam 1 tests: with fake rerank scores set below the threshold, the response is a Refusal and the LLM fake records no call; above the threshold, an answer is returned
- [ ] Seam 2 tests for threshold tuning: separable scores, overlapping scores, the tie-break, and a Dev Split with no Unanswerable Questions (no division by zero)
