# sdc.redistribute R Package Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `sdc.redistribute`, a CRAN-bound R package that redistributes attribute values between polygon layers via area-weighted (`redistribute_direct`) and parcel-centroid dasymetric (`redistribute_parcels`) methods.

**Architecture:** Two exported, `sf`-native functions returning the `target` layer with appended interpolated columns. Extensive (count) measures are total-preserving; intensive (rate) measures use area-weighted means. Internal helpers handle CRS validation and aggregation. `sf` is the only hard dependency; aggregation is base R.

**Tech Stack:** R (>= 4.1), `sf`, roxygen2, testthat (3e), pkgdown, GitHub Actions (`r-lib/actions`).

**Reference spec:** `docs/superpowers/specs/2026-06-05-sdc-redistribute-r-package-design.md` (in the `local_level_data` repo).

**Where the work happens:** a NEW standalone repo at `~/git/sdc.redistribute` (the package at the repo root). All paths below are relative to that repo unless noted. This plan file lives in `local_level_data`.

---

## File Structure

- `DESCRIPTION` — package metadata, deps, CRAN fields.
- `R/utils.R` — internal helpers: `.validate_layers`, `.require_projected`, `.align_crs`, `.suffixed`.
- `R/redistribute_direct.R` — `redistribute_direct()`.
- `R/redistribute_parcels.R` — `redistribute_parcels()`.
- `R/sdc.redistribute-package.R` — package-level roxygen doc + `@importFrom`.
- `R/data.R` — roxygen doc for the shipped example dataset.
- `data-raw/example_geographies.R` — generates the example dataset.
- `data/sdc_example.rda` — shipped example `sf` objects.
- `tests/testthat/test-direct.R`, `test-parcels.R`, `test-validation.R`.
- `vignettes/introduction.Rmd`, `vignettes/method-comparison.Rmd`.
- `README.Rmd` (+ generated `README.md`).
- `_pkgdown.yml`.
- `.github/workflows/R-CMD-check.yaml`, `test-coverage.yaml`, `pkgdown.yaml`.
- `NEWS.md`, `cran-comments.md`, `LICENSE`, `LICENSE.md`.

---

## Task 1: Scaffold the package repository

**Files:**
- Create: `~/git/sdc.redistribute/` (whole skeleton)
- Create: `DESCRIPTION`, `LICENSE`, `LICENSE.md`, `NEWS.md`, `.gitignore`, `.Rbuildignore`

- [ ] **Step 1: Create the package skeleton**

Run:
```bash
Rscript -e 'usethis::create_package("~/git/sdc.redistribute", fields = list(
  Package = "sdc.redistribute",
  Title = "Redistribute Values Between Geographic Areas",
  Version = "0.0.0.9000",
  Language = "en-US"
), open = FALSE, rstudio = FALSE)'
```
Expected: a new directory `~/git/sdc.redistribute` with `DESCRIPTION`, `R/`, `NAMESPACE`.

- [ ] **Step 2: Initialize git and testthat**

Run:
```bash
cd ~/git/sdc.redistribute && git init -b main
Rscript -e 'usethis::proj_set("~/git/sdc.redistribute"); usethis::use_testthat(3); usethis::use_mit_license("Aaron Schroeder")'
```
Expected: `tests/testthat/`, `tests/testthat.R`, `LICENSE`, `LICENSE.md` created.

- [ ] **Step 3: Write the full DESCRIPTION**

Overwrite `DESCRIPTION` with:
```
Package: sdc.redistribute
Title: Redistribute Values Between Geographic Areas
Version: 0.0.0.9000
Authors@R:
    person("Aaron", "Schroeder", email = "ads7fg@virginia.edu",
           role = c("aut", "cre"), comment = c(ORCID = "0000-0001-9985-1136"))
Description: Estimate attribute values for one set of polygons from values
    measured on a different, misaligned set. Provides area-weighted areal
    interpolation and a dasymetric method that distributes values across a
    point layer (such as parcel centroids). Count (extensive) measures are
    total-preserving; rate (intensive) measures use area-weighted means.
License: MIT + file LICENSE
Encoding: UTF-8
Language: en-US
Depends:
    R (>= 4.1)
Imports:
    sf
Suggests:
    testthat (>= 3.0.0),
    knitr,
    rmarkdown,
    areal,
    spelling,
    covr
Config/testthat/edition: 3
Roxygen: list(markdown = TRUE)
RoxygenNote: 7.3.2
URL: https://github.com/dads2busy/sdc.redistribute
BugReports: https://github.com/dads2busy/sdc.redistribute/issues
VignetteBuilder: knitr
```
(Replace the ORCID if it is not correct.)

- [ ] **Step 4: Add .Rbuildignore entries and NEWS**

Run:
```bash
cd ~/git/sdc.redistribute
Rscript -e 'usethis::proj_set("."); usethis::use_build_ignore(c("data-raw","^.*\\.Rproj$",".github","_pkgdown.yml","cran-comments.md","docs")); usethis::use_news_md(open = FALSE)'
```
Expected: `.Rbuildignore` updated, `NEWS.md` created.

