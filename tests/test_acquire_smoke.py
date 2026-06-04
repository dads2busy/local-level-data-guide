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
