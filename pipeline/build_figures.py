"""Regenerate every visual asset (figures + diagrams) for the guide."""
from __future__ import annotations

from pathlib import Path

from pipeline import diagrams, figures

ROOT = Path(__file__).resolve().parent.parent

EXPECTED = [
    "figures/fig_transformation_3panel.png",
    "figures/fig_locator_civic.png",
    "figures/fig_ookla_tiles.png",
    "figures/map_income.png",
    "figures/map_speed.png",
    "figures/map_ratio.png",
    "figures/map_bivariate.png",
    "figures/scatter_income_speed.png",
    "figures/diagrams/dataflow.png",
    "figures/diagrams/acs_transform.png",
    "figures/diagrams/ookla_transform.png",
]


def main() -> None:
    figures.main()
    diagrams.main()
    missing = [p for p in EXPECTED if not (ROOT / p).exists()]
    if missing:
        raise SystemExit(f"Missing expected assets: {missing}")
    print(f"All {len(EXPECTED)} guide assets present.")


if __name__ == "__main__":
    main()
