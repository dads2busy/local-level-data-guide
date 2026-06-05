"""Acquire Arlington MHUD parcel polygons and reduce them to unit-bearing centroids."""
from __future__ import annotations

import json
import urllib.parse
import urllib.request

import geopandas as gpd
import pandas as pd

from pipeline import config

LAYER = (
    "https://arlgis.arlingtonva.us/arcgis/rest/services/Open_Data/"
    "od_MHUD_Polygons/FeatureServer/0/query"
)
PAGE = 2000


def _fetch_page(offset: int) -> gpd.GeoDataFrame | None:
    params = {
        "where": "1=1",
        "outFields": "Total_Units,Unit_Type",
        "outSR": "4326",
        "resultOffset": str(offset),
        "resultRecordCount": str(PAGE),
        "f": "geojson",
    }
    url = LAYER + "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=60) as resp:  # noqa: S310
        data = json.load(resp)
    feats = data.get("features", [])
    if not feats:
        return None
    return gpd.GeoDataFrame.from_features(feats, crs="EPSG:4326")


def fetch_parcels() -> gpd.GeoDataFrame:
    """Page through the MHUD FeatureServer and return all parcel polygons."""
    parts: list[gpd.GeoDataFrame] = []
    offset = 0
    while True:
        page = _fetch_page(offset)
        if page is None or len(page) == 0:
            break
        parts.append(page)
        if len(page) < PAGE:
            break
        offset += PAGE
    gdf = gpd.GeoDataFrame(pd.concat(parts, ignore_index=True), crs="EPSG:4326")
    return gdf


def to_centroids(polys: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Reduce parcel polygons to centroids, keeping Total_Units and Unit_Type."""
    cent = polys.copy()
    # representative_point() is guaranteed inside the polygon (unlike centroid)
    cent["geometry"] = cent.geometry.representative_point()
    return cent[["Total_Units", "Unit_Type", "geometry"]]


def main() -> None:
    polys = fetch_parcels()
    pts = to_centroids(polys)
    pts.to_file(config.PARCELS, driver="GeoJSON")
    print(f"Wrote {len(pts)} parcel centroids → {config.PARCELS}")


if __name__ == "__main__":
    main()
