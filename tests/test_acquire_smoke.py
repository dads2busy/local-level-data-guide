# tests/test_acquire_smoke.py
import pytest


@pytest.mark.network
def test_fetch_block_groups_returns_arlington():
    from pipeline.acquire_geographies import fetch_block_groups

    bg = fetch_block_groups()
    assert len(bg) > 0
    assert "GEOID" in bg.columns
    # Arlington County block group GEOIDs start with 51013
    assert bg["GEOID"].str.startswith("51013").all()


@pytest.mark.network
def test_fetch_acs_counts_has_count_columns():
    from pipeline.acquire_acs import fetch_acs_counts

    df = fetch_acs_counts()
    assert {"GEOID", "agg_income", "households"} <= set(df.columns)
    assert (df["households"].dropna() >= 0).all()


@pytest.mark.network
def test_fetch_ookla_tiles_has_speed_columns():
    from pipeline.acquire_ookla import fetch_ookla_tiles

    tiles = fetch_ookla_tiles()
    assert len(tiles) > 0
    assert {"quadkey", "avg_d_kbps", "tests"} <= set(tiles.columns)


@pytest.mark.network
def test_fetch_parcels_has_units_and_type():
    from pipeline.acquire_parcels import fetch_parcels

    gdf = fetch_parcels()
    assert len(gdf) > 30000
    assert {"Total_Units", "Unit_Type"} <= set(gdf.columns)
    assert gdf["Total_Units"].sum() > 100000  # exploded units ≈ household count
