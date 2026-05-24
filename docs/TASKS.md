# Post-processing tasks

Open issues for the transcription of notebook `15908163` (collection `2224542`).
Each task covers both **diagnosis** (surveying the current PAGE-XML to see
how often / where the problem occurs) and **improvement** (a rule or
pipeline step that fixes it and writes corrected PAGE-XML to
`data/notebook_15908163/page_final/`).

## 1. Dates

- [ ] Inventory every date-like token in the transcription (Hebrew calendar,
      Gregorian, mixed; e.g. `תרצ"ח`, `1938`, `15.4.38`, `ט"ו ניסן`).
- [ ] Classify: Hebrew-letter numerals vs. Arabic numerals vs. month names.
- [ ] Flag malformed dates (missing gershayim, OCR-confused digits like
      `1`/`l`/`ו`, wrong separators).
- [ ] Decide a normalized representation and emit corrected forms in
      `page_final/`; consider tagging dates so they're queryable downstream.

## 2. Roman letters and other LTR material

- [ ] Find every LTR run inside the RTL text: Latin words, Arabic numerals,
      site codes, measurements, abbreviations.
- [ ] Diagnose how Transkribus currently encodes them — order in the
      `<Unicode>` line, presence/absence of bidi control characters,
      reversed digit sequences (`8391` ↔ `1938`).
- [ ] Fix reversed numeric runs and stray LTR fragments; verify rendering
      in both a plain text dump and the Transkribus viewer.
- [ ] Where useful, wrap LTR runs in an explicit marker so the bidi
      behaviour is stable across exports.

## 3. Line extension and unification

- [x] Identify lines split across the page that should be a single logical
      line (continuations, hanging words, marginal extensions).
- [x] Diagnose at the PAGE-XML level: are these separate `<TextLine>`
      elements, separate `<TextRegion>`s, or split baselines? → separate
      `<TextLine>` elements within one region, split horizontally.
- [x] Define merge rules (geometric adjacency, reading order, indent
      heuristics) and unify the offending lines, preserving baseline
      coordinates for the merged result. → [`code/corrections/line_merge.py`](../code/corrections/line_merge.py):
      cluster lines whose baseline centres are within half the median line
      spacing, concatenate RTL (rightmost fragment first), merge baselines,
      and clamp every line to a full-width band `[region_xmin .. region_xmax]`.
- [ ] Spot-check on a handful of pages before running across all 89.
      → done for doc `15642626` page 10 (37→34 lines, 3 fragment-rows merged;
      pushed as a new transcript layer). Lines an inline illustration wraps
      around are already handled (their fragments share a baseline). **Open:**
      subscript / below-baseline comments are mis-recognised — a separate issue.

## 4. Acronym normalization (gershayim)

- [ ] Survey all uses of `"` and `״` (Hebrew gershayim) and `'` / `׳`
      (geresh) in the transcription — acronyms vs. quotation marks vs.
      stray punctuation.
- [ ] Normalize the character itself: ASCII `"`/`'` → Unicode `״` (U+05F4)
      and `׳` (U+05F3) where the context is Hebrew abbreviation.
- [ ] Normalize *position*: gershayim belongs before the final letter
      (`תשע״ה`, not `תשעה״`); fix misplacements.
- [ ] Build a small acronym lexicon (`ז״ל`, `תנ״ך`, `ע״פ`, site- and
      period-specific abbreviations from the notebook) to validate
      candidates against.
- [ ] Distinguish gershayim used as quote marks from gershayim used in
      acronyms before normalizing — don't rewrite real quotations.

## Cross-cutting

- [ ] Decide an output convention: edit in place vs. write to
      `page_final/`, and how to record what changed (PAGE-XML
      `<Metadata>` comment? side-car JSON diff?).
- [ ] Agree on the Transkribus push workflow: one combined push per page
      after all four passes, or one push per task (each becomes its own
      transcript layer).
