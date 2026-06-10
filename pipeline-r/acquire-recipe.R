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
