"""Acquire Arlington census block-group geometries via pygris."""
from __future__ import annotations

import geopandas as gpd
from pygris import block_groups

from pipeline import config


def fetch_block_groups() -> gpd.GeoDataFrame:
    """Download Arlington County (VA/013) block groups for the ACS vintage."""
    bg = block_groups(
        state=config.STATE_FIPS,
        county=config.COUNTY_FIPS,
        year=config.ACS_YEAR,
        cb=True,
    )
    return bg


def main() -> None:
    bg = fetch_block_groups()
    bg.to_file(config.BLOCK_GROUPS, driver="GeoJSON")
    print(f"Wrote {len(bg)} block groups → {config.BLOCK_GROUPS}")


if __name__ == "__main__":
    main()
