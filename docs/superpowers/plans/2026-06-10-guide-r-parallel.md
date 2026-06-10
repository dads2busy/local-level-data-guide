# Guide Parallel R Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a runnable R core (`pipeline-r/`, using `sf` + the `sdc.redistribute` R package) that reproduces the guide's redistribute → combine → validate stages from the same intermediate data the Python pipeline produces, verified for number-parity, and surface R alongside Python in the guide (per-stage tabs + a generated R code appendix).

**Architecture:** `pipeline-r/*.R` reads the existing `data/*.geojson` intermediates (the Python pipeline's inputs/outputs), reprojects to EPSG:3857 (matching Python's internal CRS), redistributes via `sdc.redistribute::redistribute_direct`/`redistribute_parcels`, derives the same metrics, and writes `*_r` outputs. A parity script compares the R combined output to the Python one. The guide gains Python|R tabsets and a generated `09-code-r.qmd` appendix; one generalized generator emits both appendices.

**Tech Stack:** R (>= 4.1), `sf`, `sdc.redistribute` (from GitHub: `pak::pak("dads2busy/sdc.redistribute")`), Quarto, Python (only to run the existing generator script).

**Reference spec:** `docs/superpowers/specs/2026-06-10-guide-r-parallel-design.md`.

**All paths are relative to the repo root** `/Users/ads7fg/git/local_level_data`. Run R modules from the repo root (e.g. `Rscript pipeline-r/run.R`).

---

## Prerequisites (verify before Task 1)

- [ ] **R + sf + sdc.redistribute available.** Run:
  `Rscript -e 'library(sf); library(sdc.redistribute); cat("ok\n")'`
  Expected: `ok`. If `sdc.redistribute` is missing: `Rscript -e 'pak::pak("dads2busy/sdc.redistribute")'` (or `remotes::install_github("dads2busy/sdc.redistribute")`).
- [ ] **Intermediate data present.** Run: `ls data/va013_acs_income_counts.geojson data/ookla_tiles_arlington.geojson data/va013_parcels.geojson data/va013_geo_arl_2021_civic_associations.geojson data/civic_combined.geojson data/civic_income_comparison.geojson`
  Expected: all six exist. If not, regenerate with `uv run python -m pipeline.run` (needs `CENSUS_API_KEY`).

Confirmed column facts the code relies on: `ACS_COUNTS` has `GEOID, agg_income, households` (Polygon); `CIVIC_ASSOC` has `geoid, region_name, region_type, year` (Polygon); `OOKLA_TILES` has `quadkey, avg_d_kbps, avg_u_kbps, tests` (Polygon); `PARCELS` has `Total_Units, Unit_Type` (Point).

---

## File Structure

- `pipeline-r/config.R` — paths + constants (`PROJECT_CRS`, years, `MIN_TESTS`).
- `pipeline-r/redistribute_income.R` — area-weighted income → `civic_income_r.csv`.
- `pipeline-r/redistribute_broadband.R` — area-weighted broadband → `civic_broadband_r.csv`.
- `pipeline-r/combine.R` — join + derived metrics → `civic_combined_r.geojson`.
- `pipeline-r/redistribute_income_parcels.R` — dasymetric income → `civic_income_parcels_r.csv`.
- `pipeline-r/compare_methods.R` — area vs parcel → `civic_income_comparison_r.geojson`.
- `pipeline-r/validate.R` — totals/range checks.
- `pipeline-r/run.R` — orchestrate the runnable stages.
- `pipeline-r/acquire-recipe.R` — recipe only (not executed).
- `pipeline-r/compare_to_python.R` — parity assertion vs Python outputs.
- `scripts/build_code_appendix.py` — generalized to emit `08-code.qmd` (Python) and `09-code-r.qmd` (R).
- `guide/09-code-r.qmd` — generated R appendix.
- `guide/_quarto.yml`, `guide/04-worked-example.qmd`, `guide/parcel-approach.qmd`, `guide/the-gap.qmd`, `guide/07-apply-it.qmd` — integration + prose.

---

## Task 1: `pipeline-r/config.R`

**Files:** Create `pipeline-r/config.R`

- [ ] **Step 1: Write the file**

```r
# Shared configuration for the R pipeline. Mirrors pipeline/config.py.
# Run all modules from the repository root (e.g. `Rscript pipeline-r/run.R`).

PROJECT_CRS <- 3857   # match the CRS sdc-redistribute uses internally in Python
ACS_YEAR    <- 2021
OOKLA_YEAR  <- 2023
MIN_TESTS   <- 5      # statistical-reliability filter on source tiles

DATA <- "data"
path_data <- function(...) file.path(DATA, ...)

# Inputs (shared with the Python pipeline)
CIVIC_ASSOC <- path_data("va013_geo_arl_2021_civic_associations.geojson")
ACS_COUNTS  <- path_data("va013_acs_income_counts.geojson")
OOKLA_TILES <- path_data("ookla_tiles_arlington.geojson")
PARCELS     <- path_data("va013_parcels.geojson")

# R outputs (suffixed _r so they never clobber the Python outputs)
CIVIC_INCOME_R            <- path_data("civic_income_r.csv")
CIVIC_BROADBAND_R         <- path_data("civic_broadband_r.csv")
CIVIC_COMBINED_R          <- path_data("civic_combined_r.geojson")
CIVIC_INCOME_PARCELS_R    <- path_data("civic_income_parcels_r.csv")
CIVIC_INCOME_COMPARISON_R <- path_data("civic_income_comparison_r.geojson")

# Python outputs (for parity comparison)
CIVIC_COMBINED_PY <- path_data("civic_combined.geojson")
```

