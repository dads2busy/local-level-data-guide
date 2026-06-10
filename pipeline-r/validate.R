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
