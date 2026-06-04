"""Acquire Arlington ACS aggregate income + household counts (block group)."""
from __future__ import annotations

import os

import geopandas as gpd
import pandas as pd
from census import Census

from pipeline import config
from pipeline.acquire_geographies import fetch_block_groups


def fetch_acs_counts(api_key: str | None = None) -> pd.DataFrame:
    """Return a DataFrame: GEOID, agg_income, households for Arlington block groups."""
    key = api_key or os.environ.get("CENSUS_API_KEY")
    c = Census(key, year=config.ACS_YEAR)
    # The census library needs the API estimate suffix "E" on each variable
    # (e.g. B19025_001E), unlike tidycensus which strips it.
    agg_var = config.ACS_VARS["agg_income"] + "E"
    hh_var = config.ACS_VARS["households"] + "E"
    rows = c.acs5.state_county_blockgroup(
        fields=("NAME", agg_var, hh_var),
        state_fips=config.STATE_FIPS,
        county_fips=config.COUNTY_FIPS,
        blockgroup=Census.ALL,
        tract=Census.ALL,
    )
    df = pd.DataFrame(rows)
    df["GEOID"] = df["state"] + df["county"] + df["tract"] + df["block group"]
    df = df.rename(columns={agg_var: "agg_income", hh_var: "households"})
    return df[["GEOID", "agg_income", "households"]]


def main() -> None:
    counts = fetch_acs_counts()
    bg = fetch_block_groups()[["GEOID", "geometry"]]
    merged = bg.merge(counts, on="GEOID", how="left")
    gdf = gpd.GeoDataFrame(merged, geometry="geometry", crs=bg.crs)
    gdf.to_file(config.ACS_COUNTS, driver="GeoJSON")
    print(f"Wrote {len(gdf)} block groups with income counts → {config.ACS_COUNTS}")


if __name__ == "__main__":
    main()
