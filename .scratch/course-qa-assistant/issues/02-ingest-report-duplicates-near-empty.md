# 02: Ingest report: Duplicate Slides and near-empty Slides

**What to build:** When the developer runs ingest, near-identical Slides within a Lecture (progressive builds) are deduplicated, keeping the most complete version. Duplicates across Lectures are kept. Ingest then prints and returns a report: Slides read, Duplicate Slides removed, and how many Slides were near-empty, listed by Lecture and Slide number. The developer can see how much of the Course Material is actually searchable.

**Blocked by:** 01 (Tracer bullet: ask a question, get a cited answer)

**Status:** ready-for-agent

- [x] Near-identical Slides within one Lecture are deduplicated, and the most complete version is the one kept
- [x] Identical Slides in different Lectures both survive
- [x] The near-empty threshold (extractable text beyond the title) is a config setting
- [x] The ingest report includes Slides read, Duplicate Slides removed, the near-empty count and the near-empty list
- [x] Removed Duplicate Slides never appear in the index or in Citations
- [x] Broken bullet glyphs are stripped from Slide text: the replacement character `�` (U+FFFD) and private-use symbol-font characters (U+E000–U+F8FF, e.g. Wingdings U+F0A7, U+F0E0, U+F0D8). Lines left empty are dropped
- [x] Page numbers are removed: a line consisting only of a number equal to the Slide's own page number. Other numeric lines are kept
- [x] Repeated deck footers and headers are removed: a line sitting in the top or bottom margin of the page (default 8% of the page height) on at least a configured share of a Lecture's Slides (default 10%) and at least a minimum count (default 5). Position is required because the PDF wraps phrases like "Supervised Learning", so a body word like "Learning" repeats on 28% of the ML deck's Slides
- [x] Lines holding only bullet or arrow symbols (e.g. a lone "•") are stripped
- [x] Slide title detection ignores footer lines and page numbers
- [x] The ingest report lists the footer lines removed per Lecture
- [x] Cleaning runs before dedupe and the near-empty check, so page numbers and footers don't make builds look different or empty Slides look full
- [x] Kept Slides keep their original page number, so Citations still match the PDF
- [x] Seam 1 fixtures include a progressive build, a near-empty Slide, the same Slide in two Lectures, broken glyphs, page numbers and a repeated footer; tests assert on the ingest report and on what `/ask` can cite

## Comments

**2026-11-14:** Built test-first; 11 new Seam 1 tests (19 in total, all passing). On the real Course Material, ingest reads 542 Slides, removes 13 Duplicate Slides (each one's text is kept in full by the Slide after it), indexes 529 Passages, and lists 54 near-empty Slides. Footers removed: "Human Computer Interaction" and "CSEN909: Human Computer Interaction" in the HCI decks; none in the ML deck. No broken glyphs, page numbers or lone bullet lines remain. Two notes: the replacement character `�` is stripped by the same rule as private-use glyphs, but the fixtures can only reproduce private-use glyphs (MuPDF won't emit U+FFFD from a font map), so `�` is verified against the real decks, not a unit test. A footer that appears on fewer than 5 Slides of a Lecture is kept (two such mentions remain in Lecture 2UX 2).

**2026-11-15:** Follow-up cleaning from the user's review of the Streamlit page: titles wrapped over several lines are joined (only lines in the same font on the same baseline or within 1.5 line-heights, and never list items), "o" sub-bullets are stripped, Sinhala-block signs that equation fonts use as hat accents are stripped, and mathematical letters are folded to plain ones (𝜽𝟎 → θ0). Lecture names show underscores as spaces. New totals on the real Course Material: 542 Slides read, 15 Duplicate Slides removed (two real builds that broken titles had hidden), 527 Passages, 58 near-empty Slides.