- [ ] **Step 2: Verify it sources cleanly**

Run: `Rscript -e 'source("pipeline-r/config.R"); cat(CIVIC_ASSOC, "|", PROJECT_CRS, "\n")'`
Expected: `data/va013_geo_arl_2021_civic_associations.geojson | 3857`

- [ ] **Step 3: Commit**

```bash
git add pipeline-r/config.R
git commit -m "feat(r): pipeline-r config (paths, CRS, constants)"
```

---

## Task 2: `pipeline-r/redistribute_income.R`

**Files:** Create `pipeline-r/redistribute_income.R`

- [ ] **Step 1: Write the file**

```r
# Area-weight ACS income counts onto civic associations; derive mean income.
# Parallels pipeline/redistribute_income.py.
source("pipeline-r/config.R")
suppressPackageStartupMessages({
  library(sf)
  library(sdc.redistribute)
})

redistribute_income <- function(acs_path = ACS_COUNTS, civic_path = CIVIC_ASSOC) {
  bg <- sf::st_read(acs_path, quiet = TRUE)
  names(bg)[names(bg) == "GEOID"] <- "geoid"
  civ <- sf::st_read(civic_path, quiet = TRUE)

  bg  <- sf::st_transform(bg,  PROJECT_CRS)
  civ <- sf::st_transform(civ, PROJECT_CRS)

  # agg_income and households are extensive counts; redistribute both, then
  # derive mean income (an intensive quantity) as their ratio.
  out <- redistribute_direct(bg, civ, extensive = c("agg_income", "households"))
  out$mean_income <- ifelse(out$households > 0, out$agg_income / out$households, NA_real_)

  d <- sf::st_drop_geometry(out)
  d[, c("geoid", "agg_income", "households", "mean_income")]
}

run_income <- function() {
  out <- redistribute_income()
  write.csv(out, CIVIC_INCOME_R, row.names = FALSE)
  cat(sprintf("Wrote %d civic-association income rows -> %s\n", nrow(out), CIVIC_INCOME_R))
}

if (sys.nframe() == 0) run_income()
```

- [ ] **Step 2: Run it**

Run: `Rscript pipeline-r/redistribute_income.R`
Expected: prints `Wrote 62 civic-association income rows -> data/civic_income_r.csv`.

- [ ] **Step 3: Sanity-check the output against Python**

Run:
```bash
Rscript -e 'r<-read.csv("data/civic_income_r.csv"); cat("rows:",nrow(r),"| hh sum:",round(sum(r$households)),"| mean_income range:",round(min(r$mean_income,na.rm=TRUE)),"-",round(max(r$mean_income,na.rm=TRUE)),"\n")'
```
Expected: `rows: 62`, household sum near the ACS total (~109,000), mean_income a plausible dollar range (tens of thousands to low hundreds of thousands). If `rows` != 62 or mean_income is absurd, stop and report.

- [ ] **Step 4: Commit**

```bash
git add pipeline-r/redistribute_income.R
git commit -m "feat(r): area-weighted income redistribution"
```

---

## Task 3: `pipeline-r/redistribute_broadband.R`

**Files:** Create `pipeline-r/redistribute_broadband.R`

- [ ] **Step 1: Write the file**

```r
# Area-weight Ookla broadband onto civic associations; derive count-weighted
# mean speeds. Parallels pipeline/redistribute_broadband.py.
source("pipeline-r/config.R")
suppressPackageStartupMessages({
  library(sf)
  library(sdc.redistribute)
})

redistribute_broadband <- function(tiles_path = OOKLA_TILES, civic_path = CIVIC_ASSOC) {
  tiles <- sf::st_read(tiles_path, quiet = TRUE)
  tiles <- tiles[tiles$tests >= MIN_TESTS, ]
  # Speed is intensive: rebuild the extensive speed x tests product so the
  # count-weighted mean can be recovered after redistribution.
  tiles$d_product <- tiles$avg_d_kbps * tiles$tests
  tiles$u_product <- tiles$avg_u_kbps * tiles$tests

  civ <- sf::st_read(civic_path, quiet = TRUE)
  tiles <- sf::st_transform(tiles, PROJECT_CRS)
  civ   <- sf::st_transform(civ,   PROJECT_CRS)

  out <- redistribute_direct(tiles, civ, extensive = c("tests", "d_product", "u_product"))
  valid <- out$tests > 0
  out$download_mbps <- ifelse(valid, (out$d_product / out$tests) / 1000, NA_real_)
  out$upload_mbps   <- ifelse(valid, (out$u_product / out$tests) / 1000, NA_real_)

  d <- sf::st_drop_geometry(out)
  d[, c("geoid", "tests", "download_mbps", "upload_mbps")]
}

run_broadband <- function() {
  out <- redistribute_broadband()
  write.csv(out, CIVIC_BROADBAND_R, row.names = FALSE)
  cat(sprintf("Wrote %d civic-association broadband rows -> %s\n", nrow(out), CIVIC_BROADBAND_R))
}

if (sys.nframe() == 0) run_broadband()
```

- [ ] **Step 2: Run it**

Run: `Rscript pipeline-r/redistribute_broadband.R`
Expected: `Wrote 62 civic-association broadband rows -> data/civic_broadband_r.csv`.

