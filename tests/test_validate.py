import pandas as pd
import pytest
from pipeline.validate import check_total_preserved, check_ranges


def test_total_preserved_passes_within_tolerance():
    check_total_preserved(source_total=1000.0, target_total=1004.0, tol=0.01)


def test_total_preserved_fails_outside_tolerance():
    with pytest.raises(AssertionError):
        check_total_preserved(source_total=1000.0, target_total=1100.0, tol=0.01)


def test_ranges_rejects_negative_speed():
    df = pd.DataFrame({"download_mbps": [-5.0], "mean_income": [50_000.0]})
    with pytest.raises(AssertionError):
        check_ranges(df)
