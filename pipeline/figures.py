"""Generate every raster figure used in the guide, into ./figures."""
from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import matplotlib
import matplotlib.pyplot as plt
import numpy as np

matplotlib.use("Agg")

from pipeline import config, maps, style

FIGURES = Path(__file__).resolve().parent.parent / "figures"


def _save(fig, name: str) -> Path:
    FIGURES.mkdir(exist_ok=True)
    out = FIGURES / name
    fig.savefig(out)
    plt.close(fig)
    return out


def _combined() -> gpd.GeoDataFrame:
    return gpd.read_file(config.CIVIC_COMBINED)


def fig_income() -> Path:
    fig = maps.choropleth(
        _combined(), "mean_income",
        title="Mean Household Income by Civic Association",
        legend_label="Mean income ($)", fmt="${:,.0f}",
    )
    return _save(fig, "map_income.png")


def fig_speed() -> Path:
    fig = maps.choropleth(
        _combined(), "download_mbps",
        title="Broadband Download Speed by Civic Association",
        legend_label="Download (Mbps)", fmt="{:.0f}",
    )
    return _save(fig, "map_speed.png")


def fig_ratio() -> Path:
    fig = maps.choropleth(
        _combined(), "income_speed_ratio",
        title="Income-to-Speed Ratio (\\$ per Mbps)",
        legend_label="$ per Mbps", cmap=style.DIVERGING, fmt="{:,.0f}",
    )
    return _save(fig, "map_ratio.png")


def fig_bivariate() -> Path:
    fig = maps.bivariate_map(
        _combined(),
        title="Digital Equity: Income × Broadband Speed",
    )
    return _save(fig, "map_bivariate.png")


def fig_scatter() -> Path:
    df = _combined()
    fig = maps.scatter(
        df, "mean_income", "download_mbps",
        title="Income vs. Broadband Speed",
        xlabel="Mean household income ($)", ylabel="Download speed (Mbps)",
    )
    return _save(fig, "scatter_income_speed.png")


def fig_locator() -> Path:
    civ = gpd.read_file(config.CIVIC_ASSOC)
    fig = maps.locator_map(
        civ, title="Arlington County Civic Associations",
        label_col="region_name",
    )
    return _save(fig, "fig_locator_civic.png")


def fig_ookla_tiles() -> Path:
    tiles = gpd.read_file(config.OOKLA_TILES)
    tiles["download_mbps"] = tiles["avg_d_kbps"] / 1000
    fig = maps.choropleth(
        tiles, "download_mbps",
        title="Ookla Speed-Test Tiles (Download Mbps)",
        legend_label="Download (Mbps)", k=5,
    )
    return _save(fig, "fig_ookla_tiles.png")


def fig_transformation_3panel() -> Path:
    """Hero figure: source broadband | source income | target civic associations."""
    tiles = gpd.read_file(config.OOKLA_TILES)
    tiles["download_mbps"] = tiles["avg_d_kbps"] / 1000
    acs = gpd.read_file(config.ACS_COUNTS)
    acs["mean_income"] = (
        acs["agg_income"] / acs["households"].where(acs["households"] > 0)
    )
    civ = _combined()

    fig, axes = plt.subplots(1, 3, figsize=(15, 6))
    maps.to_plot_crs(tiles).plot(
        column="download_mbps", cmap=style.SEQUENTIAL, ax=axes[0],
        edgecolor="none",
    )
    axes[0].set_title("Ookla tiles\n(610 m grid)")
    maps.to_plot_crs(acs).plot(
        column="mean_income", cmap=style.SEQUENTIAL, ax=axes[1],
        edgecolor="white", linewidth=0.3,
    )
    axes[1].set_title("ACS block groups\n(income)")
    maps.to_plot_crs(civ).plot(
        column="mean_income", cmap=style.SEQUENTIAL, ax=axes[2],
        edgecolor="white", linewidth=0.4,
    )
    axes[2].set_title("Civic associations\n(policy unit)")
    for ax in axes:
        ax.set_axis_off()
    fig.suptitle(
        "Transforming misaligned source data onto policy-relevant geographies",
        fontsize=14, fontweight="bold", color=style.PALETTE["ink"],
    )
    return _save(fig, "fig_transformation_3panel.png")