- [ ] **Step 3: Sanity-check**

Run:
```bash
Rscript -e 'r<-read.csv("data/civic_broadband_r.csv"); cat("rows:",nrow(r),"| dl range:",round(min(r$download_mbps,na.rm=TRUE)),"-",round(max(r$download_mbps,na.rm=TRUE)),"Mbps\n")'
```
Expected: `rows: 62`, download_mbps in a plausible range (roughly 100-350 Mbps, matching the guide's figures). Stop if absurd.

- [ ] **Step 4: Commit**

```bash
git add pipeline-r/redistribute_broadband.R
git commit -m "feat(r): area-weighted broadband redistribution"
```

---

## Task 4: `pipeline-r/combine.R`

**Files:** Create `pipeline-r/combine.R`

- [ ] **Step 1: Write the file**

```r
# Join redistributed income + broadband onto civic polygons; derive metrics.
# Parallels pipeline/combine.py.
source("pipeline-r/config.R")
suppressPackageStartupMessages(library(sf))

tercile <- function(x) {
  # 1/2/3 labels by rank (robust to ties and NA), mirroring pandas qcut on ranks.
  r <- rank(x, ties.method = "first", na.last = "keep")
  br <- stats::quantile(r, probs = c(0, 1/3, 2/3, 1), na.rm = TRUE)
  cut(r, breaks = br, labels = c("1", "2", "3"), include.lowest = TRUE)
}

add_derived_metrics <- function(df) {
  df$income_speed_ratio <- ifelse(df$download_mbps > 0,
                                  df$mean_income / df$download_mbps, NA_real_)
  inc <- tercile(df$mean_income)
  spd <- tercile(df$download_mbps)
  df$bivariate_class <- paste0(as.character(inc), "-", as.character(spd))
  df
}

run_combine <- function() {
  civ <- sf::st_read(CIVIC_ASSOC, quiet = TRUE)[, c("geoid", "region_name")]
  income    <- read.csv(CIVIC_INCOME_R,    colClasses = c(geoid = "character"))
  broadband <- read.csv(CIVIC_BROADBAND_R, colClasses = c(geoid = "character"))
  civ$geoid <- as.character(civ$geoid)

  merged <- merge(civ, income, by = "geoid", all.x = TRUE)
  merged <- merge(merged, broadband, by = "geoid", all.x = TRUE)
  merged <- add_derived_metrics(merged)

  sf::st_write(merged, CIVIC_COMBINED_R, delete_dsn = TRUE, quiet = TRUE)
  cat(sprintf("Wrote %d combined civic-association rows -> %s\n",
              nrow(merged), CIVIC_COMBINED_R))
}

if (sys.nframe() == 0) run_combine()
```

- [ ] **Step 2: Run it** (Tasks 2 and 3 must have run first)

Run: `Rscript pipeline-r/combine.R`
Expected: `Wrote 62 combined civic-association rows -> data/civic_combined_r.geojson`.

- [ ] **Step 3: Sanity-check columns**

Run:
```bash
Rscript -e 'g<-sf::st_read("data/civic_combined_r.geojson",quiet=TRUE); cat(paste(names(g),collapse=","),"\n")'
```
Expected: includes `geoid, region_name, agg_income, households, mean_income, tests, download_mbps, upload_mbps, income_speed_ratio, bivariate_class, geometry`.

- [ ] **Step 4: Commit**

```bash
git add pipeline-r/combine.R
git commit -m "feat(r): combine income + broadband and derive metrics"
```

---

## Task 5: `pipeline-r/redistribute_income_parcels.R`

**Files:** Create `pipeline-r/redistribute_income_parcels.R`

- [ ] **Step 1: Write the file**

```r
# Dasymetric income redistribution through unit-weighted parcels.
# Parallels pipeline/redistribute_income_parcels.py: Python replicates each
# parcel into Total_Units identical points; here we pass Total_Units as the
# per-point weight, which splits each source value in the same proportion.
source("pipeline-r/config.R")
suppressPackageStartupMessages({
  library(sf)
  library(sdc.redistribute)
})

redistribute_income_parcels <- function(acs_path = ACS_COUNTS,
                                        parcels_path = PARCELS,
                                        civic_path = CIVIC_ASSOC) {
  bg <- sf::st_read(acs_path, quiet = TRUE)
  names(bg)[names(bg) == "GEOID"] <- "geoid"
  parcels <- sf::st_read(parcels_path, quiet = TRUE)
  parcels <- parcels[parcels$Total_Units > 0, ]
  civ <- sf::st_read(civic_path, quiet = TRUE)

  bg      <- sf::st_transform(bg,      PROJECT_CRS)
  parcels <- sf::st_transform(parcels, PROJECT_CRS)
  civ     <- sf::st_transform(civ,     PROJECT_CRS)

  out <- redistribute_parcels(bg, civ, parcels,
                              extensive = c("agg_income", "households"),
                              weights = "Total_Units")
  out$mean_income <- ifelse(out$households > 0, out$agg_income / out$households, NA_real_)

  d <- sf::st_drop_geometry(out)
  d[, c("geoid", "agg_income", "households", "mean_income")]
}

run_income_parcels <- function() {
  out <- redistribute_income_parcels()
  write.csv(out, CIVIC_INCOME_PARCELS_R, row.names = FALSE)
  cat(sprintf("Wrote %d parcel-weighted income rows -> %s\n",
              nrow(out), CIVIC_INCOME_PARCELS_R))
}

if (sys.nframe() == 0) run_income_parcels()
```

- [ ] **Step 2: Run it**

Run: `Rscript pipeline-r/redistribute_income_parcels.R`
Expected: `Wrote 62 parcel-weighted income rows -> data/civic_income_parcels_r.csv` (may take longer; ~34k parcels).

- [ ] **Step 3: Sanity-check**

Run:
```bash
Rscript -e 'r<-read.csv("data/civic_income_parcels_r.csv"); cat("rows:",nrow(r),"| mean_income range:",round(min(r$mean_income,na.rm=TRUE)),"-",round(max(r$mean_income,na.rm=TRUE)),"\n")'
```
Expected: `rows: 62`, plausible dollar range. Stop if absurd.

- [ ] **Step 4: Commit**

```bash
git add pipeline-r/redistribute_income_parcels.R
git commit -m "feat(r): dasymetric (parcel-weighted) income redistribution"
```

---

## Task 6: `pipeline-r/compare_methods.R`

**Files:** Create `pipeline-r/compare_methods.R`

- [ ] **Step 1: Write the file**

```r
# Compare area-weighted vs parcel-weighted income per civic association.
# Parallels pipeline/compare_methods.py.
source("pipeline-r/config.R")
suppressPackageStartupMessages(library(sf))

compare_income <- function(area, parcel) {
  a <- data.frame(geoid = as.character(area$geoid),
                  mean_income_area = area$mean_income, stringsAsFactors = FALSE)
  p <- data.frame(geoid = as.character(parcel$geoid),
                  mean_income_parcel = parcel$mean_income, stringsAsFactors = FALSE)
  out <- merge(a, p, by = "geoid", all = TRUE)
  out$diff <- out$mean_income_parcel - out$mean_income_area
  out$pct_diff <- ifelse(out$mean_income_area > 0,
                         100 * out$diff / out$mean_income_area, NA_real_)
  out
}

run_compare <- function() {
  civ    <- sf::st_read(CIVIC_ASSOC, quiet = TRUE)[, c("geoid", "region_name")]
  civ$geoid <- as.character(civ$geoid)
  area   <- read.csv(CIVIC_INCOME_R,         colClasses = c(geoid = "character"))
  parcel <- read.csv(CIVIC_INCOME_PARCELS_R, colClasses = c(geoid = "character"))
  cmp <- compare_income(area, parcel)
  out <- merge(civ, cmp, by = "geoid", all.x = TRUE)
  sf::st_write(out, CIVIC_INCOME_COMPARISON_R, delete_dsn = TRUE, quiet = TRUE)
  cat(sprintf("Wrote %d comparison rows -> %s\n", nrow(out), CIVIC_INCOME_COMPARISON_R))
}

if (sys.nframe() == 0) run_compare()
```

- [ ] **Step 2: Run it**

Run: `Rscript pipeline-r/compare_methods.R`
Expected: `Wrote 62 comparison rows -> data/civic_income_comparison_r.geojson`.

- [ ] **Step 3: Commit**

```bash
git add pipeline-r/compare_methods.R
git commit -m "feat(r): compare area-weighted vs parcel-weighted income"
```

---

## Task 7: `pipeline-r/validate.R` and `pipeline-r/run.R`

**Files:** Create `pipeline-r/validate.R`, `pipeline-r/run.R`

- [ ] **Step 1: Write `pipeline-r/validate.R`**

```r
# Integrity checks on redistributed outputs. Parallels pipeline/validate.py.
source("pipeline-r/config.R")
suppressPackageStartupMessages(library(sf))

check_total_preserved <- function(source_total, target_total, tol = 0.01) {
  if (source_total == 0) return(invisible(TRUE))
  rel <- abs(target_total - source_total) / abs(source_total)
  if (rel > tol) {
    stop(sprintf("total drift %.3f%% exceeds %.3f%%", 100 * rel, 100 * tol), call. = FALSE)
  }
  invisible(TRUE)
}

check_ranges <- function(df) {
  for (col in c("download_mbps", "upload_mbps", "mean_income", "households")) {
    if (col %in% names(df)) {
      vals <- df[[col]][!is.na(df[[col]])]
      if (any(vals < 0)) stop(sprintf("%s has negative values", col), call. = FALSE)
    }
  }
  invisible(TRUE)
}

run_validate <- function() {
  combined <- sf::st_drop_geometry(sf::st_read(CIVIC_COMBINED_R, quiet = TRUE))
  acs <- sf::st_drop_geometry(sf::st_read(ACS_COUNTS, quiet = TRUE))
  check_total_preserved(sum(acs$households), sum(combined$households, na.rm = TRUE), tol = 0.02)
  check_ranges(combined)
  cat("Validation passed.\n")
}

if (sys.nframe() == 0) run_validate()
```

- [ ] **Step 2: Write `pipeline-r/run.R`**

```r
# Run the runnable R stages end to end (acquisition is a recipe; see
# pipeline-r/acquire-recipe.R). Parallels pipeline/run.py.
# Usage from the repository root: Rscript pipeline-r/run.R
source("pipeline-r/redistribute_income.R")
source("pipeline-r/redistribute_broadband.R")
source("pipeline-r/combine.R")
source("pipeline-r/redistribute_income_parcels.R")
source("pipeline-r/compare_methods.R")
source("pipeline-r/validate.R")

run_income()
run_broadband()
run_combine()
run_income_parcels()
run_compare()
run_validate()
cat("R pipeline complete.\n")
```

- [ ] **Step 3: Run the whole pipeline**

Run: `Rscript pipeline-r/run.R`
Expected: each stage prints its "Wrote ..." line, then `Validation passed.` and `R pipeline complete.` with no error.

- [ ] **Step 4: Commit**

```bash
git add pipeline-r/validate.R pipeline-r/run.R
git commit -m "feat(r): validation and end-to-end run orchestration"
```

---

## Task 8: `pipeline-r/compare_to_python.R` (parity gate)

**Files:** Create `pipeline-r/compare_to_python.R`

- [ ] **Step 1: Write the file**

```r
# Parity check: confirm the R combined output matches the Python combined output
# (mean_income and download_mbps) within tolerance. Small differences are
# expected from GEOS/sf vs shapely/geopandas geometry handling.
source("pipeline-r/config.R")
suppressPackageStartupMessages(library(sf))

compare_to_python <- function(tol = 0.02) {
  r  <- sf::st_drop_geometry(sf::st_read(CIVIC_COMBINED_R, quiet = TRUE))
  py <- sf::st_drop_geometry(sf::st_read(CIVIC_COMBINED_PY, quiet = TRUE))
  r$geoid  <- as.character(r$geoid)
  py$geoid <- as.character(py$geoid)
  m <- merge(r, py, by = "geoid", suffixes = c("_r", "_py"))

  rel <- function(a, b) {
    ok <- is.finite(a) & is.finite(b) & b != 0
    max(abs(a[ok] - b[ok]) / abs(b[ok]))
  }
  d_income <- rel(m$mean_income_r,   m$mean_income_py)
  d_speed  <- rel(m$download_mbps_r, m$download_mbps_py)

  cat(sprintf("Parity vs Python (n=%d): max rel diff  mean_income=%.4f%%  download_mbps=%.4f%%\n",
              nrow(m), 100 * d_income, 100 * d_speed))
  if (d_income > tol || d_speed > tol) {
    stop(sprintf("parity exceeds tolerance %.2f%%", 100 * tol), call. = FALSE)
  }
  cat(sprintf("Parity OK (within %.2f%%).\n", 100 * tol))
  invisible(TRUE)
}

if (sys.nframe() == 0) compare_to_python()
```

- [ ] **Step 2: Run it (the acceptance gate)**

Run: `Rscript pipeline-r/compare_to_python.R`
Expected: prints the max relative differences for `mean_income` and `download_mbps` and `Parity OK (within 2.00%).` The differences should be small (well under 1% in practice). If parity fails, do NOT loosen the tolerance blindly — investigate (likely a CRS or column issue) and report. If the genuine geometry-engine difference is just above 2%, report the observed value for a human tolerance decision rather than hiding it.

- [ ] **Step 3: Commit**

```bash
git add pipeline-r/compare_to_python.R
git commit -m "feat(r): parity check of R outputs against the Python pipeline"
```

---

## Task 9: `pipeline-r/acquire-recipe.R` (recipe only, not executed)

**Files:** Create `pipeline-r/acquire-recipe.R`

- [ ] **Step 1: Write the file**

```r
# Data-acquisition recipe (NOT executed by run.R). Shows how the same
# intermediate inputs the R pipeline reads would be produced in R, paralleling
# the Python acquire_*.py modules. Requires a Census API key and network access.
#
# install.packages(c("tidycensus", "tigris", "sf"))
# # ooklaOpenDataR is on GitHub: remotes::install_github("teamookla/ooklaOpenDataR")

if (FALSE) {  # recipe guard: never runs

  library(tidycensus)
  library(tigris)
  library(sf)

  # 1. Census block-group geometries for Arlington County, VA (FIPS 51013),
  #    2021 vintage. Parallels acquire_geographies.py.
  bg_geo <- tigris::block_groups(state = "51", county = "013", year = 2021, cb = FALSE)

  # 2. ACS extensive counts: aggregate household income (B19025_001) and
  #    households (B11001_001). Parallels acquire_acs.py. NEVER fetch the median.
  acs <- tidycensus::get_acs(
    geography = "block group", state = "51", county = "013",
    year = 2021, survey = "acs5", geometry = TRUE,
    variables = c(agg_income = "B19025_001", households = "B11001_001"),
    output = "wide"
  )
  # acs has agg_incomeE / householdsE columns; rename to agg_income / households.

  # 3. Ookla fixed-broadband tiles, clipped to Arlington. Parallels acquire_ookla.py.
  #    ooklaOpenDataR::get_performance_tiles(service = "fixed", year = 2023,
  #      quarter = 2) returns the global tile set; clip to the county bbox.

  # 4. Parcels: county MHUD parcel points carrying Total_Units. Parallels
  #    acquire_parcels.py (an ArcGIS FeatureServer; read via arcgislayers or sf).
}
```

- [ ] **Step 2: Verify it sources without executing anything**

Run: `Rscript -e 'source("pipeline-r/acquire-recipe.R"); cat("recipe sourced (no execution)\n")'`
Expected: `recipe sourced (no execution)` with no package-load or network activity (the `if (FALSE)` guard prevents execution).

- [ ] **Step 3: Commit**

```bash
git add pipeline-r/acquire-recipe.R
git commit -m "docs(r): data-acquisition recipe (tidycensus/tigris/ooklaOpenDataR)"
```

---

## Task 10: Generalize the appendix generator; generate `09-code-r.qmd`

**Files:** Modify `scripts/build_code_appendix.py`; Create `guide/09-code-r.qmd` (generated); Modify `guide/_quarto.yml`

- [ ] **Step 1: Replace `scripts/build_code_appendix.py` with a two-language generator**

Overwrite the file with:
```python
"""Generate the guide's code appendix chapters from the real pipeline sources.

Single source of truth: `pipeline/*.py` (Python) and `pipeline-r/*.R` (R). This
embeds those modules verbatim into `guide/08-code.qmd` and `guide/09-code-r.qmd`,
so the appendices always match the runnable implementations. Re-run after
changing pipeline code:

    uv run python scripts/build_code_appendix.py
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

PY_MODULES: list[tuple[str, str, str]] = [
    ("config.py", "Configuration",
     "Central settings: the Arlington FIPS codes, the ACS count variables "
     "(aggregate income and households), and the dataset paths every other "
     "module reads."),
    ("acquire_geographies.py", "Acquire census geographies",
     "Download Arlington's census block groups, the source geography for the "
     "income redistribution."),
    ("acquire_acs.py", "Acquire ACS income counts",
     "Pull aggregate household income and household counts from the Census API. "
     "These are *counts* (extensive measures); mean income is derived later."),
    ("acquire_ookla.py", "Acquire Ookla broadband tiles",
     "Read the Ookla open-data broadband tiles from S3 and clip them to "
     "Arlington."),
    ("redistribute_income.py", "Redistribute income",
     "Area-weight the income and household counts onto civic associations with "
     "`sdc-redistribute`, then derive mean household income."),
    ("redistribute_broadband.py", "Redistribute broadband",
     "Redistribute test counts and the speed×tests product, then derive the "
     "count-weighted mean download and upload speeds."),
    ("combine.py", "Combine and derive metrics",
     "Join the redistributed income and broadband measures onto the civic "
     "association polygons and compute the income-to-speed ratio and the "
     "bivariate income×speed classes."),
    ("acquire_parcels.py", "Acquire parcels",
     "Page through the Arlington MHUD FeatureServer and reduce parcel polygons "
     "to unit-bearing centroids."),
    ("redistribute_income_parcels.py", "Redistribute income through parcels",
     "Explode parcels into per-unit points and redistribute block-group income "
     "through them (the dasymetric second approach)."),
    ("compare_methods.py", "Compare methods",
     "Join the area-weighted and parcel-weighted income and quantify the "
     "difference per civic association."),
    ("validate.py", "Validate",
     "Confirm household totals are preserved by the redistribution and that no "
     "speeds or incomes are negative."),
    ("run.py", "Run the full pipeline",
     "Wire every stage into one command: `uv run python -m pipeline.run`."),
]

R_MODULES: list[tuple[str, str, str]] = [
    ("config.R", "Configuration",
     "Shared paths, the projected CRS used for area weighting, and the count "
     "constants. Mirrors the Python configuration."),
    ("redistribute_income.R", "Redistribute income",
     "Area-weight aggregate income and households onto civic associations with "
     "`sdc.redistribute::redistribute_direct()`, then derive mean income."),
    ("redistribute_broadband.R", "Redistribute broadband",
     "Rebuild the speed×tests product, redistribute it with the test counts, "
     "then derive the count-weighted mean download and upload speeds."),
    ("combine.R", "Combine and derive metrics",
     "Join redistributed income and broadband onto the civic polygons and "
     "compute the income-to-speed ratio and bivariate income×speed classes."),
    ("redistribute_income_parcels.R", "Redistribute income through parcels",
     "Dasymetric income via `redistribute_parcels()`, weighting parcels by "
     "their unit count (the second approach)."),
    ("compare_methods.R", "Compare methods",
     "Join the area-weighted and parcel-weighted income and quantify the "
     "difference per civic association."),
    ("validate.R", "Validate",
     "Confirm household totals are preserved and that no speeds or incomes are "
     "negative."),
    ("run.R", "Run the R pipeline",
     "Run the redistribute/combine/validate stages end to end: "
     "`Rscript pipeline-r/run.R`."),
    ("acquire-recipe.R", "Acquisition recipe",
     "How the same inputs would be produced in R (`tidycensus`/`tigris`/"
     "`ooklaOpenDataR`). Shown for reference; not executed by the pipeline."),
    ("compare_to_python.R", "Parity with the Python pipeline",
     "Confirm the R outputs match the Python pipeline's mean income and "
     "download speed within tolerance."),
]

PY_HEADER = """\
# The Complete Pipeline Code (Python) {#sec-code}

This appendix reproduces the full, runnable Python pipeline behind the worked
example: the actual source, not a simplified sketch. It is generated directly
from the `pipeline/` package in the companion repository, so it always matches
the code that produced every figure and number in this guide.

The pipeline is built on the [`sdc-redistribute`](https://pypi.org/project/sdc-redistribute/)
package and runs end to end with a single command:

```bash
uv run python -m pipeline.run
```

The modules below appear in execution order. Figure generation
(`pipeline/style.py`, `pipeline/maps.py`, `pipeline/figures.py`) lives in the
same repository and is omitted here to keep the focus on the data method.
"""

R_HEADER = """\
# The Complete Pipeline Code (R) {#sec-code-r}

This appendix reproduces the runnable R counterpart to the worked example. It is
generated directly from the `pipeline-r/` directory in the companion repository.
The R pipeline reads the same intermediate data the Python pipeline produces and
performs the redistribution, combination, and validation in R, built on the
[`sdc.redistribute`](https://github.com/dads2busy/sdc.redistribute) package:

```r
# install.packages("pak"); pak::pak("dads2busy/sdc.redistribute")
# from the repository root:
# Rscript pipeline-r/run.R
```

Data acquisition is shown as a recipe (`acquire-recipe.R`) rather than re-run.
The `compare_to_python.R` module confirms the R results match the Python results.
"""


def _render(modules, src_dir: Path, src_label: str, lang: str, header: str) -> str:
    parts = [header]
    for filename, title, blurb in modules:
        src = (src_dir / filename).read_text(encoding="utf-8").rstrip()
        parts.append(f"\n## {title}\n\n{blurb}\n")
        parts.append(f"**`{src_label}/{filename}`**\n")
        parts.append(f"```{lang}\n{src}\n```\n")
    return "\n".join(parts) + "\n"


def main() -> None:
    py = _render(PY_MODULES, ROOT / "pipeline", "pipeline", "python", PY_HEADER)
    (ROOT / "guide" / "08-code.qmd").write_text(py, encoding="utf-8")
    r = _render(R_MODULES, ROOT / "pipeline-r", "pipeline-r", "r", R_HEADER)
    (ROOT / "guide" / "09-code-r.qmd").write_text(r, encoding="utf-8")
    print(f"Wrote 08-code.qmd ({len(PY_MODULES)} modules) and 09-code-r.qmd ({len(R_MODULES)} modules)")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Generate both appendices**

Run: `uv run python scripts/build_code_appendix.py`
Expected: `Wrote 08-code.qmd (12 modules) and 09-code-r.qmd (10 modules)`. Confirm `guide/09-code-r.qmd` now exists and begins with `# The Complete Pipeline Code (R)`.

- [ ] **Step 3: Confirm 08-code.qmd is unchanged in content**

Run: `git diff --stat guide/08-code.qmd`
Expected: only the H1 title line changed (now "(Python)"). If the body diff is large, the generator regressed; investigate. (The title change is intended.)

- [ ] **Step 4: Add `09-code-r.qmd` to the book**

In `guide/_quarto.yml`, the chapters list currently ends:
```yaml
    - 08-code.qmd
    - references.qmd
```
Change it to:
```yaml
    - 08-code.qmd
    - 09-code-r.qmd
    - references.qmd
```

- [ ] **Step 5: Commit**

```bash
git add scripts/build_code_appendix.py guide/08-code.qmd guide/09-code-r.qmd guide/_quarto.yml
git commit -m "feat: generate Python and R code appendices from a single generator"
```

---

## Task 11: Per-stage Python|R tabs and prose updates

**Files:** Modify `guide/04-worked-example.qmd`, `guide/parcel-approach.qmd`, `guide/the-gap.qmd`, `guide/07-apply-it.qmd`

- [ ] **Step 1: Worked example — add a Python|R tabset to Stage 2 (income)**

In `guide/04-worked-example.qmd`, immediately AFTER the displayed mean-income equation block in "## Stage 2: Redistribute income" (the line ending `\text{households}_j}$$`), insert:
```markdown

::: {.panel-tabset}
## Python
```python
from sdc_redistribute import redistribute_direct
# agg_income and households are extensive counts.
res = redistribute_direct(counts_long, source_geo=block_groups,
                          target_geos={"civic_association": civic}, count_cols=["agg_income", "households"])
civic["mean_income"] = civic["agg_income"] / civic["households"]
```

## R
```r
library(sf); library(sdc.redistribute)
# agg_income and households are extensive counts.
civic <- redistribute_direct(block_groups, civic,
                             extensive = c("agg_income", "households"))
civic$mean_income <- civic$agg_income / civic$households
```
:::
```

- [ ] **Step 2: Worked example — convert the Stage 3 (broadband) Python callout to a tabset**

In `guide/04-worked-example.qmd`, replace this existing block:
```markdown
::: {.callout-note collapse="true" title="Python: count-weighting broadband speed"}
```python
# Speed is INTENSIVE: redistribute counts, then derive the rate.
tiles["d_product"] = tiles["avg_d_kbps"] * tiles["tests"]   # extensive
# ... redistribute tests + d_product to civic associations ...
civic["download_mbps"] = (civic["d_product"] / civic["tests"]) / 1000
```
:::
```
with:
```markdown
::: {.panel-tabset}
## Python
```python
# Speed is INTENSIVE: redistribute counts, then derive the rate.
tiles["d_product"] = tiles["avg_d_kbps"] * tiles["tests"]   # extensive
# ... redistribute tests + d_product to civic associations ...
civic["download_mbps"] = (civic["d_product"] / civic["tests"]) / 1000
```

## R
```r
# Speed is INTENSIVE: redistribute counts, then derive the rate.
tiles$d_product <- tiles$avg_d_kbps * tiles$tests            # extensive
civic <- redistribute_direct(tiles, civic, extensive = c("tests", "d_product"))
civic$download_mbps <- (civic$d_product / civic$tests) / 1000
```
:::
```

- [ ] **Step 3: Parcel chapter — add an R tab beside its Python snippet**

In `guide/parcel-approach.qmd`, find the existing parcel-redistribution Python code block. (Run `grep -n '```python' guide/parcel-approach.qmd` to locate it.) Wrap that existing Python block and a new R tab in a tabset, using this R equivalent:
```r
library(sf); library(sdc.redistribute)
# Split each block group's counts across its parcels, weighted by unit count.
civic <- redistribute_parcels(block_groups, civic, parcels,
                              extensive = c("agg_income", "households"),
                              weights = "Total_Units")
civic$mean_income <- civic$agg_income / civic$households
```
Concretely: change the existing ` ```python ... ``` ` block into:
```markdown
::: {.panel-tabset}
## Python
<the existing python block, unchanged>

## R
```r
library(sf); library(sdc.redistribute)
# Split each block group's counts across its parcels, weighted by unit count.
civic <- redistribute_parcels(block_groups, civic, parcels,
                              extensive = c("agg_income", "households"),
                              weights = "Total_Units")
civic$mean_income <- civic$agg_income / civic$households
```
:::
```
(Keep the surrounding prose unchanged. If the parcel chapter has more than one Python block, add the R tab only to the redistribution one; report the others.)

- [ ] **Step 4: Update `guide/the-gap.qmd` prose**

Replace this line:
```markdown
The worked example is implemented in **Python**. An **R** implementation is forthcoming.
```
with:
```markdown
The worked example is implemented in both **Python** and **R**. The two produce the same estimates; each stage below shows the code in both languages, and the complete source for each is in the code appendices.
```

- [ ] **Step 5: Update `guide/07-apply-it.qmd` R paragraph**

Replace the sentence beginning "An R implementation of the full Arlington pipeline is forthcoming, using ..." (the part about a forthcoming implementation) so the paragraph reads:
```markdown
The areal interpolation logic in the Python pipeline mirrors the `sdc-redistribute` family of functions available in R. A runnable R implementation of the redistribution stages ships with this guide in `pipeline-r/`, built on the [`sdc.redistribute`](https://github.com/dads2busy/sdc.redistribute) R package; the data-acquisition recipe uses `tigris` for Census geometries, `tidycensus` for ACS data, and `ooklaOpenDataR` for speed-test tiles. Analysts already working in R can follow the same six-step recipe; the redistribution algebra is language-agnostic.
```
Confirm no em dash (`—`) characters are introduced in any edited prose (the guide is em-dash-free).

- [ ] **Step 6: Commit**

```bash
git add guide/04-worked-example.qmd guide/parcel-approach.qmd guide/the-gap.qmd guide/07-apply-it.qmd
git commit -m "docs: show Python and R side by side; R implementation no longer forthcoming"
```

---

## Task 12: Render the guide and verify

**Files:** none (verification)

- [ ] **Step 1: Render the book**

Run: `cd guide && quarto render 2>&1 | tail -5`
Expected: `Output created: _output/index.html`, no error. (If figure-regeneration churn appears under `figures/diagrams`, discard it: `git checkout -- figures/diagrams`.)

- [ ] **Step 2: Confirm the R appendix and tabs are present in the HTML**

Run:
```bash
cd guide
grep -c "panel-tabset" _output/04-worked-example.html
grep -c "Complete Pipeline Code (R)" _output/09-code-r.html
```
Expected: the worked-example page has at least 2 tabsets; the R appendix page exists and contains the R appendix title.

- [ ] **Step 3: Confirm chapter ordering**

Run: `grep -o '0[0-9]-[a-z-]*\.html' guide/_output/index.html | sort -u | tail -6`
Expected: shows both `08-code.html` and `09-code-r.html` in the sidebar.

- [ ] **Step 4: Commit the regenerated PDF (repo convention)**

```bash
git add -f guide/_output/Creating-Local-Level-Geographic-Datasets.pdf
git add guide/Creating-Local-Level-Geographic-Datasets.tex
git commit -m "docs: render guide with parallel R implementation"
```
(Do NOT stage `guide/_output` HTML, `guide/_book`, `guide/figures/`, or `guide/site_libs`.)

---

## Self-Review Notes

- **Spec coverage:** §4 R pipeline → Tasks 1-9; §5 parity → Task 8; §6 guide integration (tabs, 09 appendix, generalized generator, prose) → Tasks 10-11; render verification → Task 12. Acquisition recipe (§3 non-goal of running it) → Task 9 (`if (FALSE)` guard). The Python pipeline is untouched (only `08-code.qmd`'s H1 title changes, Task 10 Step 3).
- **Type/identifier consistency:** module entry points are uniquely named (`run_income`, `run_broadband`, `run_combine`, `run_income_parcels`, `run_compare`, `run_validate`, `compare_to_python`) so `run.R` can source all and call them without collision; the `if (sys.nframe() == 0)` guard prevents auto-run on source. Output path constants (`CIVIC_*_R`) are defined once in `config.R` and reused. Column names (`geoid`, `agg_income`, `households`, `tests`, `d_product`, `u_product`, `download_mbps`, `Total_Units`) match the verified data files.
- **Parity caveat (logged, not hidden):** the parcel method does not preserve household totals exactly (parcels do not perfectly tile block groups) — same as Python; the parity gate (Task 8) checks the area-weighted combined output (`mean_income`, `download_mbps`), which should match tightly. `bivariate_class` may differ on tie boundaries between `pandas` qcut and R's `cut`; it is intentionally not part of the parity assertion.
- **Data dependency:** Tasks 2-8 require the `data/` intermediates (Prerequisites). They exist locally; not in CI.
