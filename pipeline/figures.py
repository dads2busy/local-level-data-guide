"""Generate every raster figure used in the guide, into ./figures."""
from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import matplotlib
import matplotlib.pyplot as plt

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


ALL_FIGURES = [
    fig_transformation_3panel,
    fig_locator,
    fig_ookla_tiles,
    fig_income,
    fig_speed,
    fig_ratio,
    fig_bivariate,
    fig_scatter,
]


def main() -> None:
    for fn in ALL_FIGURES:
        out = fn()
        print(f"wrote {out.relative_to(FIGURES.parent)}")


if __name__ == "__main__":
    main()
