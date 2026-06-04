"""Combine income + broadband and compute derived policy metrics."""
from __future__ import annotations

import geopandas as gpd
import pandas as pd

from pipeline import config


def _tercile(series: pd.Series) -> pd.Series:
    """Return 1/2/3 tercile labels by rank (robust to ties and NaN)."""
    ranks = series.rank(method="first")
    return pd.qcut(ranks, 3, labels=[1, 2, 3]).astype("Int64")


def add_derived_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """Add income_speed_ratio and bivariate_class (income-speed terciles)."""
    out = df.copy()
    out["income_speed_ratio"] = out["mean_income"] / out["download_mbps"].where(
        out["download_mbps"] > 0
    )
    inc = _tercile(out["mean_income"])
    spd = _tercile(out["download_mbps"])
    out["bivariate_class"] = inc.astype(str) + "-" + spd.astype(str)
    return out


def main() -> None:
    civ = gpd.read_file(config.CIVIC_ASSOC)[["geoid", "region_name", "geometry"]]
    income = pd.read_csv(config.CIVIC_INCOME, dtype={"geoid": str})
    broadband = pd.read_csv(config.CIVIC_BROADBAND, dtype={"geoid": str})
    merged = civ.merge(income, on="geoid", how="left").merge(
        broadband, on="geoid", how="left"
    )
    merged = add_derived_metrics(merged)
    gdf = gpd.GeoDataFrame(merged, geometry="geometry", crs=civ.crs)
    gdf.to_file(config.CIVIC_COMBINED, driver="GeoJSON")
    print(f"Wrote {len(gdf)} combined civic-association rows → {config.CIVIC_COMBINED}")


if __name__ == "__main__":
    main()
