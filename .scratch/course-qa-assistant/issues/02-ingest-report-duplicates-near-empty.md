# 02: Ingest report: Duplicate Slides and near-empty Slides

**What to build:** When the developer runs ingest, near-identical Slides within a Lecture (progressive builds) are deduplicated, keeping the most complete version. Duplicates across Lectures are kept. Ingest then prints and returns a report: Slides read, Duplicate Slides removed, and how many Slides were near-empty, listed by Lecture and Slide number. The developer can see how much of the Course Material is actually searchable.

**Blocked by:** 01 (Tracer bullet: ask a question, get a cited answer)

**Status:** ready-for-agent

- [ ] Near-identical Slides within one Lecture are deduplicated, and the most complete version is the one kept
- [ ] Identical Slides in different Lectures both survive
- [ ] The near-empty threshold (extractable text beyond the title) is a config setting
- [ ] The ingest report includes Slides read, Duplicate Slides removed, the near-empty count and the near-empty list
- [ ] Removed Duplicate Slides never appear in the index or in Citations
- [ ] Seam 1 fixtures include a progressive build, a near-empty Slide and the same Slide in two Lectures; tests assert on the ingest report and on what `/ask` can cite
