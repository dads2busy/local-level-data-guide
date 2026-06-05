"""Shared visual identity for all guide figures: palette, colormaps, fonts."""
from __future__ import annotations

from pathlib import Path

import matplotlib.font_manager as fm
import matplotlib.patches
import matplotlib.pyplot as plt

PALETTE = {
    "ink": "#1B2A4A",
    "blue": "#2166AC",
    "teal": "#2A7F7F",
    "amber": "#D8732E",
    "gray": "#6B7280",
    "light": "#E5E7EB",
}

SEQUENTIAL = "viridis"
DIVERGING = "RdBu_r"

# 3×3 bivariate scheme (Joshua Stevens purple-blue), keyed "income-speed".
BIVARIATE_COLORS = {
    "1-1": "#e8e8e8", "1-2": "#ace4e4", "1-3": "#5ac8c8",
    "2-1": "#dfb0d6", "2-2": "#a5add3", "2-3": "#5698b9",
    "3-1": "#be64ac", "3-2": "#8c62aa", "3-3": "#3b4994",
}

FIG_DPI = 300
MAP_CRS = "EPSG:26918"   # UTM 18N (metres): accurate scale bars for Arlington

_FONTS_DIR = Path(__file__).resolve().parent.parent / "fonts"
_HEADING_FAMILY = "Libre Franklin"


def _register_fonts() -> str:
    """Register any TTFs in ./fonts. Return the heading family if available."""
    family = "sans-serif"
    if _FONTS_DIR.exists():
        for ttf in _FONTS_DIR.glob("*.ttf"):
            try:
                fm.fontManager.addfont(str(ttf))
            except Exception:  # noqa: BLE001
                continue
        names = {f.name for f in fm.fontManager.ttflist}
        if _HEADING_FAMILY in names:
            family = _HEADING_FAMILY
    return family


def apply_style() -> None:
    """Apply the guide's matplotlib rcParams. Safe to call repeatedly."""
    family = _register_fonts()
    plt.rcParams.update({
        "savefig.dpi": FIG_DPI,
        "figure.dpi": 150,
        "savefig.bbox": "tight",
        "font.family": family,
        "axes.titlesize": 14,
        "axes.titleweight": "bold",
        "axes.titlecolor": PALETTE["ink"],
        "axes.labelcolor": PALETTE["ink"],
        "text.color": PALETTE["ink"],
        "axes.edgecolor": PALETTE["gray"],
        "figure.facecolor": "white",
    })


def bivariate_legend(ax) -> None:
    """Draw a 3×3 bivariate key on the given (small inset) axes."""
    for i in (1, 2, 3):          # income tercile → vertical
        for j in (1, 2, 3):      # speed tercile → horizontal
            ax.add_patch(
                matplotlib.patches.Rectangle(
                    (j - 1, i - 1), 1, 1, color=BIVARIATE_COLORS[f"{i}-{j}"]
                )
            )
    ax.set_xlim(0, 3)
    ax.set_ylim(0, 3)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    # Use mathtext arrows so the glyph renders regardless of the label font
    # (Libre Franklin's variable-font subset lacks U+2192).
    ax.set_xlabel(r"Speed $\rightarrow$", fontsize=8)
    ax.set_ylabel(r"Income $\rightarrow$", fontsize=8)


def add_north_arrow(ax) -> None:
    """Add a simple north arrow in the upper-left of a map axes."""
    ax.annotate(
        "N",
        xy=(0.06, 0.96), xytext=(0.06, 0.86),
        xycoords="axes fraction",
        arrowprops=dict(arrowstyle="-|>", color=PALETTE["ink"], lw=1.5),
        ha="center", va="center", fontsize=11, fontweight="bold",
        color=PALETTE["ink"],
    )


def add_scale_bar(ax, length_m: float = 2000.0, label: str = "2 km") -> None:
    """Draw a scale bar of ``length_m`` metres (axes must be in a metric CRS)."""
    x0, x1 = ax.get_xlim()
    y0, y1 = ax.get_ylim()
    x = x0 + (x1 - x0) * 0.06
    y = y0 + (y1 - y0) * 0.06
    ax.plot([x, x + length_m], [y, y], color=PALETTE["ink"], lw=3,
            solid_capstyle="butt")
    ax.text(x + length_m / 2, y + (y1 - y0) * 0.015, label,
            ha="center", va="bottom", fontsize=8, color=PALETTE["ink"])
