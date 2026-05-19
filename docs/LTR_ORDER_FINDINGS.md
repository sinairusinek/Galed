# LTR-order diagnostic — first sweep

Initial pass over `data/notebook_15908163/page/` (89 pages), focused on the
two LTR-run categories that can be checked from text alone: **dates** and
**Roman numerals**. The goal was to test whether transcribers' edits in
Transkribus' bidi-rendered editor produced *logically reversed* LTR runs.

## Result

Yes — at least 15 dates and 1 Roman numeral are stored in reversed logical
order. The smoking gun is on **page 4** (line tr_1_tl_1):

```
כ47 קIX ח. מע. 7/IIV/1972 (המשך)
```

`IIV` is not a valid Roman numeral. It is the character-reversal of `VII`.
The only realistic way that string enters the XML is if a transcriber
typed the LTR characters in **visual-mirror order** — reading them off
the manuscript leftmost-first into a bidi-confused editor field. The
neighbouring page-1, -3, -5 entries for the same week use a clean
`D/VII/1972` shape, so this isn't the scribe's hand — it's an editor
artefact.

## The scribe's convention

Across ~110 date occurrences in the notebook, the dominant form is
**`DD/MM/YY`** or **`DD/MM/YYYY`** with the month written as a Roman
numeral (Israeli standard, 1969–1988):

```
28/VI/1969    25/VII/69    9/V/69    20/VI/1988    21/VI/88
```

This makes the reverse shape — `YY(YY)/MM/DD` — easy to flag.

## Confirmed reversed dates

| file | stored | suspected logical | note |
|---|---|---|---|
| `0001_…` | `1969/VII/25` | `25/VII/1969` | header line |
| `0002_…` | `72/VII/5`    | `5/VII/72`    | parenthetical |
| `0004_…` | `7/IIV/1972`  | `7/VII/1972`  | **invalid Roman — proof** |
| `0008_…` | `1969.5.3`    | `3.5.1969`    | dot-separated |
| `0026_…` | `88/VII/5`    | `5/VII/88`    | |
| `0031_…` | `88/VIII/14`  | `14/VIII/88`  | |
| `0033_…` | `88/VIII/17`  | `17/VIII/88`  | |
| `0034_…` | `1988/VIII/17`, `88/VIII/18` | day-first | |
| `0035_…` | `1988/VIII/19`, `88/VIII/20` | day-first | |
| `0036_…` | `1988/VIII/20`, `1988/VIII/21` | day-first | |
| `0037_…` | `8/88/23`     | likely `23/8/88` | Arabic-num month |
| `0038_…` | `1987/XII/27`, `79/I/14`, `87/XII/23` | day-first | |
| `0039_…` | `1987/XII/28` | `28/XII/1987` | |
| `0040_…` | `1987/XII/29` | `29/XII/1987` | |
| `0050_…` | `1988/I/26`, `88/I/29` | day-first | |
| `0052_…` | `1988/I/31`, `88/II/3` | day-first | |

## What's *not* a problem

Page 2's `1/VII/72` looks visually different from the manuscript (`72` is
on the left of the manuscript LTR run, `1` is on the left of the
Transkribus viewer's rendering), but it is the **logically correct** form
under DD/MM/YY convention. The visual mismatch comes from the *scribe*
having written the LTR run with the day adjacent to the preceding Hebrew
word (i.e. on the right of the LTR run on paper) — the opposite of what
Unicode bidi does when it renders a logically-stored DD/MM/YY date.
Different layouts, same logical string.

This distinction matters: not every visual mismatch is a transcription
bug. The reliable signal is **semantic** (does the date make sense in the
notebook's convention?) and **bidi-asymmetric tokens** like invalid Roman
numerals.

## Next steps

1. Open each affected page in Transkribus and **re-key the LTR run in
   logical order**. Watch the cursor behaviour while typing: in an RTL
   field, type the day first; the digits will visually move leftward as
   you go — that's correct and means you're entering logical order.
2. Re-run the diagnostic after the fix-up pass:
   ```sh
   python3 -m code.diagnostics.ltr_order data/notebook_15908163/page
   ```
   It should report 0 issues.
3. Extend the diagnostic to cover other LTR runs: Latin words, site
   codes, measurements. Those don't have a built-in validity check, so
   the approach there will be a whitelist of expected tokens + manual
   review of anything outside it.
4. Decide whether to fix in-place on Transkribus (one new transcript
   layer per page) or to fix locally in the XML and push the corrected
   files back. The diagnostic + `push` / `push-dir` in `code/transkribus/sync.py`
   already supports the latter.
