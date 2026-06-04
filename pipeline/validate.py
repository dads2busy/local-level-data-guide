"""Integrity checks on redistributed outputs."""
from __future__ import annotations

import pandas as pd


def check_total_preserved(source_total: float, target_total: float, tol: float = 0.01) -> None:
    """Assert target total matches source total within relative tolerance ``tol``."""
    if source_total == 0:
        return
    rel = abs(target_total - source_total) / abs(source_total)
    assert rel <= tol, f"total drift {rel:.3%} exceeds {tol:.3%}"


def check_ranges(df: pd.DataFrame) -> None:
    """Assert speed/income columns are non-negative where present."""
    for col in ("download_mbps", "upload_mbps", "mean_income", "households"):
        if col in df.columns:
            vals = df[col].dropna()
            assert (vals >= 0).all(), f"{col} has negative values"


def main() -> None:
    import geopandas as gpd
    from pipeline import config

    combined = gpd.read_file(config.CIVIC_COMBINED)
    acs = gpd.read_file(config.ACS_COUNTS)
    check_total_preserved(
        acs["households"].sum(), combined["households"].sum(), tol=0.02
    )
    check_ranges(combined)
    print("Validation passed.")


if __name__ == "__main__":
    main()
