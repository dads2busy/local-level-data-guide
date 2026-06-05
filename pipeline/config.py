"""Central configuration: geographies, CRS, source identifiers, paths."""
from pathlib import Path

from dotenv import load_dotenv

# Load secrets (e.g. CENSUS_API_KEY) from a local .env if present. The file is
# gitignored; loading it here makes the key available to any pipeline module.
load_dotenv()

# Arlington County, Virginia
STATE_FIPS = "51"
COUNTY_FIPS = "013"
ACS_YEAR = 2021          # 5-year ACS vintage used throughout
OOKLA_YEAR = 2023
OOKLA_QUARTER = 2

# Area weighting is handled inside sdc-redistribute, which reprojects geographic
# inputs to EPSG:3857 before computing intersection areas. At county scale the
# choice of projected CRS is immaterial (<0.3% area-ratio spread vs State Plane),
# so the pipeline does not impose its own projected CRS.

# ACS variables are EXTENSIVE COUNTS (never redistribute the median directly).
# Mean household income is derived later as agg_income / households.
ACS_VARS = {
    "agg_income": "B19025_001",   # Aggregate household income (dollars)
    "households": "B11001_001",   # Total households (count)
}

# Ookla open data S3 parquet path template
OOKLA_S3 = (
    "s3://ookla-open-data/parquet/performance/type=fixed/"
    "year={year}/quarter={quarter}/"
    "{year}-{month:02d}-01_performance_fixed_tiles.parquet"
)

# Paths
ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

# Source / output dataset paths
CIVIC_ASSOC = DATA / "va013_geo_arl_2021_civic_associations.geojson"
BLOCK_GROUPS = DATA / "va013_block_groups.geojson"          # produced by acquire_geographies
BLOCKS = DATA / "va013_geo_blocks.geojson"                  # existing
ACS_COUNTS = DATA / "va013_acs_income_counts.geojson"       # produced by acquire_acs
OOKLA_TILES = DATA / "ookla_tiles_arlington.geojson"        # existing/refreshable
CIVIC_INCOME = DATA / "civic_income.csv"                    # produced by redistribute_income
CIVIC_BROADBAND = DATA / "civic_broadband.csv"             # produced by redistribute_broadband
CIVIC_COMBINED = DATA / "civic_combined.geojson"           # produced by combine
PARCELS = DATA / "va013_parcels.geojson"                   # produced by acquire_parcels
CIVIC_INCOME_PARCELS = DATA / "civic_income_parcels.csv"   # produced by redistribute_income_parcels
CIVIC_INCOME_COMPARISON = DATA / "civic_income_comparison.geojson"  # produced by compare_methods