def fig_parcels() -> Path:
    parcels = gpd.read_file(config.PARCELS)
    parcels["category"] = parcels["Unit_Type"].where(
        parcels["Unit_Type"] == "MULTI", "Single-family"
    ).replace({"MULTI": "Multifamily"})
    fig = maps.points_map(
        parcels, size_col="Total_Units", cat_col="category",
        title="Arlington Housing Units by Parcel (size = units)",
    )
    return _save(fig, "map_parcels.png")


def fig_income_parcels() -> Path:
    cmp = gpd.read_file(config.CIVIC_INCOME_COMPARISON)
    fig = maps.choropleth(
        cmp, "mean_income_parcel",
        title="Mean Household Income (Parcel Method)",
        legend_label="Mean income ($)", fmt="${:,.0f}",
    )
    return _save(fig, "map_income_parcels.png")


def fig_income_diff() -> Path:
    cmp = gpd.read_file(config.CIVIC_INCOME_COMPARISON)
    fig = maps.choropleth(
        cmp, "diff",
        title="Income Difference: Parcel − Area Method",
        legend_label="$ difference", cmap=style.DIVERGING, fmt="${:,.0f}",
    )
    return _save(fig, "map_income_diff.png")


def fig_scatter_area_vs_parcel() -> Path:
    cmp = gpd.read_file(config.CIVIC_INCOME_COMPARISON)
    fig = maps.scatter(
        cmp, "mean_income_area", "mean_income_parcel",
        title="Area vs. Parcel Mean Income",
        xlabel="Area-weighted ($)", ylabel="Parcel-weighted ($)",
    )
    ax = fig.axes[0]
    lo = float(min(cmp["mean_income_area"].min(), cmp["mean_income_parcel"].min()))
    hi = float(max(cmp["mean_income_area"].max(), cmp["mean_income_parcel"].max()))
    ax.plot([lo, hi], [lo, hi], color=style.PALETTE["gray"], ls="--", lw=1)
    return _save(fig, "scatter_area_vs_parcel.png")


