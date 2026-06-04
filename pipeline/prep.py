"""Normalize source geometries for redistribution."""
from __future__ import annotations

import geopandas as gpd


def normalize_source(
    gdf: gpd.GeoDataFrame, id_col: str, target_crs: str
) -> gpd.GeoDataFrame:
    """Return a copy with the id column renamed to ``geoid`` (str) and reprojected.

    Parameters
    ----------
    gdf : GeoDataFrame with an identifier column ``id_col``.
    id_col : name of the source identifier column.
    target_crs : CRS to reproject to (e.g. ``"EPSG:3968"``).
    """
    out = gdf.copy()
    out = out.rename(columns={id_col: "geoid"})
    out["geoid"] = out["geoid"].astype(str)
    out = out.to_crs(target_crs)
    return out
