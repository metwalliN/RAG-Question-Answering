# 10: Final Test Split run and README results

**What to build:** Once tuning on the Dev Split is finished, the developer runs the whole improvement ladder once on the Test Split:
1. Baseline
2. Chunking variants
3. Hybrid
4. Rerank, with the tuned Refusal threshold

They then publish the results in the README. Each number in the README states how it was produced, so a portfolio reviewer can reproduce it. The CV bullet is updated with the measured figures, whatever they turn out to be.

**Blocked by:** 04 (Building the Evaluation Set), 05 (Chunking variants), 07 (Reranking and Refusal), 08 (Faithfulness Verdicts), 09 (Docker compose and the latency measurement)

**Status:** ready-for-agent

- [ ] Every Retrieval Configuration is frozen, including the tuned threshold, before the Test Split run
- [ ] One command produces the Test Split results table: Recall@5, MRR, Refusal accuracy, false Refusal rate and Faithfulness Verdict shares, one row per configuration
- [ ] Latency (median and p95) is measured over the Test Split's questions on the Docker setup, with the hardware recorded
- [ ] The README includes the results table, the judge agreement rate, the latency figures, the hardware, and the LLM provider and model (Groq free tier or Ollama)
- [ ] The README states that the project uses no paid API (ADR-0002), and that Faithfulness Verdicts were judged in-session by Claude Code and committed as a file, so they are recomputed by script but not re-judged by it
- [ ] The README explains the method: Slide-level Gold Slides, Anchor Slide collapsing, the fixed 100/50 split, the pre-registered Baseline and the paraphrase rule for questions (linking ADR-0001)
- [ ] The README states the Evaluation Set's size and make-up: drafted-and-reviewed versus hand-written, and how many Unanswerable Questions
- [ ] The CV bullet's numbers match the README exactly
