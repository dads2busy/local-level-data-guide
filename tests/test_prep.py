import geopandas as gpd
from shapely.geometry import box
from pipeline.prep import normalize_source


def _gdf(id_col):
    return gpd.GeoDataFrame(
        {id_col: [101, 102]},
        geometry=[box(0, 0, 1, 1), box(1, 0, 2, 1)],
        crs="EPSG:4326",
    )


def test_renames_id_to_geoid_as_string():
    out = normalize_source(_gdf("GEOID"), id_col="GEOID", target_crs="EPSG:3857")
    assert "geoid" in out.columns
    assert out["geoid"].tolist() == ["101", "102"]


def test_reprojects_to_target_crs():
    out = normalize_source(_gdf("GEOID"), id_col="GEOID", target_crs="EPSG:3857")
    assert out.crs.to_string() == "EPSG:3857"
