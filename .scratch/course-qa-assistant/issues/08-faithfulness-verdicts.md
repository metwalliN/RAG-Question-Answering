# 08: Faithfulness Verdicts

**What to build:** When the ladder runs with answering enabled, a Claude Sonnet 5.5 judge gives each answer a Faithfulness Verdict (Supported, Partially Supported or Unsupported) against that answer's own Citations. The results table reports the share of each verdict. The developer can export 20 judged answers for hand-checking and get the agreement rate between their verdicts and the judge's.

**Blocked by:** 03 (Scoring and the Baseline results table)

**Note:** build and test this on the small sample of Evaluation Pairs from ticket 03. Real Faithfulness Verdict shares and the judge agreement rate are recorded only after ticket 04 delivers the full Evaluation Set. Numbers from the sample are smoke checks and must not be reported.

**Status:** ready-for-agent

- [ ] The judge uses the shared LLM interface with structured output (one of the three verdicts plus a short reason), and the judge model is set in config
- [ ] The judge sees only the answer and its cited Passages, not the reference answer
- [ ] Refusals aren't judged; they're counted separately
- [ ] The results table includes the share of each Faithfulness Verdict per Retrieval Configuration
- [ ] An export picks 20 judged answers with a fixed seed into a file the developer can fill in with their own verdicts
- [ ] An agreement command compares the filled-in file with the judge's verdicts and reports the agreement rate
- [ ] Tests use the scripted LLM fake. No test calls the real Anthropic API
