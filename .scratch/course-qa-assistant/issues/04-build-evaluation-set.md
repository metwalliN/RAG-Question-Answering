# 04: Building the Evaluation Set

**What to build:** The developer can build the 150-pair Evaluation Set without paying for any API (ADR-0002):
- **Planning:** a command picks target Slides across all six Lectures in proportion to each Lecture's number of eligible (not near-empty) Slides. About 20% of targets are two neighbouring Slides, so their answer spans both.
- **Drafting:** Claude Code writes a paraphrased question and reference answer for each target in-session, with no API call. Drafts must not copy Slide wording.
- **Overlap check:** a command flags drafts whose wording overlaps too much with their Slides, so they are reworded before review.
- **Review:** a Streamlit review page shows one draft at a time: the question, the reference answer, and each Gold Slide's text plus a rendered image of the Slide. It has Accept, Edit and Reject buttons and a way to add extra Gold Slides. Progress is saved, so a review can stop and resume.
- **Hand-written pairs:** the developer adds hand-written hard questions, including Unanswerable Questions.
- **Split:** the set is split once, with a fixed seed, into a 100-pair Dev Split and a 50-pair Test Split.

The tooling and the drafts are this ticket. The developer's review and hand-writing happen outside it.

**Blocked by:** 02 (Ingest report: Duplicate Slides and near-empty Slides). Gold Slides must be labelled after dedupe.

**Status:** ready-for-agent

**Test seams (agreed with the user):**
- **A: planning and the overlap check**, on fixture Lectures.
- **B: the review session's operations** (accept, edit, reject, add a Gold Slide, resume) and what they write. The Streamlit page is a thin view over it and is checked by running it.
- **C: split and validate**, as pure functions.

- [x] Ingest saves Slide-level data (Lecture, Slide, title, text, near-empty flag, source PDF) for planning and review
- [ ] The plan spreads targets across Lectures in proportion to their eligible Slides, never targets a near-empty Slide, uses each Slide at most once, and is the same for the same seed
- [ ] About 20% of targets (configurable) are two neighbouring Slides of the same Lecture, and both become Gold Slides
- [ ] About 200 drafts are written by Claude Code in-session, paraphrased away from the Slide wording
- [ ] Drafts whose wording overlaps heavily with their Slides are flagged
- [ ] The review page shows the question, the reference answer, each Gold Slide's text and a rendered image of the Slide, with Accept, Edit and Reject, and a way to add extra Gold Slides
- [ ] Gold Slides can only reference Slides present in the current ingest; unknown references are rejected
- [ ] Review progress is saved after every decision, and the review resumes at the first undecided draft
- [ ] Hand-written pairs and Unanswerable Questions (empty Gold Slides) can be added in the same file format, with origin recorded
- [ ] The split uses a fixed seed, puts Unanswerable Questions in both splits, and gives the same result every time it runs
- [ ] A validation command checks the whole Evaluation Set file (fields, Gold Slide references, split sizes) and reports problems
