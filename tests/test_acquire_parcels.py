import geopandas as gpd
from shapely.geometry import box
from pipeline.acquire_parcels import to_centroids


def test_to_centroids_keeps_fields_and_makes_points():
    polys = gpd.GeoDataFrame(
        {"Total_Units": [1, 200], "Unit_Type": ["SFD", "MULTI"]},
        geometry=[box(0, 0, 1, 1), box(2, 2, 4, 4)],
        crs="EPSG:4326",
    )
    pts = to_centroids(polys)
    assert (pts.geometry.geom_type == "Point").all()
    assert list(pts.columns) == ["Total_Units", "Unit_Type", "geometry"]
    assert pts.crs.to_epsg() == 4326