- [ ] **Step 5: Verify the skeleton loads**

Run: `cd ~/git/sdc.redistribute && Rscript -e 'devtools::load_all(".")'`
Expected: loads with no error (no functions yet).

- [ ] **Step 6: Commit**

```bash
cd ~/git/sdc.redistribute
git add -A
git commit -m "chore: scaffold sdc.redistribute package"
```

---

## Task 2: Internal helpers (`R/utils.R`)

**Files:**
- Create: `R/utils.R`
- Test: `tests/testthat/test-validation.R`

- [ ] **Step 1: Write failing tests for the helpers**

Create `tests/testthat/test-validation.R`:
```r
box_sf <- function(xmin, ymin, xmax, ymax, crs = 3857, ...) {
  poly <- sf::st_polygon(list(rbind(
    c(xmin, ymin), c(xmax, ymin), c(xmax, ymax), c(xmin, ymax), c(xmin, ymin)
  )))
  sf::st_sf(..., geometry = sf::st_sfc(poly, crs = crs))
}

test_that(".validate_layers rejects non-sf and missing columns", {
  src <- box_sf(0, 0, 2, 2, pop = 100)
  tgt <- box_sf(0, 0, 1, 2)
  expect_error(.validate_layers(data.frame(), tgt, "pop"), "must be an sf")
  expect_error(.validate_layers(src, data.frame(), "pop"), "must be an sf")
  expect_error(.validate_layers(src, tgt, "nope"), "not found in .source.")
  expect_true(.validate_layers(src, tgt, "pop"))
})

test_that(".require_projected errors on geographic / missing CRS", {
  geo <- box_sf(0, 0, 1, 1, crs = 4326)
  expect_error(.require_projected(geo, "source"), "geographic CRS")
  nocrs <- box_sf(0, 0, 1, 1, crs = NA)
  expect_error(.require_projected(nocrs, "source"), "no CRS")
  proj <- box_sf(0, 0, 1, 1, crs = 3857)
  expect_silent(.require_projected(proj, "source"))
})

test_that(".align_crs transforms to the reference CRS", {
  ref <- box_sf(0, 0, 1, 1, crs = 3857)
  other <- box_sf(0, 0, 1, 1, crs = 4326)
  aligned <- .align_crs(other, ref)
  expect_equal(sf::st_crs(aligned), sf::st_crs(ref))
})
```

- [ ] **Step 2: Run to verify failure**

Run: `cd ~/git/sdc.redistribute && Rscript -e 'devtools::test(filter = "validation")'`
Expected: FAIL — `.validate_layers` etc. not found.

- [ ] **Step 3: Implement the helpers**

Create `R/utils.R`:
```r
# Internal helpers. Not exported.

.is_sf <- function(x) inherits(x, "sf")

.validate_layers <- function(source, target, cols = character()) {
  if (!.is_sf(source)) stop("`source` must be an sf object.", call. = FALSE)
  if (!.is_sf(target)) stop("`target` must be an sf object.", call. = FALSE)
  missing <- setdiff(cols, names(source))
  if (length(missing) > 0) {
    stop(sprintf("Column(s) not found in `source`: %s",
                 paste(missing, collapse = ", ")), call. = FALSE)
  }
  invisible(TRUE)
}

.require_projected <- function(x, name) {
  crs <- sf::st_crs(x)
  if (is.na(crs)) {
    stop(sprintf("`%s` has no CRS; set one with sf::st_crs() before redistributing.", name),
         call. = FALSE)
  }
  if (isTRUE(sf::st_is_longlat(x))) {
    stop(sprintf(paste0("`%s` uses a geographic CRS; project to a planar CRS ",
                        "(e.g. sf::st_transform()) before redistributing."), name),
         call. = FALSE)
  }
  invisible(x)
}

.align_crs <- function(x, ref) {
  if (sf::st_crs(x) != sf::st_crs(ref)) {
    x <- sf::st_transform(x, sf::st_crs(ref))
  }
  x
}

.suffixed <- function(col, suffix) {
  if (is.null(suffix)) col else paste0(col, suffix)
}
```

- [ ] **Step 4: Run to verify pass**

Run: `cd ~/git/sdc.redistribute && Rscript -e 'devtools::test(filter = "validation")'`
Expected: PASS (all tests in test-validation.R).

- [ ] **Step 5: Commit**

```bash
cd ~/git/sdc.redistribute
git add R/utils.R tests/testthat/test-validation.R
git commit -m "feat: add internal validation and CRS helpers"
```

---

## Task 3: `redistribute_direct` — extensive measures

**Files:**
- Create: `R/redistribute_direct.R`
- Test: `tests/testthat/test-direct.R`

- [ ] **Step 1: Write the failing test**

