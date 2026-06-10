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
