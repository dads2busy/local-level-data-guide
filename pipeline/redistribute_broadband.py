"""Redistribute Ookla broadband to civic associations; derive mean speeds."""
from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import pandas as pd
from sdc_redistribute import redistribute_direct

from pipeline import config

MIN_TESTS = 5  # statistical-reliability filter on source tiles


def redistribute_broadband(
    counts_long: pd.DataFrame, source_geo: Path, target_geo: Path
) -> pd.DataFrame:
    """Return per-civic-association tests and derived download/upload Mbps."""
    result = redistribute_direct(
        source_df=counts_long,
        source_geo=source_geo,
        target_geos={"civic_association": target_geo},
        count_cols=["tests", "d_product", "u_product"],
        source_id="geoid",
    )
    wide = result.pivot_table(
        index="geoid", columns="measure", values="value", aggfunc="first"
    ).reset_index()
    wide.columns.name = None
    wide = wide.rename(
        columns={
            "tests_direct": "tests",
            "d_product_direct": "d_product",
            "u_product_direct": "u_product",
        }
    )
    valid = wide["tests"] > 0
    wide["download_mbps"] = (wide["d_product"] / wide["tests"].where(valid)) / 1000
    wide["upload_mbps"] = (wide["u_product"] / wide["tests"].where(valid)) / 1000
    return wide[["geoid", "tests", "download_mbps", "upload_mbps"]]


def build_counts_long(tiles: gpd.GeoDataFrame) -> pd.DataFrame:
    """Build the long-format count frame from raw Ookla tiles."""
    t = tiles[tiles["tests"] >= MIN_TESTS].copy()
    t["d_product"] = t["avg_d_kbps"] * t["tests"]
    t["u_product"] = t["avg_u_kbps"] * t["tests"]
    long = t[["quadkey", "tests", "d_product", "u_product"]].melt(
        id_vars="quadkey", var_name="measure", value_name="value"
    )
    long = long.rename(columns={"quadkey": "geoid"})
    long["year"] = config.OOKLA_YEAR
    return long


def main() -> None:
    tiles = gpd.read_file(config.OOKLA_TILES)
    tiles["geoid"] = tiles["quadkey"].astype(str)
    long = build_counts_long(tiles)
    # Write a geoid-keyed source file for redistribute_direct
    src = tiles[["geoid", "geometry"]].copy()
    src_path = config.DATA / "_ookla_src.geojson"
    src.to_file(src_path, driver="GeoJSON")
    out = redistribute_broadband(long, src_path, config.CIVIC_ASSOC)
    out.to_csv(config.CIVIC_BROADBAND, index=False)
    src_path.unlink(missing_ok=True)
    print(f"Wrote {len(out)} civic-association broadband rows → {config.CIVIC_BROADBAND}")


if __name__ == "__main__":
    main()
