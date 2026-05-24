# Post-processing tasks

Open issues for the transcription of notebook `15908163` (collection `2224542`).
Each task covers both **diagnosis** (surveying the current PAGE-XML to see
how often / where the problem occurs) and **improvement** (a rule or
pipeline step that fixes it and writes corrected PAGE-XML to
`data/notebook_15908163/page_final/`).

## 1. Dates

- [x] Inventory date tokens of the form day/Roman-month/year (the dominant
      pattern). [`code/diagnostics/date_spans.py`](../code/diagnostics/date_spans.py)
      finds 255 spans on 87 pages, separating dates from fractions (`1/2`) by
      requiring a Roman-numeral month.
- [ ] Inventory the remaining date styles (Hebrew calendar `תרצ"ח`, `15.4.38`,
      month names `ט"ו ניסן`) — not yet covered.
- [x] Flag malformed/inconsistent dates: 16 use a `\` separator, 37 use Unicode
      Roman numerals (`Ⅳ` U+2163) instead of ASCII, 25 are reversed
      year/month/day (bidi artifact, overlaps #2 / LTR_ORDER_FINDINGS).
- [ ] **Correct date order first** (reverse the year/month/day cases), *then*
      normalize Roman numerals (`Ⅳ`→`IV`) and consider `\`→`/`. Order matters:
      Roman/slash normalization only makes sense on already-ordered dates.

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

## 4. Acronym / punctuation normalization (gershayim + dashes)

- [x] Survey all uses of `"`/`״` and `'`/`׳` —
      [`code/diagnostics/quote_survey.py`](../code/diagnostics/quote_survey.py)
      classifies by function (acronym / abbrev / transliteration / quotation).
- [x] Normalize the character itself. **Decision:** collapse *all* quote-like
      marks to Hebrew punctuation by width (single→`׳`, double→`״`), including
      quotation marks — uniform glyphs help OCR training. Also unite dash
      variants (`–`→`-`). Done in
      [`code/corrections/normalize.py`](../code/corrections/normalize.py)
      (families `quotes`, `dashes`); 1041 marks + 82 dashes over 88 pages,
      written to `page_final/`. Quote pass pushed to Transkribus as new layers.
- [ ] Normalize *position*: gershayim belongs before the final letter
      (`תשע״ה`, not `תשעה״`); fix misplacements. (Not done — by-width pass
      doesn't move marks.)
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
