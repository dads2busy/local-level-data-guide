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
