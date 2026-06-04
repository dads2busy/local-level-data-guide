# Load required libraries
library(tidycensus)
library(tigris)
library(sf)
library(dplyr)
library(areal)
library(aws.s3)

# Function to download Ookla data for a specific quarter
download_ookla_data <- function(type = "fixed", year = 2024, quarter = 1, format = "parquet") {
  
  # Construct the S3 path
  if (format == "parquet") {
    file_path <- paste0("parquet/performance/type=", type, "/year=", year, 
                        "/quarter=", quarter, "/", year, "-", 
                        sprintf("%02d", quarter*3), "-01_performance_", 
                        type, "_tiles.parquet")
  } else {
    file_path <- paste0("shapefiles/performance/type=", type, "/year=", year,
                        "/quarter=", quarter, "/", year, "-",
                        sprintf("%02d", quarter*3), "-01_performance_",
                        type, "_tiles.zip")
  }
  
  # Create directory if it doesn't exist
  dir.create("ookla_data", showWarnings = FALSE)
  
  # Download from S3 (no credentials required)
  system(paste0("aws s3 cp s3://ookla-open-data/", file_path, 
                " ./ookla_data/ --no-sign-request"))
  
  return(file_path)
}

# Install the package from GitHub
install.packages("remotes")
remotes::install_github("teamookla/ooklaOpenDataR")
library(ooklaOpenDataR)

download_ookla_data <- function(service = "fixed", quarter = 1, year = 2024, sf = FALSE) {
  # Load required library
  library(ooklaOpenDataR)
  
  # Download performance tiles
  data <- get_performance_tiles(
    service = service,  # "fixed" or "mobile"
    quarter = quarter,  # 1, 2, 3, or 4
    year = year,       # Available from 2019 onwards
    sf = sf           # TRUE for sf object, FALSE for data frame
  )
  
  return(data)
}

# Example usage:
# Fixed broadband data for Q2 2024
fixed_data <- download_ookla_data(service = "fixed", quarter = 2, year = 2023)


download.file("https://ookla-open-data.s3.amazonaws.com/shapefiles/performance/type=fixed/year=2024/quarter=4/2024-10-01_performance_fixed_tiles.zip", 
              destfile = "git/2024-10-01_performance_fixed_tiles.zip")

ook <- sf::read_sf("downloads/2024-10-01_performance_fixed_tiles/gps_fixed_tiles.shp")

