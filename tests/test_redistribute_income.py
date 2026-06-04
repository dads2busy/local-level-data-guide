import geopandas as gpd
import pandas as pd
from shapely.geometry import box
from pipeline.redistribute_income import redistribute_income


def _write(tmp_path):
    # One source block group (2x2). Two target civic assocs split it 50/50.
    src = gpd.GeoDataFrame(
        {"geoid": ["BG1"]}, geometry=[box(0, 0, 2, 2)], crs="EPSG:3857"
    )
    tgt = gpd.GeoDataFrame(
        {"geoid": ["CA1", "CA2"]},
        geometry=[box(0, 0, 1, 2), box(1, 0, 2, 2)],
        crs="EPSG:3857",
    )
    src_path = tmp_path / "bg.geojson"
    tgt_path = tmp_path / "ca.geojson"
    src.to_file(src_path, driver="GeoJSON")
    tgt.to_file(tgt_path, driver="GeoJSON")
    return src_path, tgt_path


def test_mean_income_is_preserved_when_split_evenly(tmp_path):
    # BG1: $1,000,000 aggregate income across 10 households → mean $100,000.
    # Split 50/50 by area → each CA gets $500,000 / 5 households → mean $100,000.
    src_path, tgt_path = _write(tmp_path)
    counts = pd.DataFrame(
        {
            "geoid": ["BG1", "BG1"],
            "year": [2021, 2021],
            "measure": ["agg_income", "households"],
            "value": [1_000_000.0, 10.0],
        }
    )
    out = redistribute_income(counts, src_path, tgt_path)
    out = out.set_index("geoid").sort_index()
    assert out.loc["CA1", "households"] == 5.0
    assert out.loc["CA2", "households"] == 5.0
    assert out.loc["CA1", "mean_income"] == 100_000.0
    assert out.loc["CA2", "mean_income"] == 100_000.0
