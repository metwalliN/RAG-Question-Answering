# 04: Building the Evaluation Set

**What to build:** The developer can build the Evaluation Set (about 227 pairs) without paying for any API (ADR-0002):
- **Planning:** a command picks target Slides across all six Lectures in proportion to each Lecture's number of eligible (not near-empty) Slides. About 20% of targets are two neighbouring Slides, so their answer spans both.
- **Drafting:** Claude Code writes a paraphrased question and reference answer for each target in-session, with no API call. Drafts must not copy Slide wording.
- **Overlap check:** a command flags drafts whose wording overlaps too much with their Slides, so they are reworded before review.
- **Review:** a Streamlit review page shows one draft at a time: the question, the reference answer, and each Gold Slide's text plus a rendered image of the Slide. It has Accept, Edit and Reject buttons and a way to add extra Gold Slides. Progress is saved, so a review can stop and resume.
- **Unanswerable Questions:** Claude Code drafts about 30 in-session, each checked against the whole Course Material, and the developer reviews them; the developer may also add hand-written pairs.
- **Split:** the set is split once, with a fixed seed, two-thirds into the Dev Split and one third into the Test Split.

The tooling and the drafts are this ticket. The developer's review and hand-writing happen outside it.

**Blocked by:** 02 (Ingest report: Duplicate Slides and near-empty Slides). Gold Slides must be labelled after dedupe.

**Status:** ready-for-agent

**Test seams (agreed with the user):**
- **A: planning and the overlap check**, on fixture Lectures.
- **B: the review session's operations** (accept, edit, reject, add a Gold Slide, resume) and what they write. The Streamlit page is a thin view over it and is checked by running it.
- **C: split and validate**, as pure functions.

- [x] Ingest saves Slide-level data (Lecture, Slide, title, text, near-empty flag, source PDF) for planning and review
- [x] The plan spreads targets across Lectures in proportion to their eligible Slides, never targets a near-empty Slide, uses each Slide at most once, and is the same for the same seed
- [x] About 20% of targets (configurable) are two neighbouring Slides of the same Lecture, and both become Gold Slides
- [x] About 200 drafts are written by Claude Code in-session, paraphrased away from the Slide wording
- [x] Drafts whose wording overlaps heavily with their Slides are flagged
- [x] The review page shows the question, the reference answer, each Gold Slide's text and a rendered image of the Slide, with Accept, Edit and Reject, and a way to add extra Gold Slides
- [x] Gold Slides can only reference Slides present in the current ingest; unknown references are rejected
- [x] Review progress is saved after every decision, and the review resumes at the first undecided draft
- [x] Hand-written pairs and Unanswerable Questions (empty Gold Slides) can be added in the same file format, with origin recorded
- [x] The split uses a fixed seed, puts Unanswerable Questions in both splits, and gives the same result every time it runs
- [x] A validation command checks the whole Evaluation Set file (fields, Gold Slide references, split sizes) and reports problems

## Comments

**2026-11-15:** Tooling and drafts done, built test-first: Seam A (planning, overlap check) 5 tests, Seam B (review session) 5, Seam C (split, validate) 4; 54 tests in total, all passing.
- **Plan:** `course-qa plan-drafts` (seed 2026) picked 200 targets across the six Lectures in proportion to their eligible Slides (18 / 19 / 44 / 18 / 26 / 75), 41 of them two neighbouring Slides. It holds Slide text, so it lives in the git-ignored `data/drafts/plan.jsonl`.
- **Drafts:** `eval/drafts.jsonl` holds 198 drafts written by Claude Code in-session (40 need two Slides). t010 and t067 were skipped because their Slides hold no askable content. Where a planned two-Slide target's second Slide had no relevant text, the draft became single-Slide rather than carrying a Gold Slide that doesn't hold the answer. `course-qa check-drafts` flags 0 drafts; 6 were reworded after it flagged them (5 or more consecutive words copied from the Slide).
- **Review page:** `python -m uv run streamlit run ui/review.py` shows one draft at a time with the Slide image (same renderer as Citations), Accept / Accept with edits / Reject, adding or removing Gold Slides, and a form for hand-written and Unanswerable pairs. Decisions go to `eval/reviewed.jsonl` as they're made.
- **Next (developer):** review the drafts, add about 30 hand-written hard pairs including Unanswerable Questions, then run `course-qa split` and `course-qa validate`. Until then, tickets 03 and 05–08 keep using `eval/sample_pairs.jsonl` for smoke checks only.

**2026-11-15, later:** The user reviewed the flagged drafts (rejected d015; 197 answerable pairs kept). At the user's request: Claude Code drafted 30 Unanswerable Questions (u001-u030), mostly near misses on topics the decks only name (e.g. Fitts' Law, Gestalt principles, gradient descent), each checked against the whole index by word match and bge-small, with 10 of 40 candidates dropped as too close to Slide content; and the split became two-thirds Dev / one third Test (about 151 / 76). The review page handles drafted Unanswerable Questions; adding a Gold Slide turns one into an answerable question. Next: the user reviews u001-u030, then `course-qa split` and `course-qa validate`.
