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
