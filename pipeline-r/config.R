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
