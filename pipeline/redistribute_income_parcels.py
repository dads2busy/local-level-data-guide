"""Redistribute income through unit-weighted parcels (dasymetric), derive mean income."""
from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import pandas as pd
from sdc_redistribute import redistribute_parcels

from pipeline import config


def explode_by_units(parcels: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Replicate each parcel into Total_Units identical points; drop units <= 0."""
    p = parcels[parcels["Total_Units"] > 0].copy()
    reps = p["Total_Units"].astype(int).to_numpy()
    out = p.loc[p.index.repeat(reps)].reset_index(drop=True)
    return out


def redistribute_income_parcels(
    counts_long: pd.DataFrame,
    parcels: gpd.GeoDataFrame,
    source_geo: Path,
    target_geo: Path,
) -> pd.DataFrame:
    """Return per-civic-association agg_income, households, derived mean_income."""
    points = explode_by_units(parcels)
    result = redistribute_parcels(
        source_df=counts_long,
        parcel_centroids=points,
        source_geo=source_geo,
        target_geos={"civic_association": target_geo},
        count_cols=["agg_income", "households"],
        source_id="geoid",
    )
    wide = result.pivot_table(
        index="geoid", columns="measure", values="value", aggfunc="first"
    ).reset_index()
    wide.columns.name = None
    wide = wide.rename(
        columns={"agg_income_parcels": "agg_income", "households_parcels": "households"}
    )
    wide["mean_income"] = wide["agg_income"] / wide["households"].where(
        wide["households"] > 0
    )
    return wide[["geoid", "agg_income", "households", "mean_income"]]


def main() -> None:
    parcels = gpd.read_file(config.PARCELS)
    bg = gpd.read_file(config.ACS_COUNTS).rename(columns={"GEOID": "geoid"})
    long = bg[["geoid", "agg_income", "households"]].melt(
        id_vars="geoid", var_name="measure", value_name="value"
    )
    long["year"] = config.ACS_YEAR

    src_path = config.DATA / "_acs_src_parcels.geojson"
    bg[["geoid", "geometry"]].to_file(src_path, driver="GeoJSON")
    out = redistribute_income_parcels(long, parcels, src_path, config.CIVIC_ASSOC)
    src_path.unlink(missing_ok=True)

    out.to_csv(config.CIVIC_INCOME_PARCELS, index=False)
    print(f"Wrote {len(out)} parcel-weighted income rows → {config.CIVIC_INCOME_PARCELS}")


if __name__ == "__main__":
    main()