def fig_maup() -> Path:
    """Synthetic illustration of the Modifiable Areal Unit Problem.

    One east-west speed gradient, summarised under two district schemes. Bands
    cut across the gradient (panel 2) each span its full range and average out
    to a near-uniform value, hiding the variation; bands aligned with the
    gradient (panel 3) diverge sharply, revealing it. The field depends only on
    the east-west axis, so the contrast is exact rather than staged.
    """
    nx, ny = 48, 36
    cols = np.arange(nx)
    surface = 100.0 + (cols / (nx - 1)) * 240.0   # 100..340 Mbps, east-west only
    grid = np.tile(surface, (ny, 1))
    vmin, vmax = 100.0, 340.0
    cmap = style.SEQUENTIAL

    def bands(axis: int):
        out = np.empty_like(grid)
        n = grid.shape[axis]
        edges = [0, n // 3, 2 * n // 3, n]
        means = []
        for i in range(3):
            sl = slice(edges[i], edges[i + 1])
            block = grid[sl, :] if axis == 0 else grid[:, sl]
            m = float(block.mean())
            if axis == 0:
                out[sl, :] = m
            else:
                out[:, sl] = m
            means.append(m)
        return out, edges, means

    fig, axes = plt.subplots(1, 3, figsize=(13.5, 5.4))
    box = dict(boxstyle="round,pad=0.3", fc="white", ec="none", alpha=0.85)

    axes[0].imshow(grid, cmap=cmap, vmin=vmin, vmax=vmax, origin="lower", aspect="equal")
    axes[0].set_title("The underlying data")

    g2, e2, m2 = bands(0)  # stacked horizontal districts → hide the gradient
    axes[1].imshow(g2, cmap=cmap, vmin=vmin, vmax=vmax, origin="lower", aspect="equal")
    for y in e2[1:-1]:
        axes[1].axhline(y - 0.5, color="white", lw=2.5)
    for i in range(3):
        axes[1].text(nx / 2, (e2[i] + e2[i + 1]) / 2 - 0.5, f"{m2[i]:.0f}",
                     ha="center", va="center", color=style.PALETTE["ink"],
                     fontweight="bold", fontsize=12, bbox=box)
    axes[1].set_title("Boundaries A: variation hidden")

    g3, e3, m3 = bands(1)  # side-by-side vertical districts → reveal the gradient
    axes[2].imshow(g3, cmap=cmap, vmin=vmin, vmax=vmax, origin="lower", aspect="equal")
    for x in e3[1:-1]:
        axes[2].axvline(x - 0.5, color="white", lw=2.5)
    for i in range(3):
        axes[2].text((e3[i] + e3[i + 1]) / 2 - 0.5, ny / 2, f"{m3[i]:.0f}",
                     ha="center", va="center", color=style.PALETTE["ink"],
                     fontweight="bold", fontsize=12, bbox=box)
    axes[2].set_title("Boundaries B: variation revealed")

    for ax in axes:
        ax.set_xticks([])
        ax.set_yticks([])

    sm = plt.cm.ScalarMappable(norm=plt.Normalize(vmin, vmax), cmap=cmap)
    cbar = fig.colorbar(sm, ax=axes, orientation="horizontal",
                        fraction=0.046, pad=0.08, shrink=0.5)
    cbar.set_label("Download speed (Mbps)")

    fig.suptitle("The same data, summarised two ways", fontsize=14,
                 fontweight="bold", color=style.PALETTE["ink"])
    return _save(fig, "fig_maup.png")


def fig_disaggregation() -> Path:
    """Schematic of dasymetric redistribution: source area -> parcels -> target area.

    A source polygon's count is split across the parcels inside it, then the
    parcels are reaggregated under a different (overlapping) target boundary.
    Synthetic and deterministic; illustrates the spatial logic of the parcel
    method.
    """
    from shapely.geometry import Point, Polygon

    pal = style.PALETTE
    rng = np.random.default_rng(0)
    src = Polygon([(1.0, 2.0), (5.8, 1.4), (6.4, 5.6), (2.2, 6.8), (0.8, 4.2)])
    tgt = Polygon([(4.2, 2.8), (8.8, 2.2), (9.2, 7.2), (5.0, 7.8), (3.6, 5.2)])

    pts = []
    x = 1.2
    while x < 6.2:
        y = 1.8
        while y < 6.6:
            p = Point(x + rng.uniform(-0.16, 0.16), y + rng.uniform(-0.16, 0.16))
            if src.contains(p):
                pts.append((p.x, p.y))
            y += 0.92
        x += 0.92
    pts = np.array(pts)
    inside = np.array([tgt.contains(Point(px, py)) for px, py in pts])
    cx, cy = src.centroid.x, src.centroid.y
    n = len(pts)

    def xy(poly):
        xs, ys = poly.exterior.xy
        return list(xs), list(ys)

    sx, sy = xy(src)
    tx, ty = xy(tgt)
    fig, axes = plt.subplots(1, 3, figsize=(13.5, 5.0))

    axes[0].fill(sx, sy, color=pal["blue"], alpha=0.22, ec=pal["ink"], lw=1.5)
    axes[0].scatter(pts[:, 0], pts[:, 1], s=26, color=pal["ink"], zorder=3)
    axes[0].set_title("1. A source area and its parcels")

    axes[1].fill(sx, sy, color="none", ec=pal["ink"], lw=1.2)
    for px, py in pts:
        axes[1].plot([cx, px], [cy, py], color=pal["gray"], lw=0.6, alpha=0.6, zorder=1)
    axes[1].scatter([cx], [cy], s=70, color=pal["ink"], marker="s", zorder=4)
    axes[1].scatter(pts[:, 0], pts[:, 1], s=26, color=pal["blue"], zorder=3)
    axes[1].set_title(f"2. Disaggregate the total across {n} parcels")

    axes[2].fill(sx, sy, color="none", ec=pal["gray"], lw=1.0, ls="--")
    axes[2].fill(tx, ty, color=pal["teal"], alpha=0.22, ec=pal["ink"], lw=1.5)
    axes[2].scatter(pts[~inside, 0], pts[~inside, 1], s=16, color=pal["light"], zorder=3)
    axes[2].scatter(pts[inside, 0], pts[inside, 1], s=34, color=pal["amber"], zorder=4)
    axes[2].set_title(f"3. Reaggregate to a new boundary ({int(inside.sum())} parcels)")

    for ax in axes:
        ax.set_xlim(0, 9.6)
        ax.set_ylim(0.8, 8.4)
        ax.set_aspect("equal")
        ax.axis("off")

    fig.suptitle("Disaggregate to parcels, then reaggregate to a different area",
                 fontsize=14, fontweight="bold", color=pal["ink"])
    return _save(fig, "fig_disaggregation.png")


def fig_gap_reveal() -> Path:
    """Index hero: one county-wide number vs the 62-neighborhood reality.

    The left panel fills all of Arlington with a single household-weighted
    county mean; the right panel colors each civic association on the identical
    scale. A shared colorbar (with the county value marked) makes the left read
    as a single point on a range the right panel spans. Broadband download
    speed, the example the landing page itself opens with.
    """
    civ = maps.to_plot_crs(_combined())
    col = "download_mbps"
    vmin, vmax = float(civ[col].min()), float(civ[col].max())
    county_val = float((civ[col] * civ["households"]).sum() / civ["households"].sum())
    cmap = plt.get_cmap(style.SEQUENTIAL)
    norm = plt.Normalize(vmin, vmax)
    ink, gray = style.PALETTE["ink"], style.PALETTE["gray"]
    box = dict(boxstyle="round,pad=0.4", fc="white", ec="none", alpha=0.9)

    fig, axes = plt.subplots(
        1, 3, figsize=(13.5, 6.0), gridspec_kw={"width_ratios": [1, 0.22, 1]}
    )
    left, mid, right = axes

    from shapely.geometry import MultiPolygon, Polygon

    def _solid(geom):
        """Drop interior holes so the county reads as one solid silhouette."""
        if geom.geom_type == "Polygon":
            return Polygon(geom.exterior)
        return MultiPolygon([Polygon(p.exterior) for p in geom.geoms])

    county = civ.dissolve()
    county["geometry"] = county.geometry.apply(_solid)
    county.plot(ax=left, color=cmap(norm(county_val)), edgecolor=ink, linewidth=1.4)
    pt = county.geometry.iloc[0].representative_point()
    left.annotate(
        f"{county_val:.0f} Mbps\ncounty-wide average", xy=(pt.x, pt.y),
        ha="center", va="center", color=ink, fontsize=15, fontweight="bold", bbox=box,
    )
    left.set_title("What county data shows")
    left.text(0.5, -0.01, "one value for the whole county", transform=left.transAxes,
              ha="center", va="top", color=gray, fontsize=10)

    civ.plot(ax=right, column=col, cmap=cmap, norm=norm, edgecolor="white", linewidth=0.4)
    right.set_title("What's actually there")
    right.text(0.5, -0.01, f"{vmin:.0f} to {vmax:.0f} Mbps across 62 civic associations",
               transform=right.transAxes, ha="center", va="top", color=gray, fontsize=10)

    mid.set_xlim(0, 1)
    mid.set_ylim(0, 1)
    mid.annotate("", xy=(0.96, 0.52), xytext=(0.04, 0.52),
                 arrowprops=dict(arrowstyle="-|>", color=ink, lw=2.5))

    for ax in (left, right, mid):
        ax.set_axis_off()

    sm = plt.cm.ScalarMappable(norm=norm, cmap=cmap)
    cbar = fig.colorbar(sm, ax=axes, orientation="horizontal",
                        fraction=0.05, pad=0.07, shrink=0.55)
    cbar.set_label("Broadband download speed (Mbps)")
    cbar.ax.axvline(county_val, color=ink, lw=2.5)
    cbar.ax.annotate("county avg", xy=(county_val, 1), xytext=(county_val, 2.2),
                     textcoords=("data", "axes fraction"), ha="center", va="bottom",
                     color=ink, fontsize=8, fontweight="bold")

    fig.suptitle("One county-wide number hides 62 different neighborhoods",
                 fontsize=15, fontweight="bold", color=ink)
    return _save(fig, "fig_gap_reveal.png")


ALL_FIGURES = [
    fig_gap_reveal,
    fig_maup,
    fig_transformation_3panel,
    fig_locator,
    fig_ookla_tiles,
    fig_income,
    fig_speed,
    fig_ratio,
    fig_bivariate,
    fig_scatter,
    fig_parcels,
    fig_income_parcels,
    fig_income_diff,
    fig_scatter_area_vs_parcel,
    fig_disaggregation,
]


def main() -> None:
    for fn in ALL_FIGURES:
        out = fn()
        print(f"wrote {out.relative_to(FIGURES.parent)}")


if __name__ == "__main__":
    main()
