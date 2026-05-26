# Galed

Post-processing pipeline for the transcription of an archaeological
field notebook on Transkribus (collection `2224542`, document
`15908163`), plus the related Khirbat al-Arais North collection
(`2388662`). The notebook is hand-written Hebrew interleaved with LTR
runs (Roman numerals for strata, dates, site codes), and the pipeline's
job is to surface and fix the systematic issues that show up in HTR
output and in transcriber edits.

## What this project is and what we've done

These are scanned pages of a hand-written archaeological field notebook.
A computer (the Transkribus platform) reads the handwriting and turns it
into typed text, and human transcribers correct what the computer gets
wrong. That automatic reading is never perfect, and it makes the *same
kinds of mistakes* over and over — so instead of fixing each page by
hand, we write small programs that find a recurring problem across all
the pages and fix it everywhere at once.

The text is especially tricky because it is mostly Hebrew (read
right-to-left) with bits of left-to-right material mixed in — dates,
Roman numerals for the dig's strata, site codes, measurements. Computers
often scramble the order of these mixed runs, which is a big part of what
we have to clean up.

So far we have built tools that:

- **Download and re-upload the pages safely.** We pull the latest
  transcription from Transkribus and, when we push corrections back, we
  always add a *new* version rather than overwriting anyone's work, so
  nothing is ever lost and several people can work at once.
- **Survey before fixing.** For each kind of problem we first run a
  read-only "diagnosis" that reports how often and where it occurs (for
  example, we found 255 dates across 87 pages and flagged the ones that
  are malformed or written in the wrong order). Only then do we write a
  fix.
- **Standardise punctuation.** Hebrew uses special marks (geresh and
  gershayim) that the computer transcribed inconsistently with a jumble
  of look-alike quote symbols. We unified them all (1,041 marks plus 82
  dash variants across 88 pages), because consistent symbols make the
  computer's reading more accurate over time.
- **Merge split lines.** The computer sometimes breaks one written line
  into several pieces. We detect those pieces and stitch them back into a
  single line, in the correct right-to-left order.
- **Investigate the date / direction problems.** We catalogued where
  dates and other left-to-right text come out reversed, as the basis for
  fixing the ordering next.

The corrected pages are kept separate from the originals (in a
`page_final/` folder) so the raw download is never altered. The sections
below are the technical reference for collaborators.

## Repo map

```
code/
  transkribus/       legacy Transkribus REST client + pull/push CLI
  diagnostics/       read-only scripts that scan PAGE-XML and report issues
  corrections/       scripts that rewrite PAGE-XML to fix the issues found
data/
  notebook_15908163/page/        PAGE-XML pulled from doc 15908163 (89 pp., GT)
  khirbat_al_arais_15642624/page/   PAGE-XML, 30 pp., status NEW
  khirbat_al_arais_15642625/page/   PAGE-XML, 22 pp., status NEW
  khirbat_al_arais_15642626/page/   PAGE-XML, 77 pp., status NEW
  khirbat_al_arais_15642626/images/ page scans (first 4 pp. only; see TRANSKRIBUS.md)
docs/
  COLLABORATORS.md         how to get GitHub + Transkribus access, env vars
  TRANSKRIBUS.md           sync CLI reference (pull, push, mapping images)
  TASKS.md                 open post-processing tasks (the to-do list)
  LTR_ORDER_FINDINGS.md    diagnostic report on bidi-reversed LTR runs
```

## Start here

- **New to the project?** Read [docs/COLLABORATORS.md](docs/COLLABORATORS.md)
  first — it covers requesting access and setting your Transkribus
  credentials in your shell environment.
- **Want to pull or push PAGE-XML?** See
  [docs/TRANSKRIBUS.md](docs/TRANSKRIBUS.md) for the CLI reference.
- **Need the page scans?** Images live next to the PAGE-XML in each doc's
  `images/` directory (currently only the first 4 pages of doc `15642626`).
  See [docs/TRANSKRIBUS.md](docs/TRANSKRIBUS.md#pulling-page-images) to pull more.
- **Looking for something to work on?** Open
  [docs/TASKS.md](docs/TASKS.md) — diagnostics and fixes for dates, LTR
  material, line unification, and gershayim normalization.
- **Curious about the bidi/LTR investigation?** Read
  [docs/LTR_ORDER_FINDINGS.md](docs/LTR_ORDER_FINDINGS.md) for the first
  diagnostic sweep (16 pages have reversed-order dates;
  [code/diagnostics/ltr_order.py](code/diagnostics/ltr_order.py)
  re-runs the check).

## Working principles

- **Credentials never live in the repo.** Each collaborator authenticates
  with their own Transkribus account via shell env vars.
- **Pushes are non-destructive.** Every `push` creates a new transcript
  layer parented to what you pulled — concurrent work doesn't overwrite.
- **Diagnose, then fix.** Each post-processing task is split into a
  survey pass (read-only, produces a report) and a correction pass
  (writes to `page_final/` or pushes back to Transkribus). Don't
  hand-edit pages before the survey tells you what the systematic issues
  actually are.
