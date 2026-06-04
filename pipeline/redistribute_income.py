"""Redistribute ACS income counts to civic associations and derive mean income."""
from __future__ import annotations

from pathlib import Path

import geopandas as gpd
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
    # ACS counts GeoJSON uses uppercase GEOID; rename to the lowercase `geoid`
    # that redistribute_direct expects, for both the long-format counts and the
    # source geometry. Write a geoid-keyed source file for redistribute_direct.
    bg = gpd.read_file(config.ACS_COUNTS).rename(columns={"GEOID": "geoid"})
    long = bg[["geoid", "agg_income", "households"]].melt(
        id_vars="geoid", var_name="measure", value_name="value"
    )
    long["year"] = config.ACS_YEAR

    src_path = config.DATA / "_acs_src.geojson"
    bg[["geoid", "geometry"]].to_file(src_path, driver="GeoJSON")
    out = redistribute_income(long, src_path, config.CIVIC_ASSOC)
    src_path.unlink(missing_ok=True)

    out.to_csv(config.CIVIC_INCOME, index=False)
    print(f"Wrote {len(out)} civic-association income rows → {config.CIVIC_INCOME}")


if __name__ == "__main__":
    main()
