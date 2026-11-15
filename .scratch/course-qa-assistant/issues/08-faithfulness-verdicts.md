# 08: Faithfulness Verdicts

**What to build:** When the ladder runs with answering enabled, every answer is exported together with its cited Passages. Claude Code then judges each one in-session, with no API call (ADR-0002), giving a Faithfulness Verdict (Supported, Partially Supported or Unsupported) and a short reason, written into a committed verdicts file. The results table reports the share of each verdict, recomputed from that file by script. The developer hand-checks 20 verdicts, and a command reports the agreement rate between the developer's verdicts and Claude Code's.

**Blocked by:** 03 (Scoring and the Baseline results table)

**Note:** build and test this on the small sample of Evaluation Pairs from ticket 03. Real Faithfulness Verdict shares and the judge agreement rate are recorded only after ticket 04 delivers the full Evaluation Set. Numbers from the sample are smoke checks and must not be reported.

**Status:** ready-for-agent

- [ ] An export command writes, for each answered pair, the question, the answer and its cited Passages, in a file format Claude Code can judge in-session
- [ ] The export shows only the answer and its cited Passages, not the reference answer
- [ ] The verdicts file records one of the three verdicts plus a short reason per answer, and is validated on load (unknown verdicts or missing answers are rejected)
- [ ] Refusals aren't judged; they're counted separately
- [ ] The results table includes the share of each Faithfulness Verdict per Retrieval Configuration, computed from the committed verdicts file
- [ ] An export picks 20 judged answers with a fixed seed into a file the developer fills in with their own verdicts, without seeing Claude Code's
- [ ] An agreement command compares the filled-in file with Claude Code's verdicts and reports the agreement rate
- [ ] If the answers change after judging (a re-run gives different answers), the stale verdicts are detected and reported rather than silently reused
- [ ] Tests use fakes and fixture files. No test calls any LLM service
