import geopandas as gpd
import pandas as pd
from shapely.geometry import box
from pipeline.redistribute_broadband import redistribute_broadband


def _write(tmp_path):
    src = gpd.GeoDataFrame(
        {"geoid": ["T1"]}, geometry=[box(0, 0, 2, 2)], crs="EPSG:3857"
    )
    tgt = gpd.GeoDataFrame(
        {"geoid": ["CA1", "CA2"]},
        geometry=[box(0, 0, 1, 2), box(1, 0, 2, 2)],
        crs="EPSG:3857",
    )
    src_path = tmp_path / "tiles.geojson"
    tgt_path = tmp_path / "ca.geojson"
    src.to_file(src_path, driver="GeoJSON")
    tgt.to_file(tgt_path, driver="GeoJSON")
    return src_path, tgt_path


def test_download_speed_derived_from_count_weighting(tmp_path):
    # One tile, 200,000 kbps, 10 tests. Split 50/50 → each CA: 5 tests,
    # d_product 1,000,000 → mean 200,000 kbps → 200 Mbps.
    src_path, tgt_path = _write(tmp_path)
    long = pd.DataFrame(
        {
            "geoid": ["T1", "T1", "T1"],
            "year": [2023, 2023, 2023],
            "measure": ["tests", "d_product", "u_product"],
            "value": [10.0, 2_000_000.0, 500_000.0],
        }
    )
    out = redistribute_broadband(long, src_path, tgt_path).set_index("geoid").sort_index()
    assert out.loc["CA1", "tests"] == 5.0
    assert round(out.loc["CA1", "download_mbps"], 3) == 200.0
    assert round(out.loc["CA1", "upload_mbps"], 3) == 50.0
