# Design Spec — Parallel R Implementation for the Guide

**Date:** 2026-06-10
**Status:** Draft for review
**Author:** Aaron Schroeder (with Claude)

## 1. Summary

Add a parallel **R** implementation to the "Creating Local-Level Geographic
Datasets" guide so the worked example is shown in both Python and R. The guide
currently says the example is "implemented in Python; an R implementation is
forthcoming." The R counterpart is now feasible because the
[`sdc.redistribute`](https://github.com/dads2busy/sdc.redistribute) R package
(the R sibling of the Python `sdc-redistribute`) provides `redistribute_direct`
and `redistribute_parcels`.

The R parallel covers the **methodological core** (redistribute → combine →
validate, plus the parcel second approach) as a runnable R pipeline that reads
the same intermediate data the Python pipeline produces. Data acquisition is
shown as an R **recipe** (not re-run). The Python pipeline is unchanged.

## 2. Goals

- A runnable, idiomatic R pipeline (`sf` + `sdc.redistribute`) reproducing the
  redistribution/combine/validate stages, verifiable against the Python outputs.
- Guide parity: per-stage Python|R tabs in the worked example and a generated R
  code appendix mirroring the Python appendix.
- Single source of truth: the R appendix is generated from `pipeline-r/*.R`,
  exactly as the Python appendix is generated from `pipeline/*.py`.
- Prose updated from "R forthcoming" to "shown in both Python and R."

## 3. Non-goals

- Re-implementing data acquisition (Census API, Ookla S3, parcel FeatureServer)
  as runnable R. Acquisition is a recipe only (`tidycensus`/`tigris`/`ooklaOpenDataR`).
- Executing R during `quarto render` or in CI. R is shown as static code; parity
  is verified locally (the `data/` intermediates are API-key-gated and gitignored).
- Any change to the Python pipeline or to the numbers/figures in the guide.
- Putting the R pipeline in an `R/` directory (that connotes an R package); it
  lives in `pipeline-r/`.

## 4. The R pipeline (`pipeline-r/`)

Mirrors `pipeline/` in module order. Reads the intermediate GeoJSON/CSV files the
Python pipeline writes into `data/`; uses `sf` for geometry and
`sdc.redistribute` for redistribution.

| File | Responsibility (parallels) |
|------|----------------------------|
| `config.R` | Shared `data/` paths and constants (Arlington FIPS, ACS count vars). |
| `redistribute_income.R` | `redistribute_direct(block_groups, civic, extensive = c("agg_income","households"))`; derive `mean_income = agg_income / households`. Parallels `redistribute_income.py`. |
| `redistribute_broadband.R` | Build `d_product = download_mbps * tests`; `redistribute_direct(tiles, civic, extensive = c("tests","d_product"))`; derive count-weighted `download_mbps = d_product / tests` (and upload likewise). Parallels `redistribute_broadband.py`. |
| `redistribute_income_parcels.R` | `redistribute_parcels(block_groups, civic, parcels, extensive = "agg_income", weights = "units")` (+ households) for the dasymetric second approach. Parallels `redistribute_income_parcels.py`. |
| `combine.R` | Join income + broadband onto civic polygons; compute income-to-speed ratio and bivariate income×speed classes. Parallels `combine.py`. |
| `compare_methods.R` | Area-weighted vs parcel-weighted income difference per civic association. Parallels `compare_methods.py`. |
| `validate.R` | Assert household/income totals preserved and no negative speeds/incomes. Parallels `validate.py`. |
| `run.R` | Orchestrate the stages end to end. Parallels `run.py`. |
| `acquire-recipe.R` | **Recipe only, not executed.** `tidycensus`/`tigris`/`ooklaOpenDataR` calls that would produce the same intermediates. Parallels the `acquire_*.py` modules at the recipe level. |
| `compare_to_python.R` | Parity check (see §5). |

The exact source-data column names will be read from the actual intermediate
files and Python modules during implementation; the table above states intent.

## 5. Parity verification (local)

`pipeline-r/compare_to_python.R`:

- Reads the R pipeline outputs and the Python outputs (`data/civic_combined.geojson`,
  `data/civic_income_comparison.geojson`, etc.).
- Asserts per-civic-association `mean_income` and `download_mbps` agree within a
  documented tolerance. A small relative tolerance (e.g. <= 1%) absorbs expected
  differences between the GEOS/`sf` and shapely/`geopandas` geometry engines.
- Prints a concise pass/fail summary with the max observed difference.

This is a **local author step**, run after the Python pipeline has produced the
intermediates. It is not part of CI, because `data/` is gitignored and gated on
a Census API key + network access.

## 6. Guide integration

- **`guide/04-worked-example.qmd`**: convert the per-stage Python `callout-note`
  snippets into `::: {.panel-tabset}` blocks with **Python** and **R** tabs, for
  the redistribution stages (income, broadband, parcels). Prose stays
  language-neutral.
- **`guide/09-code-r.qmd`** (new): generated R appendix mirroring `08-code.qmd`,
  embedding `pipeline-r/*.R` verbatim with per-module blurbs. Header notes it is
  built on the `sdc.redistribute` R package and is generated from `pipeline-r/`.
- **`guide/_quarto.yml`**: add `09-code-r.qmd` to the chapter list after
  `08-code.qmd`.
- **`scripts/build_code_appendix.py`**: generalize so one script generates both
  the Python appendix (`08-code.qmd` from `pipeline/*.py`) and the R appendix
  (`09-code-r.qmd` from `pipeline-r/*.R`). Keeps both appendices in lockstep with
  their source.
- **Prose updates**: `guide/the-gap.qmd` ("implemented in Python. An R
  implementation is forthcoming.") -> the example is shown in both Python and R.
  `guide/07-apply-it.qmd` R paragraph updated to point at the now-real
  `sdc.redistribute` package and the included `pipeline-r/` pipeline.

## 7. Dependencies

- R: `sf`, `sdc.redistribute` (installed from GitHub via
  `pak::pak("dads2busy/sdc.redistribute")` until it is on CRAN).
- Recipe references only: `tidycensus`/`tigris`/`ooklaOpenDataR`.
- Guide build is unchanged: R is not required to `quarto render` (R appears as
  static fenced code, like the Python appendix).

## 8. Success criteria

- `pipeline-r/run.R` runs against existing `data/` intermediates and writes R
  outputs without error.
- `pipeline-r/compare_to_python.R` reports the R civic-association `mean_income`
  and `download_mbps` match the Python outputs within tolerance.
- The worked-example chapter shows Python|R tabs; `09-code-r.qmd` is generated
  and renders; the guide builds (`quarto render`) with the new chapter.
- "Forthcoming" prose is replaced; no Python numbers/figures change.

## 9. Em-dash / prose conventions

Guide prose stays em-dash-free and in a formal register, per the existing
humanizer pass. New prose (chapter edits, appendix blurbs) follows the same rule.
