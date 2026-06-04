"""Reusable map plotting helpers built on the guide style system."""
from __future__ import annotations

import geopandas as gpd
import matplotlib.pyplot as plt

from pipeline import style

style.apply_style()


def to_plot_crs(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Reproject to the metric plotting CRS (UTM 18N)."""
    return gdf.to_crs(style.MAP_CRS)


def choropleth(
    gdf: gpd.GeoDataFrame,
    column: str,
    *,
    title: str,
    legend_label: str,
    cmap: str = style.SEQUENTIAL,
    scheme: str = "Quantiles",
    k: int = 5,
    fmt: str = "{:.0f}",
    ax=None,
):
    """Return a Figure with a classed choropleth of ``column``."""
    g = to_plot_crs(gdf)
    if ax is None:
        fig, ax = plt.subplots(figsize=(7, 8))
    else:
        fig = ax.figure
    g.plot(
        column=column, cmap=cmap, scheme=scheme, k=k, legend=True,
        edgecolor="white", linewidth=0.4, ax=ax,
        legend_kwds={"title": legend_label, "loc": "lower right", "fmt": fmt},
        missing_kwds={"color": style.PALETTE["light"], "label": "No data"},
    )
    ax.set_title(title)
    ax.set_axis_off()
    style.add_north_arrow(ax)
    style.add_scale_bar(ax)
    return fig


def bivariate_map(
    gdf: gpd.GeoDataFrame,
    class_col: str = "bivariate_class",
    *,
    title: str,
    ax=None,
):
    """Return a Figure with a 3×3 bivariate choropleth and an inset key."""
    g = to_plot_crs(gdf)
    colors = g[class_col].map(style.BIVARIATE_COLORS).fillna(style.PALETTE["light"])
    if ax is None:
        fig, ax = plt.subplots(figsize=(7, 8))
    else:
        fig = ax.figure
    g.plot(color=colors, edgecolor="white", linewidth=0.4, ax=ax)
    ax.set_title(title)
    ax.set_axis_off()
    style.add_north_arrow(ax)
    style.add_scale_bar(ax)
    inset = fig.add_axes([0.16, 0.16, 0.16, 0.16])
    style.bivariate_legend(inset)
    return fig


def locator_map(
    gdf: gpd.GeoDataFrame,
    *,
    title: str,
    label_col: str | None = None,
    facecolor: str | None = None,
    ax=None,
):
    """Return a Figure outlining ``gdf`` (optionally labelled at centroids)."""
    g = to_plot_crs(gdf)
    if ax is None:
        fig, ax = plt.subplots(figsize=(7, 8))
    else:
        fig = ax.figure
    g.plot(
        ax=ax, edgecolor=style.PALETTE["ink"], linewidth=0.5,
        facecolor=facecolor or style.PALETTE["light"],
    )
    if label_col:
        for _, row in g.iterrows():
            c = row.geometry.representative_point()
            ax.annotate(row[label_col], (c.x, c.y), fontsize=5,
                        ha="center", color=style.PALETTE["ink"])
    ax.set_title(title)
    ax.set_axis_off()
    style.add_north_arrow(ax)
    style.add_scale_bar(ax)
    return fig


def scatter(
    df,
    x: str,
    y: str,
    *,
    title: str,
    xlabel: str,
    ylabel: str,
    ax=None,
):
    """Return a Figure scatter of ``y`` vs ``x`` with a correlation annotation."""
    if ax is None:
        fig, ax = plt.subplots(figsize=(7, 6))
    else:
        fig = ax.figure
    ax.scatter(df[x], df[y], color=style.PALETTE["blue"], s=28,
               edgecolor="white", linewidth=0.5, alpha=0.9)
    r = df[[x, y]].corr().iloc[0, 1]
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.annotate(f"r = {r:.2f}", xy=(0.04, 0.93), xycoords="axes fraction",
                fontsize=11, color=style.PALETTE["ink"], fontweight="bold")
    return fig
