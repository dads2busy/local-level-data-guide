import pandas as pd
from pipeline.combine import add_derived_metrics


def test_ratio_and_bivariate_classes():
    df = pd.DataFrame(
        {
            "geoid": ["A", "B", "C"],
            "mean_income": [60_000.0, 90_000.0, 120_000.0],
            "download_mbps": [100.0, 200.0, 300.0],
        }
    )
    out = add_derived_metrics(df).set_index("geoid")
    # ratio = income / speed
    assert out.loc["A", "income_speed_ratio"] == 600.0
    # 3 rows over 3 terciles → income classes 1,2,3 and speed classes 1,2,3
    assert out.loc["A", "bivariate_class"] == "1-1"
    assert out.loc["C", "bivariate_class"] == "3-3"