Create `tests/testthat/test-direct.R`:
```r
box_sf <- function(xmin, ymin, xmax, ymax, crs = 3857, ...) {
  poly <- sf::st_polygon(list(rbind(
    c(xmin, ymin), c(xmax, ymin), c(xmax, ymax), c(xmin, ymax), c(xmin, ymin)
  )))
  sf::st_sf(..., geometry = sf::st_sfc(poly, crs = crs))
}

test_that("extensive count splits by area share and preserves the total", {
  src <- box_sf(0, 0, 2, 2, pop = 100)
  tgt <- rbind(box_sf(0, 0, 1, 2, id = "A"), box_sf(1, 0, 2, 2, id = "B"))
  out <- redistribute_direct(src, tgt, extensive = "pop")
  expect_s3_class(out, "sf")
  expect_equal(out$pop, c(50, 50))
  expect_equal(sum(out$pop), sum(src$pop))
  expect_equal(out$id, c("A", "B"))  # target attributes retained
})
```

- [ ] **Step 2: Run to verify failure**

Run: `cd ~/git/sdc.redistribute && Rscript -e 'devtools::test(filter = "direct")'`
Expected: FAIL — `redistribute_direct` not found.

- [ ] **Step 3: Implement the extensive path**

Create `R/redistribute_direct.R`:
```r
#' Area-weighted redistribution between polygon layers
#'
#' @param source An `sf` polygon layer carrying the values to redistribute.
#' @param target An `sf` polygon layer to estimate values for.
#' @param extensive Character vector of count column names in `source` to
#'   redistribute as totals (area-share weighted, optionally rescaled to
#'   preserve the source total).
#' @param intensive Character vector of rate/density column names in `source`
#'   to redistribute as area-weighted means.
#' @param preserve_totals Logical; if `TRUE` (default) extensive results are
#'   rescaled so each target column sums to the source total.
#' @param suffix Optional string appended to each new column name.
#' @return The `target` layer (an `sf` object) with one new column per
#'   redistributed measure.
#' @export
redistribute_direct <- function(source, target, extensive = NULL,
                                intensive = NULL, preserve_totals = TRUE,
                                suffix = NULL) {
  .validate_layers(source, target, c(extensive, intensive))
  .require_projected(source, "source")
  target <- .align_crs(target, source)

  source[[".src_area"]] <- as.numeric(sf::st_area(source))
  target[[".tgt_id"]] <- seq_len(nrow(target))
  target[[".tgt_area"]] <- as.numeric(sf::st_area(target))

  src_cols <- c(".src_area", extensive, intensive)
  ints <- suppressWarnings(sf::st_intersection(
    source[, src_cols], target[, c(".tgt_id", ".tgt_area")]
  ))
  keep <- !is.na(sf::st_dimension(ints)) & sf::st_dimension(ints) == 2L
  ints <- ints[keep, ]
  ints[[".int_area"]] <- as.numeric(sf::st_area(ints))
  d <- sf::st_drop_geometry(ints)

  out <- target

  for (col in extensive) {
    piece <- d[[col]] * (d[[".int_area"]] / d[[".src_area"]])
    agg <- tapply(piece, d[[".tgt_id"]], sum, na.rm = TRUE)
    vals <- rep(0, nrow(target))
    vals[as.integer(names(agg))] <- as.numeric(agg)
    if (isTRUE(preserve_totals)) {
      src_total <- sum(source[[col]], na.rm = TRUE)
      tgt_total <- sum(vals)
      if (tgt_total > 0 && src_total > 0) vals <- vals * (src_total / tgt_total)
    }
    out[[.suffixed(col, suffix)]] <- vals
  }

  for (col in intensive) {
    piece <- d[[col]] * (d[[".int_area"]] / d[[".tgt_area"]])
    agg <- tapply(piece, d[[".tgt_id"]], sum, na.rm = TRUE)
    vals <- rep(NA_real_, nrow(target))
    vals[as.integer(names(agg))] <- as.numeric(agg)
    out[[.suffixed(col, suffix)]] <- vals
  }

  out[[".tgt_id"]] <- NULL
  out[[".tgt_area"]] <- NULL
  out
}
```

- [ ] **Step 4: Run to verify pass**

Run: `cd ~/git/sdc.redistribute && Rscript -e 'devtools::test(filter = "direct")'`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
cd ~/git/sdc.redistribute
git add R/redistribute_direct.R tests/testthat/test-direct.R
git commit -m "feat: redistribute_direct extensive area-weighting"
```

---

## Task 4: `redistribute_direct` — intensive, suffix, identity

**Files:**
- Modify: `tests/testthat/test-direct.R`

- [ ] **Step 1: Add failing tests for intensive, suffix, identity**

Append to `tests/testthat/test-direct.R`:
```r
test_that("intensive measure is an area-weighted mean", {
  # Two source halves with different densities; target is the whole extent.
  src <- rbind(box_sf(0, 0, 1, 2, dens = 10), box_sf(1, 0, 2, 2, dens = 30))
  tgt <- box_sf(0, 0, 2, 2, id = "whole")
  out <- redistribute_direct(src, tgt, intensive = "dens")
  expect_equal(out$dens, 20)  # equal areas -> mean of 10 and 30
})

