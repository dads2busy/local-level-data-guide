library(tidycensus)
library(tigris)

va013bg <- tigris::block_groups(state = "VA", county = "013", cb = TRUE, year = 2024)

acs_vars <- tidycensus::load_variables(2023, "acs5")
acs_income <- get_acs(year = 2021,  
                      state = "VA", 
                      county = "013", 
                      geography = "block group", 
                      variables = "B19013_001", 
                      geometry = TRUE
                      )
sf::write_sf(acs_income, "data/va013_median_household_income.geojson")

tiles <- download_ookla_tiles_robust("fixed", 2023, 2, filter_region = va013bg)

civ_assoc <- sf::read_sf("data/va013_geo_arl_2021_civic_associations.geojson")

sf::write_sf(tiles, "data/ookla_tiles_arlington.geojson")

va013_blocks <- tigris::blocks(state = "VA", county = "013")
sf::write_sf(va013_blocks, "data/va013_geo_blocks.geojson")


par(mfrow = c(1, 3)) # Create a 3 x 1 plotting matrix
# The next 3 plots created will be plotted next to each other

# Plot 1
plot(tiles[, c("avg_d_kbps")], key.pos = NULL, reset = FALSE)

# Plot 2
plot(acs_income[, c("estimate")], key.pos = NULL, reset = FALSE)

# Plot 3
plot(civ_assoc[, c("region_name")], key.pos = NULL, reset = FALSE)

par(mfrow=c(1,1))
