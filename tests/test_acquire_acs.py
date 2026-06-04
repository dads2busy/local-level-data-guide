import pandas as pd

from pipeline.acquire_acs import _sanitize_counts


def test_negative_sentinels_become_zero():
    df = pd.DataFrame(
        {
            "GEOID": ["a", "b", "c"],
            "agg_income": [1_000_000.0, -666666666.0, 500_000.0],
            "households": [10.0, 0.0, -999999999.0],
        }
    )
    out = _sanitize_counts(df)
    assert out["agg_income"].tolist() == [1_000_000.0, 0.0, 500_000.0]
    assert out["households"].tolist() == [10.0, 0.0, 0.0]


def test_valid_values_unchanged():
    df = pd.DataFrame({"GEOID": ["a"], "agg_income": [123.0], "households": [4.0]})
    out = _sanitize_counts(df)
    assert out["agg_income"].tolist() == [123.0]
    assert out["households"].tolist() == [4.0]