test_that("suffix renames new columns and keeps source values out of target", {
  src <- box_sf(0, 0, 2, 2, pop = 80)
  tgt <- rbind(box_sf(0, 0, 1, 2, id = "A"), box_sf(1, 0, 2, 2, id = "B"))
  out <- redistribute_direct(src, tgt, extensive = "pop", suffix = "_direct")
  expect_true("pop_direct" %in% names(out))
  expect_false("pop" %in% names(out))
})

test_that("identity: redistributing onto the same geometry is a no-op", {
  src <- rbind(box_sf(0, 0, 1, 1, pop = 5), box_sf(1, 0, 2, 1, pop = 7))
  out <- redistribute_direct(src, src, extensive = "pop")
  expect_equal(sort(round(out$pop, 6)), c(5, 7))
})
```

- [ ] **Step 2: Run to verify**

Run: `cd ~/git/sdc.redistribute && Rscript -e 'devtools::test(filter = "direct")'`
Expected: PASS (the Task 3 implementation already covers intensive/suffix). If the identity test fails on floating-point, the implementation is wrong — fix before continuing.

- [ ] **Step 3: Commit**

```bash
cd ~/git/sdc.redistribute
git add tests/testthat/test-direct.R
git commit -m "test: cover intensive, suffix, and identity for redistribute_direct"
```

---

## Task 5: `redistribute_direct` — validation errors

**Files:**
- Modify: `tests/testthat/test-direct.R`

- [ ] **Step 1: Add failing tests for the error paths**

Append to `tests/testthat/test-direct.R`:
```r
test_that("redistribute_direct validates inputs", {
  src <- box_sf(0, 0, 2, 2, pop = 100)
  tgt <- box_sf(0, 0, 1, 2)
  expect_error(redistribute_direct(src, tgt, extensive = "missing"),
               "not found in .source.")
  geo <- box_sf(0, 0, 2, 2, crs = 4326, pop = 100)
  expect_error(redistribute_direct(geo, tgt, extensive = "pop"),
               "geographic CRS")
})

test_that("redistribute_direct reprojects target to source CRS", {
  src <- box_sf(0, 0, 2, 2, pop = 100)               # EPSG:3857
  tgt <- sf::st_transform(
    rbind(box_sf(0, 0, 1, 2, id = "A"), box_sf(1, 0, 2, 2, id = "B")), 4326)
  out <- redistribute_direct(src, tgt, extensive = "pop")
  expect_equal(sf::st_crs(out), sf::st_crs(src))
  expect_equal(round(sum(out$pop)), 100)
})
```

- [ ] **Step 2: Run to verify**

Run: `cd ~/git/sdc.redistribute && Rscript -e 'devtools::test(filter = "direct")'`
Expected: PASS (helpers from Task 2 already enforce this).

- [ ] **Step 3: Commit**

```bash
cd ~/git/sdc.redistribute
git add tests/testthat/test-direct.R
git commit -m "test: cover validation and reprojection for redistribute_direct"
```

---

## Task 6: `redistribute_parcels` — equal-weight dasymetric

**Files:**
- Create: `R/redistribute_parcels.R`
- Test: `tests/testthat/test-parcels.R`

- [ ] **Step 1: Write the failing test**

Create `tests/testthat/test-parcels.R`:
```r
box_sf <- function(xmin, ymin, xmax, ymax, crs = 3857, ...) {
  poly <- sf::st_polygon(list(rbind(
    c(xmin, ymin), c(xmax, ymin), c(xmax, ymax), c(xmin, ymax), c(xmin, ymin)
  )))
  sf::st_sf(..., geometry = sf::st_sfc(poly, crs = crs))
}

pts_sf <- function(coords, crs = 3857, ...) {
  g <- sf::st_sfc(lapply(seq_len(nrow(coords)),
                         function(i) sf::st_point(coords[i, ])), crs = crs)
  sf::st_sf(..., geometry = g)
}

