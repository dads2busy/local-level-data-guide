# tests/test_maps.py
import geopandas as gpd
from shapely.geometry import box
from pipeline import maps


def _gdf():
    return gpd.GeoDataFrame(
        {"v": [1.0, 2.0]},
        geometry=[box(-77.1, 38.8, -77.0, 38.9), box(-77.0, 38.8, -76.9, 38.9)],
        crs="EPSG:4326",
    )


def test_to_plot_crs_reprojects_to_metric():
    out = maps.to_plot_crs(_gdf())
    assert out.crs.to_epsg() == 26918


def test_choropleth_returns_figure_with_axes():
    import matplotlib
    matplotlib.use("Agg")
    fig = maps.choropleth(_gdf(), "v", title="t", legend_label="v")
    assert fig is not None
    assert len(fig.axes) >= 1
