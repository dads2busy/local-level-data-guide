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
    rows = c.acs5.state_county_blockgroup(
        fields=("NAME", config.ACS_VARS["agg_income"], config.ACS_VARS["households"]),
        state_fips=config.STATE_FIPS,
        county_fips=config.COUNTY_FIPS,
        blockgroup=Census.ALL,
        tract=Census.ALL,
    )
    df = pd.DataFrame(rows)
    df["GEOID"] = df["state"] + df["county"] + df["tract"] + df["block group"]
    df = df.rename(
        columns={
            config.ACS_VARS["agg_income"]: "agg_income",
            config.ACS_VARS["households"]: "households",
        }
    )
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
