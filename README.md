# Galed

Post-processing pipeline for the transcription of an archaeological
field notebook on Transkribus (collection `2224542`, document
`15908163`), plus the related Khirbat al-Arais North collection
(`2388662`). The notebook is hand-written Hebrew interleaved with LTR
runs (Roman numerals for strata, dates, site codes), and the pipeline's
job is to surface and fix the systematic issues that show up in HTR
output and in transcriber edits.

## Repo map

```
code/
  transkribus/       legacy Transkribus REST client + pull/push CLI
  diagnostics/       scripts that scan PAGE-XML and report issues
data/
  notebook_15908163/page/        PAGE-XML pulled from doc 15908163 (89 pp., GT)
  khirbat_al_arais_15642624/page/   PAGE-XML, 30 pp., status NEW
  khirbat_al_arais_15642625/page/   PAGE-XML, 22 pp., status NEW
  khirbat_al_arais_15642626/page/   PAGE-XML, 77 pp., status NEW
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
