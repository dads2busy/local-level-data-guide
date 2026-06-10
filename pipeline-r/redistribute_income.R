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