test_that("parcels spread a count evenly across contained points", {
  # Source has 100 pop and 4 parcels (3 left of x=1, 1 right of x=1).
  src <- box_sf(0, 0, 2, 2, pop = 100)
  tgt <- rbind(box_sf(0, 0, 1, 2, id = "A"), box_sf(1, 0, 2, 2, id = "B"))
  pts <- pts_sf(rbind(c(0.5, 0.5), c(0.5, 1.5), c(0.5, 1.0), c(1.5, 1.0)))
  out <- redistribute_parcels(src, tgt, pts, extensive = "pop")
  # 25 pop per parcel -> A gets 3 parcels (75), B gets 1 (25)
  expect_equal(out$pop[out$id == "A"], 75)
  expect_equal(out$pop[out$id == "B"], 25)
  expect_equal(sum(out$pop), 100)
})
```

- [ ] **Step 2: Run to verify failure**

Run: `cd ~/git/sdc.redistribute && Rscript -e 'devtools::test(filter = "parcels")'`
Expected: FAIL — `redistribute_parcels` not found.

- [ ] **Step 3: Implement parcels**

Create `R/redistribute_parcels.R`:
```r
#' Dasymetric redistribution via a point layer
#'
#' Distributes each `source` value across the points (e.g. parcel centroids)
#' that fall inside it, then reaggregates the point-level values to `target`
#' polygons. With `weights = NULL` the value is split evenly across points;
#' otherwise it is split in proportion to a points column (the extension point
#' for household-size or unit-count weighting).
#'
#' @param source An `sf` polygon layer carrying the values to redistribute.
#' @param target An `sf` polygon layer to estimate values for.
#' @param points An `sf` point layer (e.g. parcel centroids).
#' @param extensive Character vector of count column names in `source`.
#' @param weights Optional name of a numeric column in `points` to weight by.
#' @param suffix Optional string appended to each new column name.
#' @return The `target` layer (an `sf` object) with one new column per measure.
#' @export
redistribute_parcels <- function(source, target, points, extensive = NULL,
                                 weights = NULL, suffix = NULL) {
  .validate_layers(source, target, extensive)
  if (!.is_sf(points)) stop("`points` must be an sf object.", call. = FALSE)
  if (!is.null(weights) && !weights %in% names(points)) {
    stop(sprintf("`weights` column '%s' not found in `points`.", weights),
         call. = FALSE)
  }
  points <- .align_crs(points, source)
  target <- .align_crs(target, source)

  source[[".src_id"]] <- seq_len(nrow(source))
  target[[".tgt_id"]] <- seq_len(nrow(target))

  pts <- sf::st_join(points, source[, ".src_id"], join = sf::st_within)
  pts <- pts[!is.na(pts[[".src_id"]]), ]
  pts <- sf::st_join(pts, target[, ".tgt_id"], join = sf::st_within)
  pts <- pts[!is.na(pts[[".tgt_id"]]), ]

  d <- sf::st_drop_geometry(pts)
  d[[".w"]] <- if (is.null(weights)) 1 else d[[weights]]
  wsum <- tapply(d[[".w"]], d[[".src_id"]], sum, na.rm = TRUE)
  d[[".wsum"]] <- as.numeric(wsum[as.character(d[[".src_id"]])])

  src_vals <- sf::st_drop_geometry(source)[, c(".src_id", extensive), drop = FALSE]
  d <- merge(d, src_vals, by = ".src_id")

  out <- target
  for (col in extensive) {
    piece <- d[[col]] * (d[[".w"]] / d[[".wsum"]])
    agg <- tapply(piece, d[[".tgt_id"]], sum, na.rm = TRUE)
    vals <- rep(0, nrow(target))
    vals[as.integer(names(agg))] <- as.numeric(agg)
    out[[.suffixed(col, suffix)]] <- vals
  }

  out[[".tgt_id"]] <- NULL
  out
}
```

- [ ] **Step 4: Run to verify pass**

Run: `cd ~/git/sdc.redistribute && Rscript -e 'devtools::test(filter = "parcels")'`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
cd ~/git/sdc.redistribute
git add R/redistribute_parcels.R tests/testthat/test-parcels.R
git commit -m "feat: redistribute_parcels dasymetric redistribution"
```

---

## Task 7: `redistribute_parcels` — weights and validation

**Files:**
- Modify: `tests/testthat/test-parcels.R`

- [ ] **Step 1: Add failing tests for weighting and errors**

Append to `tests/testthat/test-parcels.R`:
```r
test_that("weights split the value in proportion to a points column", {
  src <- box_sf(0, 0, 2, 2, pop = 100)
  tgt <- rbind(box_sf(0, 0, 1, 2, id = "A"), box_sf(1, 0, 2, 2, id = "B"))
  # One point each side; right-side point carries 3x the weight.
  pts <- pts_sf(rbind(c(0.5, 1.0), c(1.5, 1.0)), units = c(1, 3))
  out <- redistribute_parcels(src, tgt, pts, extensive = "pop", weights = "units")
  expect_equal(out$pop[out$id == "A"], 25)  # 1/(1+3) * 100
  expect_equal(out$pop[out$id == "B"], 75)  # 3/(1+3) * 100
})

test_that("redistribute_parcels validates inputs", {
  src <- box_sf(0, 0, 2, 2, pop = 100)
  tgt <- box_sf(0, 0, 1, 2)
  pts <- pts_sf(rbind(c(0.5, 1.0)))
  expect_error(redistribute_parcels(src, tgt, data.frame(), extensive = "pop"),
               "`points` must be an sf")
  expect_error(redistribute_parcels(src, tgt, pts, extensive = "pop", weights = "nope"),
               "not found in .points.")
})
```

- [ ] **Step 2: Run to verify**

