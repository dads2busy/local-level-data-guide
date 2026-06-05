# Design Spec — `sdc.redistribute` R Package

**Date:** 2026-06-05
**Status:** Draft for review
**Author:** Aaron Schroeder (with Claude)

## 1. Summary

Build an R package, **`sdc.redistribute`**, that redistributes attribute values
from one set of polygons onto another. It is the R counterpart to the Python
[`sdc-redistribute`](https://github.com/dads2busy/Social-Data-Commons) package
and is intended for eventual submission to **CRAN**.

The first release ships **two methods**, both exposed through one consistent,
`sf`-native API:

- **`redistribute_direct`** — classic area-weighted areal interpolation.
- **`redistribute_parcels`** — dasymetric redistribution using a point layer
  (e.g. parcel centroids), distributing source values across the points that
  fall inside each source polygon and reaggregating to targets.

The package's differentiator on CRAN is shipping the **dasymetric parcel method**
alongside area weighting in a single package; existing CRAN tools (`areal`,
`sf::st_interpolate_aw`) cover only the area-weighted case.

## 2. Goals

- A small, dependency-light, CRAN-quality R package (`Imports: sf` only).
- Idiomatic R API: `sf` in, `sf` out; `extensive`/`intensive` variable handling
  matching `areal` / `sf::st_interpolate_aw` conventions, so the package is
  familiar to R users and CRAN reviewers.
- Methodologically correct: extensive (count) measures preserve totals; intensive
  (rate/density) measures use area-weighted means.
- A clean forward path to the PUMS household-size-weighted parcel method via a
  `weights` argument, without a future API break.
- `R CMD check --as-cran` clean (0 errors / 0 warnings / 0 notes); fast, runnable
  examples; full roxygen2 docs; two vignettes; a pkgdown site.
- Its own standalone git repository with the package at the repo root.

## 3. Non-goals (v1)

- The PUMS household-size-weighted parcel method (`redistribute_parcel_pums_adj`
  from the original `uva-bi-sdad/redistribute`). Designed for, not built in v1.
- Any SDC pipeline wrapper (`run_redistribution`, `pipeline.yaml` parsing,
  `_geo10`/`_geo20` vintage-suffix logic). Too project-specific for CRAN; stays
  in the SDC ecosystem if needed.
- File-path / GeoJSON-reading inputs. The package operates on `sf` objects;
  reading files is the caller's job (keeps the package testable and dependency-light).
- Wiring the package into the guide's parcel chapter (separate follow-up).

## 4. Public API

Both functions take `sf` polygon layers and return the `target` layer with new
interpolated columns appended.

### 4.1 `redistribute_direct`

```r
redistribute_direct(
  source,                 # sf polygon layer carrying the values
  target,                 # sf polygon layer to estimate values for
  extensive = NULL,       # character: count columns (total-preserving)
  intensive = NULL,       # character: rate/density columns (area-weighted mean)
  preserve_totals = TRUE, # rescale extensive so sum(target) == sum(source)
  suffix = NULL           # optional string appended to new column names
)
```

Algorithm:

1. Validate inputs (both `sf`; named columns present; projected CRS — see §5.1).
   Transform `target` to `source` CRS if they differ.
2. `sf::st_intersection(source, target)`, `keep` geometry type polygons only;
   compute the area of each intersection piece.
3. **Extensive:** weight = `intersect_area / source_area`; piece value =
   `source_value * weight`; sum pieces per target; if `preserve_totals`, rescale
   each column so the target sum equals the source sum.
4. **Intensive:** weight = `intersect_area / target_area`; target value =
   `sum(source_value * weight)` (area-weighted mean within each target).
5. Return `target` with one new column per input column (optionally `+ suffix`).

### 4.2 `redistribute_parcels`

```r
redistribute_parcels(
  source,                 # sf polygon layer carrying the values
  target,                 # sf polygon layer to estimate values for
  points,                 # sf POINT layer (e.g. parcel centroids)
  extensive = NULL,       # character: count columns to distribute across points
  weights = NULL,         # optional points column to weight by (equal if NULL)
  suffix = NULL
)
```

Algorithm:

1. Validate inputs; align CRS across `source`, `target`, `points`.
2. Assign each point to a source polygon (`sf::st_join`, `within`).
3. Distribute each source extensive value across its points: equally, or in
   proportion to the `weights` column if supplied.
4. Assign points to target polygons; sum point-level values per target.
5. Return `target` with new columns (optionally `+ suffix`).

The `weights` argument is the deliberate extension point for the future PUMS
household-size-weighted method: that method becomes "compute a household-size
weight per parcel, pass it as `weights`," plus a helper to derive the weights.
v1 focuses on extensive measures for parcels; intensive-via-points is deferred.

## 5. Key design decisions

### 5.1 CRS handling
`redistribute_direct` requires a **projected** CRS (area must be metric). If the
input CRS is geographic, the function errors with a clear message telling the
caller to project (rather than silently reprojecting to a default, as the Python
package does). If `target`/`points` CRS differ from `source`, they are
transformed to the `source` CRS.

### 5.2 Total preservation
Extensive results are rescaled so each target column sums to the corresponding
source column total, absorbing edge slivers and boundary mismatch. Controlled by
`preserve_totals` (default `TRUE`).

### 5.3 Robustness / errors
`keep_geom_type = TRUE` on intersections; NA-safe aggregation; explicit, tested
errors for: non-`sf` inputs, named columns absent, geographic CRS, empty overlap,
and `weights` column absent from `points`.

### 5.4 Output shape
The returned object is the `target` `sf` with appended columns named after the
source columns (plus optional `suffix`). This is idiomatic (`areal`-style) and
distinct from the Python long-format `measure`/`value` + `_direct`/`_parcels`
output; cross-language output parity is explicitly a non-goal for v1.

## 6. Package structure

```
sdc.redistribute/                 # standalone repo; package at root
  DESCRIPTION
  NAMESPACE                       # roxygen2-generated
  LICENSE  LICENSE.md             # MIT (matches the Python package)
  NEWS.md
  cran-comments.md
  R/
    redistribute_direct.R
    redistribute_parcels.R
    utils.R                       # CRS validation, weighting, aggregation helpers
    sdc.redistribute-package.R    # package-level roxygen doc
  man/                            # generated
  tests/
    testthat.R
    testthat/
      test-direct.R
      test-parcels.R
      test-validation.R
  vignettes/
    introduction.Rmd
    method-comparison.Rmd
  inst/extdata/ or data/          # small synthetic example geometries
  README.Rmd  README.md
  _pkgdown.yml
  .github/workflows/
    R-CMD-check.yaml
    test-coverage.yaml
    pkgdown.yaml
  .Rbuildignore  .gitignore
```

### 6.1 Dependencies
- `Imports: sf` only. Aggregation in base R (`tapply`/`rowsum`/`aggregate`); no
  tidyverse, to keep the CRAN dependency surface minimal.
- `Suggests: testthat (>= 3.0), knitr, rmarkdown, areal, spelling, covr`.
- `Depends: R (>= 4.1)`.

## 7. Testing strategy

testthat (3rd edition):

- **Known-answer:** a tract split into two equal-area block groups returns 50/50
  for an extensive value; an intensive value returns the unchanged rate.
- **Property:** total preservation (`sum(target) == sum(source)` for extensive
  with `preserve_totals`); identity (source == target leaves values unchanged);
  parcels with exactly one point per source behaves like direct assignment.
- **Validation:** every error path in §5.3.
- Geometries are tiny synthetic `sf` objects built inline, so the suite and the
  examples run well within CRAN time limits.

## 8. CRAN-readiness checklist

- `R CMD check --as-cran`: 0 errors / 0 warnings / 0 notes.
- Every exported function: `@param`, `@return`, and runnable `@examples` (no
  `\dontrun` unless unavoidable; examples small and fast).
- `DESCRIPTION`: Title in Title Case (no package name / no "package"), full-sentence
  Description, `Authors@R` (with ORCID), `License: MIT + file LICENSE`,
  `URL`/`BugReports`, `Encoding: UTF-8`, `Language: en-US`.
- `spelling::spell_check_package()` clean.
- `cran-comments.md`; pre-submission checks on win-builder (release + devel) and
  R-hub.
- First CRAN release `0.1.0` after a `0.0.0.9000` development phase.

## 9. Documentation

- roxygen2 reference for both functions, with references to the areal-interpolation
  literature.
- Vignettes: **Introduction** (runnable quickstart) and **Method comparison**
  (direct vs parcels: assumptions, when each is appropriate), mirroring the Python
  docsite articles.
- `README.Rmd` with a runnable example and badges (CRAN status, R-CMD-check,
  codecov).
- pkgdown site deployed to GitHub Pages.

## 10. Roadmap (post-v1)

- **PUMS household-size-weighted parcels** via the `weights` hook plus a helper to
  derive per-parcel weights from PUMS household-size distributions.
- Optional long-format / cross-language parity helper, only if the SDC ecosystem
  needs identical output shapes across R and Python.
- Use `sdc.redistribute` as the R implementation in the guide's parcel chapter
  (the guide currently notes "an R implementation is forthcoming").

## 11. Resolved minor decisions

- **Example data:** examples build tiny `sf` geometries inline; vignettes use one
  small documented dataset shipped in `data/` (with a `data-raw/` generation
  script). Keeps examples self-contained and fast.
- **pkgdown hosting:** the standalone repo's own GitHub Pages, appropriate for a
  CRAN package with its own identity (not folded into the SDC docsite).
