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
