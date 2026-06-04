"""Redistribute ACS income counts to civic associations and derive mean income."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
from sdc_redistribute import redistribute_direct

from pipeline import config


def redistribute_income(
    counts_long: pd.DataFrame, source_geo: Path, target_geo: Path
) -> pd.DataFrame:
    """Return per-civic-association agg_income, households, and derived mean_income.

    ``counts_long`` is long format (geoid, year, measure, value) with measures
    ``agg_income`` and ``households``.
    """
    result = redistribute_direct(
        source_df=counts_long,
        source_geo=source_geo,
        target_geos={"civic_association": target_geo},
        count_cols=["agg_income", "households"],
        source_id="geoid",
    )
    # result is long with measures agg_income_direct / households_direct
    wide = result.pivot_table(
        index="geoid", columns="measure", values="value", aggfunc="first"
    ).reset_index()
    wide.columns.name = None
    wide = wide.rename(
        columns={"agg_income_direct": "agg_income", "households_direct": "households"}
    )
    # Mean household income is an INTENSIVE quantity derived from two counts.
    wide["mean_income"] = wide["agg_income"] / wide["households"].where(
        wide["households"] > 0
    )
    return wide[["geoid", "agg_income", "households", "mean_income"]]


def main() -> None:
    acs = __import__("geopandas").read_file(config.ACS_COUNTS)
    # The ACS counts GeoJSON uses uppercase GEOID; keep it consistent so that
    # redistribute_direct can match source_df rows to source_geo polygons.
    long = acs[["GEOID", "agg_income", "households"]].melt(
        id_vars="GEOID", var_name="measure", value_name="value"
    )
    long = long.rename(columns={"GEOID": "geoid"})
    long["year"] = config.ACS_YEAR
    # The ACS counts GeoJSON has GEOID (uppercase); rename so source_geo matches.
    import geopandas as gpd
    src_geo = config.ACS_COUNTS
    # Load, rename GEOID→geoid, save to a temp file so redistribute_direct finds
    # the 'geoid' column it expects.
    import tempfile, pathlib
    with tempfile.TemporaryDirectory() as td:
        tmp_src = pathlib.Path(td) / "bg.geojson"
        src_gdf = gpd.read_file(src_geo)
        src_gdf = src_gdf.rename(columns={"GEOID": "geoid"})
        src_gdf.to_file(tmp_src, driver="GeoJSON")
        out = redistribute_income(long, tmp_src, config.CIVIC_ASSOC)
    out.to_csv(config.CIVIC_INCOME, index=False)
    print(f"Wrote {len(out)} civic-association income rows → {config.CIVIC_INCOME}")


if __name__ == "__main__":
    main()
