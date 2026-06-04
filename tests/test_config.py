from pipeline import config


def test_arlington_fips():
    assert config.STATE_FIPS == "51"
    assert config.COUNTY_FIPS == "013"


def test_target_crs_is_projected():
    # Virginia State Plane North (US ft) — projected, not geographic
    assert config.TARGET_CRS == "EPSG:3968"


def test_acs_variables_are_counts():
    # Aggregate household income and total households (extensive counts)
    assert config.ACS_VARS["agg_income"] == "B19025_001"
    assert config.ACS_VARS["households"] == "B11001_001"
