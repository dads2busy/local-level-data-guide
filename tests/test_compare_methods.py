import pandas as pd
from pipeline.compare_methods import compare_income


def test_compare_computes_diff_and_pct():
    area = pd.DataFrame({"geoid": ["A", "B"], "mean_income": [100_000.0, 200_000.0]})
    parcel = pd.DataFrame({"geoid": ["A", "B"], "mean_income": [110_000.0, 150_000.0]})
    out = compare_income(area, parcel).set_index("geoid")
    assert out.loc["A", "mean_income_area"] == 100_000.0
    assert out.loc["A", "mean_income_parcel"] == 110_000.0
    assert out.loc["A", "diff"] == 10_000.0
    assert round(out.loc["A", "pct_diff"], 2) == 10.0
    assert out.loc["B", "diff"] == -50_000.0