Run: `cd ~/git/sdc.redistribute && Rscript -e 'devtools::test(filter = "parcels")'`
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
cd ~/git/sdc.redistribute
git add tests/testthat/test-parcels.R
git commit -m "test: cover weighting and validation for redistribute_parcels"
```

---

## Task 8: Roxygen docs, NAMESPACE, package doc

**Files:**
- Create: `R/sdc.redistribute-package.R`
- Generate: `NAMESPACE`, `man/*.Rd`

- [ ] **Step 1: Add the package-level doc with imports**

Create `R/sdc.redistribute-package.R`:
```r
#' @keywords internal
"_PACKAGE"

#' @importFrom sf st_area st_crs st_dimension st_drop_geometry st_intersection
#' @importFrom sf st_is_longlat st_join st_transform st_within
NULL
```

- [ ] **Step 2: Generate documentation and NAMESPACE**

Run: `cd ~/git/sdc.redistribute && Rscript -e 'devtools::document()'`
Expected: `NAMESPACE` exports `redistribute_direct`, `redistribute_parcels`; `man/redistribute_direct.Rd`, `man/redistribute_parcels.Rd`, `man/sdc.redistribute-package.Rd` created.

- [ ] **Step 3: Add runnable @examples to each function**

In `R/redistribute_direct.R`, add above `@export`:
```r
#' @examples
#' src <- sf::st_sf(pop = 100, geometry = sf::st_sfc(
#'   sf::st_polygon(list(rbind(c(0,0), c(2,0), c(2,2), c(0,2), c(0,0)))),
#'   crs = 3857))
#' tgt <- sf::st_sf(id = c("A", "B"), geometry = sf::st_sfc(
#'   sf::st_polygon(list(rbind(c(0,0), c(1,0), c(1,2), c(0,2), c(0,0)))),
#'   sf::st_polygon(list(rbind(c(1,0), c(2,0), c(2,2), c(1,2), c(1,0)))),
#'   crs = 3857))
#' redistribute_direct(src, tgt, extensive = "pop")
```
In `R/redistribute_parcels.R`, add above `@export`:
```r
#' @examples
#' src <- sf::st_sf(pop = 100, geometry = sf::st_sfc(
#'   sf::st_polygon(list(rbind(c(0,0), c(2,0), c(2,2), c(0,2), c(0,0)))),
#'   crs = 3857))
#' tgt <- sf::st_sf(id = c("A", "B"), geometry = sf::st_sfc(
#'   sf::st_polygon(list(rbind(c(0,0), c(1,0), c(1,2), c(0,2), c(0,0)))),
#'   sf::st_polygon(list(rbind(c(1,0), c(2,0), c(2,2), c(1,2), c(1,0)))),
#'   crs = 3857))
#' pts <- sf::st_sf(geometry = sf::st_sfc(
#'   sf::st_point(c(0.5, 1)), sf::st_point(c(1.5, 1)), crs = 3857))
#' redistribute_parcels(src, tgt, pts, extensive = "pop")
```

- [ ] **Step 4: Re-document and run examples**

Run: `cd ~/git/sdc.redistribute && Rscript -e 'devtools::document(); devtools::run_examples()'`
Expected: examples run with no error.

- [ ] **Step 5: Commit**

```bash
cd ~/git/sdc.redistribute
git add R/ NAMESPACE man/
git commit -m "docs: roxygen documentation, NAMESPACE, runnable examples"
```

---

## Task 9: Shipped example dataset

**Files:**
- Create: `data-raw/example_geographies.R`
- Create: `data/sdc_example.rda`
- Create: `R/data.R`

- [ ] **Step 1: Write the dataset generator**

Create `data-raw/example_geographies.R`:
```r
# Generates `sdc_example`: a tiny synthetic set of sf layers for examples and
# vignettes. Run with: source("data-raw/example_geographies.R")
make_box <- function(xmin, ymin, xmax, ymax) {
  sf::st_polygon(list(rbind(
    c(xmin, ymin), c(xmax, ymin), c(xmax, ymax), c(xmin, ymax), c(xmin, ymin))))
}

source_geo <- sf::st_sf(
  tract = c("T1", "T2"),
  pop = c(120, 80),
  geometry = sf::st_sfc(make_box(0, 0, 2, 2), make_box(2, 0, 4, 2), crs = 3857))

target_geo <- sf::st_sf(
  nbhd = c("N1", "N2", "N3"),
  geometry = sf::st_sfc(
    make_box(0, 0, 1.5, 2), make_box(1.5, 0, 2.5, 2), make_box(2.5, 0, 4, 2),
    crs = 3857))

set.seed(1)
pc <- expand.grid(x = seq(0.25, 3.75, by = 0.5), y = seq(0.25, 1.75, by = 0.5))
parcels <- sf::st_sf(
  units = sample(1:4, nrow(pc), replace = TRUE),
  geometry = sf::st_sfc(lapply(seq_len(nrow(pc)),
    function(i) sf::st_point(c(pc$x[i], pc$y[i]))), crs = 3857))

sdc_example <- list(source = source_geo, target = target_geo, parcels = parcels)

usethis::use_data(sdc_example, overwrite = TRUE)
```

- [ ] **Step 2: Generate the data**

Run: `cd ~/git/sdc.redistribute && Rscript -e 'source("data-raw/example_geographies.R")'`
Expected: `data/sdc_example.rda` created.

- [ ] **Step 3: Document the dataset**

Create `R/data.R`:
```r
#' Synthetic example geographies
#'
#' A small, self-contained set of `sf` layers used in examples and vignettes.
#'
#' @format A named list with three `sf` elements:
#' \describe{
#'   \item{source}{Two source polygons (`tract`, `pop`).}
#'   \item{target}{Three target polygons (`nbhd`).}
#'   \item{parcels}{Parcel centroid points (`units`).}
#' }
"sdc_example"
```

- [ ] **Step 4: Re-document and verify load**

Run: `cd ~/git/sdc.redistribute && Rscript -e 'devtools::document(); devtools::load_all("."); stopifnot(length(sdc_example) == 3L)'`
Expected: no error.

- [ ] **Step 5: Commit**

```bash
cd ~/git/sdc.redistribute
git add data-raw/ data/ R/data.R man/sdc_example.Rd
git commit -m "data: add synthetic sdc_example geographies"
```

---

## Task 10: README and vignettes

**Files:**
- Create: `README.Rmd` (+ generated `README.md`)
- Create: `vignettes/introduction.Rmd`, `vignettes/method-comparison.Rmd`

- [ ] **Step 1: Create README.Rmd**

Run: `cd ~/git/sdc.redistribute && Rscript -e 'usethis::use_readme_rmd(open = FALSE)'`
Then overwrite the body of `README.Rmd` (keep the generated YAML header and the setup chunk) with:
```markdown
# sdc.redistribute

<!-- badges: start -->
[![R-CMD-check](https://github.com/dads2busy/sdc.redistribute/actions/workflows/R-CMD-check.yaml/badge.svg)](https://github.com/dads2busy/sdc.redistribute/actions/workflows/R-CMD-check.yaml)
<!-- badges: end -->

Redistribute attribute values from one set of polygons onto another, by
area weighting (`redistribute_direct`) or by a dasymetric point layer such as
parcel centroids (`redistribute_parcels`).

## Installation

```r
# install.packages("pak")
pak::pak("dads2busy/sdc.redistribute")
```

## Example

```{r example}
library(sdc.redistribute)
data(sdc_example)
redistribute_direct(sdc_example$source, sdc_example$target, extensive = "pop")
```
```

- [ ] **Step 2: Render the README**

Run: `cd ~/git/sdc.redistribute && Rscript -e 'devtools::build_readme()'`
Expected: `README.md` generated with the rendered example output.

- [ ] **Step 3: Create the Introduction vignette**

Run: `cd ~/git/sdc.redistribute && Rscript -e 'usethis::use_vignette("introduction", "Introduction to sdc.redistribute")'`
Replace its body after the setup chunk with:
```markdown
`sdc.redistribute` moves measured values from a *source* set of polygons onto a
*target* set that does not share the same boundaries.

```{r}
library(sdc.redistribute)
data(sdc_example)

# Area-weighted: split tract population onto neighborhoods.
redistribute_direct(sdc_example$source, sdc_example$target, extensive = "pop")

# Dasymetric: weight the split by parcels (here, by unit count).
redistribute_parcels(
  sdc_example$source, sdc_example$target, sdc_example$parcels,
  extensive = "pop", weights = "units")
```

Use `extensive` for counts (totals are preserved) and `intensive` for rates
(area-weighted means).
```

- [ ] **Step 4: Create the Method-comparison vignette**

Run: `cd ~/git/sdc.redistribute && Rscript -e 'usethis::use_vignette("method-comparison", "Comparing redistribution methods")'`
Replace its body after the setup chunk with:
```markdown
Both methods estimate target values from source values; they differ in the
weight each assigns to a piece of a source polygon.

- **`redistribute_direct`** assumes the measure is spread *uniformly by area*
  within each source polygon. It needs only the two polygon layers.
- **`redistribute_parcels`** assumes the measure follows a *point layer* (e.g.
  parcels), which usually tracks where people and housing actually are. It is
  more accurate where such points exist, at the cost of needing that layer.

```{r}
library(sdc.redistribute)
data(sdc_example)

direct  <- redistribute_direct(sdc_example$source, sdc_example$target,
                               extensive = "pop", suffix = "_direct")
parcels <- redistribute_parcels(sdc_example$source, sdc_example$target,
                                sdc_example$parcels, extensive = "pop",
                                suffix = "_parcels")

cbind(sf::st_drop_geometry(direct["pop_direct"]),
      sf::st_drop_geometry(parcels["pop_parcels"]))
```

Both preserve the source total; they differ in how they place it.
```

- [ ] **Step 5: Build vignettes to verify**

Run: `cd ~/git/sdc.redistribute && Rscript -e 'devtools::build_vignettes()'`
Expected: both vignettes knit without error.

- [ ] **Step 6: Commit**

```bash
cd ~/git/sdc.redistribute
git add README.Rmd README.md vignettes/
git commit -m "docs: README and introduction/method-comparison vignettes"
```

---

## Task 11: pkgdown site and GitHub Actions CI

**Files:**
- Create: `_pkgdown.yml`, `.github/workflows/R-CMD-check.yaml`, `test-coverage.yaml`, `pkgdown.yaml`

- [ ] **Step 1: Add CI and pkgdown via usethis**

Run:
```bash
cd ~/git/sdc.redistribute
Rscript -e 'usethis::proj_set("."); usethis::use_github_action("check-standard"); usethis::use_github_action("test-coverage"); usethis::use_pkgdown_github_pages()'
```
Expected: the three workflow files under `.github/workflows/` and a `_pkgdown.yml`. (If `use_pkgdown_github_pages()` requires a GitHub remote and none exists yet, run `usethis::use_pkgdown()` instead to create `_pkgdown.yml`, and add the `pkgdown.yaml` workflow manually in Step 2.)

- [ ] **Step 2: Ensure the pkgdown workflow exists**

If `pkgdown.yaml` was not created in Step 1, run:
```bash
cd ~/git/sdc.redistribute && Rscript -e 'usethis::use_github_action("pkgdown")'
```
Expected: `.github/workflows/pkgdown.yaml` present.

- [ ] **Step 3: Build the pkgdown site locally**

Run: `cd ~/git/sdc.redistribute && Rscript -e 'pkgdown::build_site(preview = FALSE)'`
Expected: site builds into `docs/` with reference + both vignettes, no error.

- [ ] **Step 4: Commit**

```bash
cd ~/git/sdc.redistribute
git add .github/ _pkgdown.yml .Rbuildignore
git commit -m "ci: add R-CMD-check, coverage, and pkgdown workflows"
```

---

## Task 12: CRAN-readiness pass

**Files:**
- Create: `cran-comments.md`
- Modify: `DESCRIPTION` (only if check flags it)

- [ ] **Step 1: Install the missing Suggests used by checks**

Run: `Rscript -e 'install.packages(c("areal","spelling","covr"), repos="https://cloud.r-project.org")'`
Expected: the three packages install.

- [ ] **Step 2: Set up spelling and check it**

Run: `cd ~/git/sdc.redistribute && Rscript -e 'usethis::proj_set("."); usethis::use_spell_check(); spelling::spell_check_package()'`
Expected: no spelling errors (add genuine technical terms to `inst/WORDLIST` if flagged).

- [ ] **Step 3: Run R CMD check as CRAN**

Run: `cd ~/git/sdc.redistribute && Rscript -e 'devtools::check(args = c("--as-cran"), error_on = "note")'`
Expected: `0 errors | 0 warnings | 0 notes`. Fix anything reported (common: Title/Description wording, undocumented arguments, non-ASCII) and re-run until clean.

- [ ] **Step 4: Write cran-comments.md**

Create `cran-comments.md`:
```markdown
## R CMD check results

0 errors | 0 warnings | 0 notes

* This is a new release.

## Test environments

* local macOS, R 4.5.0
* GitHub Actions: ubuntu-latest (release, devel), macOS-latest, windows-latest
* win-builder (devel and release)
```

- [ ] **Step 5: Final full test + commit**

Run: `cd ~/git/sdc.redistribute && Rscript -e 'devtools::test()'`
Expected: all tests pass.
```bash
cd ~/git/sdc.redistribute
git add -A
git commit -m "chore: CRAN-readiness — spelling, cran-comments, clean check"
```

- [ ] **Step 6: (Manual, later) CRAN submission prerequisites**

Not run by the agent — recorded for the author:
- Create the GitHub repo `dads2busy/sdc.redistribute`, push `main`, confirm CI is green and Pages is published.
- `devtools::check_win_devel()` and an R-hub run.
- Bump version to `0.1.0`, update `NEWS.md`, then `devtools::release()`.

---

## Self-Review Notes

- **Spec coverage:** §4 API → Tasks 3–7; §5.1 CRS → Tasks 2/5; §5.2 preserve_totals → Tasks 3/4; §5.3 errors → Tasks 5/7; §5.4 output shape → Tasks 3/6; §6 structure/deps → Tasks 1/8; §7 testing → Tasks 3–7; §8 CRAN → Task 12; §9 docs → Tasks 8/10/11; §11 example data → Task 9. PUMS/pipeline wrapper are spec non-goals and intentionally absent.
- **Type consistency:** helper names `.validate_layers`, `.require_projected`, `.align_crs`, `.suffixed`, `.is_sf` are defined in Task 2 and used unchanged in Tasks 3/6. Internal temp columns (`.src_area`, `.tgt_id`, `.tgt_area`, `.int_area`, `.src_id`, `.w`, `.wsum`) are created and dropped within each function.
- **Open risk:** `st_intersection`/`st_join` on real-world (non-box) geometries can emit `GEOMETRYCOLLECTION` or duplicate joins; the box-based tests won't surface that. The dimension filter in Task 3 handles collections; revisit with a real-data integration test when wiring into the guide.
