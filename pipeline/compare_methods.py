"""Compare area-weighted vs parcel-weighted income per civic association."""
from __future__ import annotations

import geopandas as gpd
import pandas as pd

from pipeline import config


def compare_income(area: pd.DataFrame, parcel: pd.DataFrame) -> pd.DataFrame:
    """Join the two methods' mean income; add diff (parcel - area) and pct_diff."""
    a = area[["geoid", "mean_income"]].rename(columns={"mean_income": "mean_income_area"})
    p = parcel[["geoid", "mean_income"]].rename(columns={"mean_income": "mean_income_parcel"})
    out = a.merge(p, on="geoid", how="outer")
    out["diff"] = out["mean_income_parcel"] - out["mean_income_area"]
    out["pct_diff"] = 100 * out["diff"] / out["mean_income_area"].where(
        out["mean_income_area"] > 0
    )
    return out


def main() -> None:
    civ = gpd.read_file(config.CIVIC_ASSOC)[["geoid", "region_name", "geometry"]]
    area = pd.read_csv(config.CIVIC_INCOME, dtype={"geoid": str})
    parcel = pd.read_csv(config.CIVIC_INCOME_PARCELS, dtype={"geoid": str})
    cmp = compare_income(area, parcel)
    gdf = civ.merge(cmp, on="geoid", how="left")
    gdf = gpd.GeoDataFrame(gdf, geometry="geometry", crs=civ.crs)

    # Honest accounting: report parcel-method household total vs ACS source.
    acs = gpd.read_file(config.ACS_COUNTS)
    src_hh = float(acs["households"].sum())
    parcel_hh = float(pd.read_csv(config.CIVIC_INCOME_PARCELS)["households"].sum())
    pct = 100 * (parcel_hh - src_hh) / src_hh if src_hh else 0.0
    print(f"Household totals, ACS source: {src_hh:,.0f}; parcel method: {parcel_hh:,.0f} ({pct:+.1f}%)")

    gdf.to_file(config.CIVIC_INCOME_COMPARISON, driver="GeoJSON")
    print(f"Wrote {len(gdf)} comparison rows → {config.CIVIC_INCOME_COMPARISON}")


if __name__ == "__main__":
    main()
