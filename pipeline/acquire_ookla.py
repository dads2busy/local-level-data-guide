"""Acquire Ookla fixed-broadband tiles for Arlington from S3 open data."""
from __future__ import annotations

import geopandas as gpd
import pandas as pd
from shapely import wkt

from pipeline import config
from pipeline.acquire_geographies import fetch_block_groups


def _s3_path() -> str:
    month = config.OOKLA_QUARTER * 3 - 2  # Q1->01, Q2->04, Q3->07, Q4->10
    return config.OOKLA_S3.format(
        year=config.OOKLA_YEAR, quarter=config.OOKLA_QUARTER, month=month
    )


def fetch_ookla_tiles() -> gpd.GeoDataFrame:
    """Download and bbox-filter Ookla tiles to Arlington County."""
    df = pd.read_parquet(_s3_path(), storage_options={"anon": True})
    df["geometry"] = df["tile"].apply(wkt.loads)
    tiles = gpd.GeoDataFrame(df, geometry="geometry", crs="EPSG:4326")

    bbox = fetch_block_groups().to_crs("EPSG:4326").total_bounds  # minx,miny,maxx,maxy
    minx, miny, maxx, maxy = bbox
    return tiles.cx[minx:maxx, miny:maxy].copy()


def main() -> None:
    tiles = fetch_ookla_tiles()
    cols = ["quadkey", "avg_d_kbps", "avg_u_kbps", "avg_lat_ms", "tests", "devices", "geometry"]
    tiles[cols].to_file(config.OOKLA_TILES, driver="GeoJSON")
    print(f"Wrote {len(tiles)} Ookla tiles → {config.OOKLA_TILES}")


if __name__ == "__main__":
    main()
