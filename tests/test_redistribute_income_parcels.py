import geopandas as gpd
import pandas as pd
from shapely.geometry import box, Point
from pipeline.redistribute_income_parcels import explode_by_units, redistribute_income_parcels


def test_explode_by_units_replicates_and_drops_nonpositive():
    parcels = gpd.GeoDataFrame(
        {"Total_Units": [1, 3, 0]},
        geometry=[Point(0, 0), Point(1, 1), Point(2, 2)],
        crs="EPSG:3857",
    )
    out = explode_by_units(parcels)
    assert len(out) == 4              # 1 + 3, the 0-unit parcel dropped
    assert (out.geometry == Point(1, 1)).sum() == 3


def _write(tmp_path):
    src = gpd.GeoDataFrame({"geoid": ["BG1"]}, geometry=[box(0, 0, 10, 10)], crs="EPSG:3857")
    tgt = gpd.GeoDataFrame(
        {"geoid": ["CA1", "CA2"]},
        geometry=[box(0, 0, 5, 10), box(5, 0, 10, 10)], crs="EPSG:3857",
    )
    sp = tmp_path / "bg.geojson"; tp = tmp_path / "ca.geojson"
    src.to_file(sp, driver="GeoJSON"); tgt.to_file(tp, driver="GeoJSON")
    return sp, tp


def test_parcel_redistribution_splits_by_unit_points(tmp_path):
    # BG1: $1,000,000 income / 10 households spread over 10 unit-points:
    # 6 points in CA1 (left), 4 in CA2 (right). Each point => 100,000 income, 1 hh.
    sp, tp = _write(tmp_path)
    pts = [Point(x, 5) for x in (1, 1.5, 2, 2.5, 3, 3.5)] + [Point(x, 5) for x in (6, 7, 8, 9)]
    parcels = gpd.GeoDataFrame({"Total_Units": [1] * 10}, geometry=pts, crs="EPSG:3857")
    counts = pd.DataFrame({
        "geoid": ["BG1", "BG1"], "year": [2021, 2021],
        "measure": ["agg_income", "households"], "value": [1_000_000.0, 10.0],
    })
    out = redistribute_income_parcels(counts, parcels, sp, tp).set_index("geoid").sort_index()
    assert out.loc["CA1", "households"] == 6.0
    assert out.loc["CA2", "households"] == 4.0
    assert round(out.loc["CA1", "mean_income"], 2) == 100_000.0
