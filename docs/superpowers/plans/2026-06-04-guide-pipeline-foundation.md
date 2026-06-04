# Guide Pipeline Foundation — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the reproducible Python data + redistribution pipeline (and reorganized repo scaffolding) that produces the validated civic-association-level broadband and income datasets every figure in the guide will be generated from.

**Architecture:** A small set of single-responsibility Python modules under `pipeline/`. Acquisition modules pull source data (census geometries, ACS count tables, Ookla tiles) into `data/`. Redistribution modules use `sdc-redistribute`'s `redistribute_direct` to move *extensive counts* from source geographies onto Arlington's civic associations, then derive *intensive* rates (mean income, mean speed) from count ratios. A combine module joins them and computes derived metrics; a validate module asserts integrity. Pure-logic modules are TDD'd with small synthetic GeoDataFrame fixtures (no network); acquisition modules get smoke tests and are run manually against live sources.

**Tech Stack:** Python 3.12, `uv` for env management, `geopandas`, `pandas`, `pyarrow`, `pygris`, `census`, `contextily`/`mapclassify` (installed now, used in Plan 2), `sdc-redistribute`, `pytest`.

---

## File Structure

```
local_level_data/
  pyproject.toml          # Python project + deps (new)
  pipeline/
    __init__.py
    config.py             # FIPS codes, CRS, paths, ACS variable IDs, Ookla S3 path
    prep.py               # normalize source geojsons (rename id cols → geoid)
    acquire_geographies.py# pygris: block groups (+ blocks) for VA/013 → data/
    acquire_acs.py        # census API: aggregate income + households → data/
    acquire_ookla.py      # Ookla parquet from S3, bbox-filtered → data/
    redistribute_income.py# block groups → civic assoc; derive mean income
    redistribute_broadband.py # Ookla tiles → civic assoc; derive mean speeds
    combine.py            # join + ratio + bivariate classes → data/
    validate.py           # integrity checks on outputs
    run.py                # end-to-end runner
  tests/
    test_prep.py
    test_redistribute_income.py
    test_redistribute_broadband.py
    test_combine.py
    test_validate.py
    test_acquire_smoke.py # network-marked smoke tests
  data/                   # source + output datasets (4 existing geojsons kept)
  archive/                # old guide_consolidated.* + images/*.pptx (moved here)
  README.md               # reproduction instructions (rewritten)
```

---

## Task 1: Reorganize the repo and archive old artifacts

**Files:**
- Create: `archive/` (directory)
- Create: `pipeline/`, `tests/` (directories)
- Move: `guide_consolidated.tex|md|html|pdf`, `guide_consolidated_files/`, `images/`, top-level `*.R`, `.Rhistory`, `local_level_data.Rproj` → `archive/`
- Keep in place: `data/*.geojson`, `.git`, `.gitignore`, `docs/`

- [ ] **Step 1: Create directories and move old artifacts**

```bash
cd /Users/ads7fg/git/local_level_data
mkdir -p archive pipeline tests
git mv guide_consolidated.tex guide_consolidated.md guide_consolidated.html guide_consolidated.pdf archive/ 2>/dev/null || mv guide_consolidated.tex guide_consolidated.md guide_consolidated.html guide_consolidated.pdf archive/
mv guide_consolidated_files images archive/ 2>/dev/null || true
mv code1.R test.R download_ookla.R .Rhistory local_level_data.Rproj archive/ 2>/dev/null || true
```

- [ ] **Step 2: Verify data and structure**

Run: `ls data/ && echo '---' && ls archive/ | head`
Expected: `data/` still contains the 4 `.geojson` files; `archive/` contains the old guide files, `images/`, and `*.R`.

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "chore: reorganize repo; archive old guide artifacts and R scripts"
```

---

## Task 2: Python project scaffolding and dependencies

**Files:**
- Create: `pyproject.toml`
- Create: `pipeline/__init__.py` (empty package marker)
- Create: `.gitignore` additions

- [ ] **Step 1: Create `pyproject.toml`**

```toml
[project]
name = "local-level-data-pipeline"
version = "0.1.0"
description = "Reproducible pipeline for the local-level geographic data guide"
requires-python = ">=3.12"
dependencies = [
    "geopandas>=1.0",
    "pandas>=2.0",
    "pyarrow>=15",
    "shapely>=2.0",
    "pygris>=0.1.6",
    "census>=0.8.22",
    "us>=3.2",
    "contextily>=1.6",
    "mapclassify>=2.6",
    "matplotlib>=3.8",
    "sdc-redistribute>=0.1.1",
]

[dependency-groups]
dev = ["pytest>=8"]

[tool.pytest.ini_options]
markers = ["network: tests that hit live external services (deselect with -m 'not network')"]
```

- [ ] **Step 2: Create the package marker**

```bash
printf '"""Reproducible pipeline for the local-level data guide."""\n' > pipeline/__init__.py
```

- [ ] **Step 3: Append Python ignores to `.gitignore`**

Add these lines to `.gitignore`:

```
.venv/
__pycache__/
*.pyc
.pytest_cache/
ookla_data/
```

- [ ] **Step 4: Create the environment and install deps**

Run:
```bash
uv venv && uv sync
uv run python -c "import geopandas, pygris, census, sdc_redistribute; print('ok')"
```
Expected: `ok` (downloads may take a minute). If `sdc-redistribute` is not yet on the local index, install editable from the monorepo instead: `uv pip install -e /Users/ads7fg/git/social-data-commons/packages/sdc-redistribute`.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml pipeline/__init__.py .gitignore
git commit -m "build: add Python pipeline project and dependencies"
```

---

## Task 3: Configuration module

**Files:**
- Create: `pipeline/config.py`
- Test: `tests/test_config.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_config.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_config.py -v`
Expected: FAIL with `ModuleNotFoundError` / `AttributeError`.

- [ ] **Step 3: Write `pipeline/config.py`**

```python
"""Central configuration: geographies, CRS, source identifiers, paths."""
from pathlib import Path

# Arlington County, Virginia
STATE_FIPS = "51"
COUNTY_FIPS = "013"
ACS_YEAR = 2021          # 5-year ACS vintage used throughout
OOKLA_YEAR = 2023
OOKLA_QUARTER = 2

# Virginia State Plane North (US feet) — projected CRS for area math
TARGET_CRS = "EPSG:3968"

# ACS variables are EXTENSIVE COUNTS (never redistribute the median directly).
# Mean household income is derived later as agg_income / households.
ACS_VARS = {
    "agg_income": "B19025_001",   # Aggregate household income (dollars)
    "households": "B11001_001",   # Total households (count)
}

# Ookla open data S3 parquet path template
OOKLA_S3 = (
    "s3://ookla-open-data/parquet/performance/type=fixed/"
    "year={year}/quarter={quarter}/"
    "{year}-{month:02d}-01_performance_fixed_tiles.parquet"
)

# Paths
ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

# Source / output dataset paths
CIVIC_ASSOC = DATA / "va013_geo_arl_2021_civic_associations.geojson"
BLOCK_GROUPS = DATA / "va013_block_groups.geojson"          # produced by acquire_geographies
BLOCKS = DATA / "va013_geo_blocks.geojson"                  # existing
ACS_COUNTS = DATA / "va013_acs_income_counts.geojson"       # produced by acquire_acs
OOKLA_TILES = DATA / "ookla_tiles_arlington.geojson"        # existing/refreshable
CIVIC_INCOME = DATA / "civic_income.csv"                    # produced by redistribute_income
CIVIC_BROADBAND = DATA / "civic_broadband.csv"              # produced by redistribute_broadband
CIVIC_COMBINED = DATA / "civic_combined.geojson"            # produced by combine
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_config.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add pipeline/config.py tests/test_config.py
git commit -m "feat: add pipeline configuration module"
```

---

## Task 4: Source geometry normalization (`prep`)

`redistribute_direct` needs the source GeoJSON's id column named to match `source_id`. This module normalizes a source GeoDataFrame so its id column is `geoid` (string) and it is in `TARGET_CRS`.

**Files:**
- Create: `pipeline/prep.py`
- Test: `tests/test_prep.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_prep.py
import geopandas as gpd
from shapely.geometry import box
from pipeline.prep import normalize_source


def _gdf(id_col):
    return gpd.GeoDataFrame(
        {id_col: [101, 102]},
        geometry=[box(0, 0, 1, 1), box(1, 0, 2, 1)],
        crs="EPSG:4326",
    )


def test_renames_id_to_geoid_as_string():
    out = normalize_source(_gdf("GEOID"), id_col="GEOID", target_crs="EPSG:3857")
    assert "geoid" in out.columns
    assert out["geoid"].tolist() == ["101", "102"]


def test_reprojects_to_target_crs():
    out = normalize_source(_gdf("GEOID"), id_col="GEOID", target_crs="EPSG:3857")
    assert out.crs.to_string() == "EPSG:3857"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_prep.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Write `pipeline/prep.py`**

```python
"""Normalize source geometries for redistribution."""
from __future__ import annotations

import geopandas as gpd


def normalize_source(
    gdf: gpd.GeoDataFrame, id_col: str, target_crs: str
) -> gpd.GeoDataFrame:
    """Return a copy with the id column renamed to ``geoid`` (str) and reprojected.

    Parameters
    ----------
    gdf : GeoDataFrame with an identifier column ``id_col``.
    id_col : name of the source identifier column.
    target_crs : CRS to reproject to (e.g. ``"EPSG:3968"``).
    """
    out = gdf.copy()
    out = out.rename(columns={id_col: "geoid"})
    out["geoid"] = out["geoid"].astype(str)
    out = out.to_crs(target_crs)
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_prep.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add pipeline/prep.py tests/test_prep.py
git commit -m "feat: add source geometry normalization"
```

---

## Task 5: Acquire census geographies

Downloads Arlington block groups (the income source geography) and writes them with a `geoid` column. Network-dependent, so the logic is thin and the test is a network-marked smoke test.

**Files:**
- Create: `pipeline/acquire_geographies.py`
- Test: `tests/test_acquire_smoke.py` (shared smoke-test file; this task adds one test)

- [ ] **Step 1: Write `pipeline/acquire_geographies.py`**

```python
"""Acquire Arlington census block-group geometries via pygris."""
from __future__ import annotations

import geopandas as gpd
from pygris import block_groups

from pipeline import config


def fetch_block_groups() -> gpd.GeoDataFrame:
    """Download Arlington County (VA/013) block groups for the ACS vintage."""
    bg = block_groups(
        state=config.STATE_FIPS,
        county=config.COUNTY_FIPS,
        year=config.ACS_YEAR,
        cb=True,
    )
    return bg


def main() -> None:
    bg = fetch_block_groups()
    bg.to_file(config.BLOCK_GROUPS, driver="GeoJSON")
    print(f"Wrote {len(bg)} block groups → {config.BLOCK_GROUPS}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Add a network smoke test**

```python
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
```

- [ ] **Step 3: Run the smoke test against the live service**

Run: `uv run pytest tests/test_acquire_smoke.py::test_fetch_block_groups_returns_arlington -v -m network`
Expected: PASS (requires internet). Then materialize the file: `uv run python -m pipeline.acquire_geographies` → prints the block-group count and writes `data/va013_block_groups.geojson`.

- [ ] **Step 4: Commit**

```bash
git add pipeline/acquire_geographies.py tests/test_acquire_smoke.py data/va013_block_groups.geojson
git commit -m "feat: acquire Arlington block-group geometries"
```

---

## Task 6: Acquire ACS income counts

Fetches **aggregate household income** and **total households** (both counts) for Arlington block groups, joins to block-group geometry, and writes a GeoJSON. This replaces the existing *median*-income file (kept for comparison only).

**Files:**
- Create: `pipeline/acquire_acs.py`
- Test: `tests/test_acquire_smoke.py` (add one test)

- [ ] **Step 1: Write `pipeline/acquire_acs.py`**

```python
"""Acquire Arlington ACS aggregate income + household counts (block group)."""
from __future__ import annotations

import os

import geopandas as gpd
import pandas as pd
from census import Census

from pipeline import config
from pipeline.acquire_geographies import fetch_block_groups


def fetch_acs_counts(api_key: str | None = None) -> pd.DataFrame:
    """Return a DataFrame: GEOID, agg_income, households for Arlington block groups."""
    key = api_key or os.environ.get("CENSUS_API_KEY")
    c = Census(key, year=config.ACS_YEAR)
    rows = c.acs5.state_county_blockgroup(
        fields=("NAME", config.ACS_VARS["agg_income"], config.ACS_VARS["households"]),
        state_fips=config.STATE_FIPS,
        county_fips=config.COUNTY_FIPS,
        blockgroup=Census.ALL,
        tract=Census.ALL,
    )
    df = pd.DataFrame(rows)
    df["GEOID"] = df["state"] + df["county"] + df["tract"] + df["block group"]
    df = df.rename(
        columns={
            config.ACS_VARS["agg_income"]: "agg_income",
            config.ACS_VARS["households"]: "households",
        }
    )
    return df[["GEOID", "agg_income", "households"]]


def main() -> None:
    counts = fetch_acs_counts()
    bg = fetch_block_groups()[["GEOID", "geometry"]]
    merged = bg.merge(counts, on="GEOID", how="left")
    gdf = gpd.GeoDataFrame(merged, geometry="geometry", crs=bg.crs)
    gdf.to_file(config.ACS_COUNTS, driver="GeoJSON")
    print(f"Wrote {len(gdf)} block groups with income counts → {config.ACS_COUNTS}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Add a network smoke test**

```python
# append to tests/test_acquire_smoke.py
@pytest.mark.network
def test_fetch_acs_counts_has_count_columns():
    from pipeline.acquire_acs import fetch_acs_counts

    df = fetch_acs_counts()
    assert {"GEOID", "agg_income", "households"} <= set(df.columns)
    assert (df["households"].dropna() >= 0).all()
```

- [ ] **Step 3: Run the smoke test and materialize the file**

Run: `CENSUS_API_KEY=$CENSUS_API_KEY uv run pytest tests/test_acquire_smoke.py::test_fetch_acs_counts_has_count_columns -v -m network`
Expected: PASS (needs a free Census API key in `CENSUS_API_KEY`). Then: `uv run python -m pipeline.acquire_acs` writes `data/va013_acs_income_counts.geojson`.

- [ ] **Step 4: Commit**

```bash
git add pipeline/acquire_acs.py tests/test_acquire_smoke.py data/va013_acs_income_counts.geojson
git commit -m "feat: acquire ACS aggregate income and household counts"
```

---

## Task 7: Acquire Ookla tiles

Reads the Ookla fixed-broadband parquet for the configured quarter directly from S3, filters to the Arlington bounding box, and writes a GeoJSON. The existing `ookla_tiles_arlington.geojson` is refreshed by this.

**Files:**
- Create: `pipeline/acquire_ookla.py`
- Test: `tests/test_acquire_smoke.py` (add one test)

- [ ] **Step 1: Write `pipeline/acquire_ookla.py`**

```python
"""Acquire Ookla fixed-broadband tiles for Arlington from S3 open data."""
from __future__ import annotations

import geopandas as gpd
import pandas as pd
from shapely import wkt

from pipeline import config
from pipeline.acquire_geographies import fetch_block_groups


def _s3_path() -> str:
    month = config.OOKLA_QUARTER * 3 - 2  # Q1->01, Q2->04, Q3->07, Q4->10
    return config.OOKLA_S3.format(
        year=config.OOKLA_YEAR, quarter=config.OOKLA_QUARTER, month=month
    )


def fetch_ookla_tiles() -> gpd.GeoDataFrame:
    """Download and bbox-filter Ookla tiles to Arlington County."""
    df = pd.read_parquet(_s3_path(), storage_options={"anon": True})
    df["geometry"] = df["tile"].apply(wkt.loads)
    tiles = gpd.GeoDataFrame(df, geometry="geometry", crs="EPSG:4326")

    bbox = fetch_block_groups().to_crs("EPSG:4326").total_bounds  # minx,miny,maxx,maxy
    minx, miny, maxx, maxy = bbox
    return tiles.cx[minx:maxx, miny:maxy].copy()


def main() -> None:
    tiles = fetch_ookla_tiles()
    cols = ["quadkey", "avg_d_kbps", "avg_u_kbps", "avg_lat_ms", "tests", "devices", "geometry"]
    tiles[cols].to_file(config.OOKLA_TILES, driver="GeoJSON")
    print(f"Wrote {len(tiles)} Ookla tiles → {config.OOKLA_TILES}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Add a network smoke test**

```python
# append to tests/test_acquire_smoke.py
@pytest.mark.network
def test_fetch_ookla_tiles_has_speed_columns():
    from pipeline.acquire_ookla import fetch_ookla_tiles

    tiles = fetch_ookla_tiles()
    assert len(tiles) > 0
    assert {"quadkey", "avg_d_kbps", "tests"} <= set(tiles.columns)
```

- [ ] **Step 3: Run the smoke test and materialize the file**

Run: `uv run pytest tests/test_acquire_smoke.py::test_fetch_ookla_tiles_has_speed_columns -v -m network`
Expected: PASS (downloads a large parquet; may take a minute). Then: `uv run python -m pipeline.acquire_ookla` refreshes `data/ookla_tiles_arlington.geojson`.

- [ ] **Step 4: Commit**

```bash
git add pipeline/acquire_ookla.py tests/test_acquire_smoke.py data/ookla_tiles_arlington.geojson
git commit -m "feat: acquire Arlington Ookla broadband tiles from S3"
```

---

## Task 8: Redistribute income (block groups → civic associations)

Redistribute the two **counts** (`agg_income`, `households`) area-weighted onto civic associations using `redistribute_direct`, then derive **mean household income**. This drops the old block-disaggregation step entirely (area-weighting handles it) and never averages a median.

**Files:**
- Create: `pipeline/redistribute_income.py`
- Test: `tests/test_redistribute_income.py`

- [ ] **Step 1: Write the failing test (deterministic synthetic fixture)**

```python
# tests/test_redistribute_income.py
import geopandas as gpd
import pandas as pd
from shapely.geometry import box
from pipeline.redistribute_income import redistribute_income


def _write(tmp_path):
    # One source block group (2x2). Two target civic assocs split it 50/50.
    src = gpd.GeoDataFrame(
        {"geoid": ["BG1"]}, geometry=[box(0, 0, 2, 2)], crs="EPSG:3857"
    )
    tgt = gpd.GeoDataFrame(
        {"geoid": ["CA1", "CA2"]},
        geometry=[box(0, 0, 1, 2), box(1, 0, 2, 2)],
        crs="EPSG:3857",
    )
    src_path = tmp_path / "bg.geojson"
    tgt_path = tmp_path / "ca.geojson"
    src.to_file(src_path, driver="GeoJSON")
    tgt.to_file(tgt_path, driver="GeoJSON")
    return src_path, tgt_path


def test_mean_income_is_preserved_when_split_evenly(tmp_path):
    # BG1: $1,000,000 aggregate income across 10 households → mean $100,000.
    # Split 50/50 by area → each CA gets $500,000 / 5 households → mean $100,000.
    src_path, tgt_path = _write(tmp_path)
    counts = pd.DataFrame(
        {
            "geoid": ["BG1", "BG1"],
            "year": [2021, 2021],
            "measure": ["agg_income", "households"],
            "value": [1_000_000.0, 10.0],
        }
    )
    out = redistribute_income(counts, src_path, tgt_path)
    out = out.set_index("geoid").sort_index()
    assert out.loc["CA1", "households"] == 5.0
    assert out.loc["CA2", "households"] == 5.0
    assert out.loc["CA1", "mean_income"] == 100_000.0
    assert out.loc["CA2", "mean_income"] == 100_000.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_redistribute_income.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Write `pipeline/redistribute_income.py`**

```python
"""Redistribute ACS income counts to civic associations and derive mean income."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
from sdc_redistribute import redistribute_direct

from pipeline import config


def redistribute_income(
    counts_long: pd.DataFrame, source_geo: Path, target_geo: Path
) -> pd.DataFrame:
    """Return per-civic-association agg_income, households, and derived mean_income.

    ``counts_long`` is long format (geoid, year, measure, value) with measures
    ``agg_income`` and ``households``.
    """
    result = redistribute_direct(
        source_df=counts_long,
        source_geo=source_geo,
        target_geos={"civic_association": target_geo},
        count_cols=["agg_income", "households"],
        source_id="geoid",
    )
    # result is long with measures agg_income_direct / households_direct
    wide = result.pivot_table(
        index="geoid", columns="measure", values="value", aggfunc="first"
    ).reset_index()
    wide.columns.name = None
    wide = wide.rename(
        columns={"agg_income_direct": "agg_income", "households_direct": "households"}
    )
    # Mean household income is an INTENSIVE quantity derived from two counts.
    wide["mean_income"] = wide["agg_income"] / wide["households"].where(
        wide["households"] > 0
    )
    return wide[["geoid", "agg_income", "households", "mean_income"]]


def main() -> None:
    acs = __import__("geopandas").read_file(config.ACS_COUNTS)
    long = acs[["GEOID", "agg_income", "households"]].melt(
        id_vars="GEOID", var_name="measure", value_name="value"
    )
    long = long.rename(columns={"GEOID": "geoid"})
    long["year"] = config.ACS_YEAR
    out = redistribute_income(long, config.ACS_COUNTS, config.CIVIC_ASSOC)
    out.to_csv(config.CIVIC_INCOME, index=False)
    print(f"Wrote {len(out)} civic-association income rows → {config.CIVIC_INCOME}")


if __name__ == "__main__":
    main()
```

Note: `redistribute_direct` reprojects geographic CRS to EPSG:3857 internally; the synthetic fixture is already projected so areas are exact.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_redistribute_income.py -v`
Expected: PASS (1 passed).

- [ ] **Step 5: Commit**

```bash
git add pipeline/redistribute_income.py tests/test_redistribute_income.py
git commit -m "feat: redistribute income counts and derive mean income"
```

---

## Task 9: Redistribute broadband (Ookla tiles → civic associations)

Treat **tests** as the extensive weight. To get a test-weighted **mean download speed**, redistribute `tests` and the product `d_product = avg_d_kbps * tests` as counts, then derive `download_mbps = (d_product / tests) / 1000`. Same for upload. (We derive the rate ourselves rather than via `pct_specs`, which is hard-coded to ×100 for percentages.)

**Files:**
- Create: `pipeline/redistribute_broadband.py`
- Test: `tests/test_redistribute_broadband.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_redistribute_broadband.py
import geopandas as gpd
import pandas as pd
from shapely.geometry import box
from pipeline.redistribute_broadband import redistribute_broadband


def _write(tmp_path):
    src = gpd.GeoDataFrame(
        {"geoid": ["T1"]}, geometry=[box(0, 0, 2, 2)], crs="EPSG:3857"
    )
    tgt = gpd.GeoDataFrame(
        {"geoid": ["CA1", "CA2"]},
        geometry=[box(0, 0, 1, 2), box(1, 0, 2, 2)],
        crs="EPSG:3857",
    )
    src_path = tmp_path / "tiles.geojson"
    tgt_path = tmp_path / "ca.geojson"
    src.to_file(src_path, driver="GeoJSON")
    tgt.to_file(tgt_path, driver="GeoJSON")
    return src_path, tgt_path


def test_download_speed_derived_from_count_weighting(tmp_path):
    # One tile, 200,000 kbps, 10 tests. Split 50/50 → each CA: 5 tests,
    # d_product 1,000,000 → mean 200,000 kbps → 200 Mbps.
    src_path, tgt_path = _write(tmp_path)
    long = pd.DataFrame(
        {
            "geoid": ["T1", "T1", "T1"],
            "year": [2023, 2023, 2023],
            "measure": ["tests", "d_product", "u_product"],
            "value": [10.0, 2_000_000.0, 500_000.0],
        }
    )
    out = redistribute_broadband(long, src_path, tgt_path).set_index("geoid").sort_index()
    assert out.loc["CA1", "tests"] == 5.0
    assert round(out.loc["CA1", "download_mbps"], 3) == 200.0
    assert round(out.loc["CA1", "upload_mbps"], 3) == 50.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_redistribute_broadband.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Write `pipeline/redistribute_broadband.py`**

```python
"""Redistribute Ookla broadband to civic associations; derive mean speeds."""
from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import pandas as pd
from sdc_redistribute import redistribute_direct

from pipeline import config

MIN_TESTS = 5  # statistical-reliability filter on source tiles


def redistribute_broadband(
    counts_long: pd.DataFrame, source_geo: Path, target_geo: Path
) -> pd.DataFrame:
    """Return per-civic-association tests and derived download/upload Mbps."""
    result = redistribute_direct(
        source_df=counts_long,
        source_geo=source_geo,
        target_geos={"civic_association": target_geo},
        count_cols=["tests", "d_product", "u_product"],
        source_id="geoid",
    )
    wide = result.pivot_table(
        index="geoid", columns="measure", values="value", aggfunc="first"
    ).reset_index()
    wide.columns.name = None
    wide = wide.rename(
        columns={
            "tests_direct": "tests",
            "d_product_direct": "d_product",
            "u_product_direct": "u_product",
        }
    )
    valid = wide["tests"] > 0
    wide["download_mbps"] = (wide["d_product"] / wide["tests"].where(valid)) / 1000
    wide["upload_mbps"] = (wide["u_product"] / wide["tests"].where(valid)) / 1000
    return wide[["geoid", "tests", "download_mbps", "upload_mbps"]]


def build_counts_long(tiles: gpd.GeoDataFrame) -> pd.DataFrame:
    """Build the long-format count frame from raw Ookla tiles."""
    t = tiles[tiles["tests"] >= MIN_TESTS].copy()
    t["d_product"] = t["avg_d_kbps"] * t["tests"]
    t["u_product"] = t["avg_u_kbps"] * t["tests"]
    long = t[["quadkey", "tests", "d_product", "u_product"]].melt(
        id_vars="quadkey", var_name="measure", value_name="value"
    )
    long = long.rename(columns={"quadkey": "geoid"})
    long["year"] = config.OOKLA_YEAR
    return long


def main() -> None:
    tiles = gpd.read_file(config.OOKLA_TILES)
    tiles["geoid"] = tiles["quadkey"].astype(str)
    long = build_counts_long(tiles)
    # Write a geoid-keyed source file for redistribute_direct
    src = tiles[["geoid", "geometry"]].copy()
    src_path = config.DATA / "_ookla_src.geojson"
    src.to_file(src_path, driver="GeoJSON")
    out = redistribute_broadband(long, src_path, config.CIVIC_ASSOC)
    out.to_csv(config.CIVIC_BROADBAND, index=False)
    src_path.unlink(missing_ok=True)
    print(f"Wrote {len(out)} civic-association broadband rows → {config.CIVIC_BROADBAND}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_redistribute_broadband.py -v`
Expected: PASS (1 passed).

- [ ] **Step 5: Commit**

```bash
git add pipeline/redistribute_broadband.py tests/test_redistribute_broadband.py
git commit -m "feat: redistribute broadband and derive count-weighted speeds"
```

---

## Task 10: Combine and derive metrics

Join income + broadband per civic association onto the civic-association geometry, and compute the derived metrics the guide visualizes: **income-to-speed ratio** and **bivariate tercile classes**.

**Files:**
- Create: `pipeline/combine.py`
- Test: `tests/test_combine.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_combine.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_combine.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Write `pipeline/combine.py`**

```python
"""Combine income + broadband and compute derived policy metrics."""
from __future__ import annotations

import geopandas as gpd
import pandas as pd

from pipeline import config


def _tercile(series: pd.Series) -> pd.Series:
    """Return 1/2/3 tercile labels by rank (robust to ties and NaN)."""
    ranks = series.rank(method="first")
    return pd.qcut(ranks, 3, labels=[1, 2, 3]).astype("Int64")


def add_derived_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """Add income_speed_ratio and bivariate_class (income-speed terciles)."""
    out = df.copy()
    out["income_speed_ratio"] = out["mean_income"] / out["download_mbps"].where(
        out["download_mbps"] > 0
    )
    inc = _tercile(out["mean_income"])
    spd = _tercile(out["download_mbps"])
    out["bivariate_class"] = inc.astype(str) + "-" + spd.astype(str)
    return out


def main() -> None:
    civ = gpd.read_file(config.CIVIC_ASSOC)[["geoid", "region_name", "geometry"]]
    income = pd.read_csv(config.CIVIC_INCOME, dtype={"geoid": str})
    broadband = pd.read_csv(config.CIVIC_BROADBAND, dtype={"geoid": str})
    merged = civ.merge(income, on="geoid", how="left").merge(
        broadband, on="geoid", how="left"
    )
    merged = add_derived_metrics(merged)
    gdf = gpd.GeoDataFrame(merged, geometry="geometry", crs=civ.crs)
    gdf.to_file(config.CIVIC_COMBINED, driver="GeoJSON")
    print(f"Wrote {len(gdf)} combined civic-association rows → {config.CIVIC_COMBINED}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_combine.py -v`
Expected: PASS (1 passed).

- [ ] **Step 5: Commit**

```bash
git add pipeline/combine.py tests/test_combine.py
git commit -m "feat: combine datasets and derive ratio + bivariate metrics"
```

---

## Task 11: Validate outputs

Assert the integrity properties the guide will claim: household totals are preserved within tolerance after redistribution, and speeds/incomes fall in sane ranges.

**Files:**
- Create: `pipeline/validate.py`
- Test: `tests/test_validate.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_validate.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_validate.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Write `pipeline/validate.py`**

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_validate.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add pipeline/validate.py tests/test_validate.py
git commit -m "feat: add output validation checks"
```

---

## Task 12: End-to-end runner and reproduction README

Wire the modules into one ordered runner and document reproduction. This is the command the guide's companion-repo section will point readers to.

**Files:**
- Create: `pipeline/run.py`
- Create: `README.md` (rewrite)

- [ ] **Step 1: Write `pipeline/run.py`**

```python
"""Run the full pipeline end to end (acquisition → outputs → validation)."""
from __future__ import annotations

from pipeline import (
    acquire_acs,
    acquire_geographies,
    acquire_ookla,
    combine,
    redistribute_broadband,
    redistribute_income,
    validate,
)


def main() -> None:
    acquire_geographies.main()
    acquire_acs.main()
    acquire_ookla.main()
    redistribute_income.main()
    redistribute_broadband.main()
    combine.main()
    validate.main()
    print("Pipeline complete.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Rewrite `README.md`**

```markdown
# Local-Level Data Guide — Pipeline

Reproducible Python pipeline behind the illustrated guide to creating
sub-county geographic datasets (Arlington County: broadband × income →
civic associations).

## Setup

```bash
uv venv && uv sync
export CENSUS_API_KEY=your_key   # free: https://api.census.gov/data/key_signup.html
```

## Run

```bash
uv run python -m pipeline.run
```

Outputs land in `data/`:
- `civic_income.csv`, `civic_broadband.csv` — redistributed measures
- `civic_combined.geojson` — joined + derived metrics (ratio, bivariate class)

## Method

Counts (aggregate income, households, broadband tests) are redistributed
area-weighted with `sdc-redistribute`; intensive rates (mean income, mean
speed) are derived from count ratios. See `docs/superpowers/specs/`.

## Tests

```bash
uv run pytest -m "not network"   # fast, deterministic
uv run pytest -m network         # live Census/Ookla acquisition
```
```

- [ ] **Step 3: Run the full deterministic test suite**

Run: `uv run pytest -m "not network" -v`
Expected: PASS (all unit tests across config/prep/income/broadband/combine/validate).

- [ ] **Step 4: Run the full pipeline against live data**

Run: `uv run python -m pipeline.run`
Expected: prints progress for each stage and `Pipeline complete.`; `data/civic_combined.geojson` exists with 62 civic associations.

- [ ] **Step 5: Commit**

```bash
git add pipeline/run.py README.md data/civic_income.csv data/civic_broadband.csv data/civic_combined.geojson
git commit -m "feat: add end-to-end pipeline runner and reproduction README"
```

---

## Self-Review

**Spec coverage (§ refers to the design spec):**
- §5 deliverable "reproducible Python pipeline" → Tasks 2–12. ✓
- §5 "four GeoJSONs retained + acquisition scripts" → Task 1 keeps `data/`; Tasks 5–7 add acquisition. ✓
- §8 methodology correction (counts → derived ratios; drop block disaggregation; mean not median) → Tasks 8–9, encoded in tests. ✓
- §8 "regenerate numbers from pipeline" → Task 12 runner produces `civic_combined.geojson`. ✓
- §10 Python stack (`pygris`, `census`, S3 Ookla, `sdc-redistribute`) → Task 2 deps; Tasks 5–9. ✓
- §11 repo layout (`pipeline/`, `data/`, `archive/`) → Task 1. ✓
- §14 success "reproduce via documented steps" → Task 12 README. ✓
- Out of scope here (correctly deferred to Plans 2–3): figure generation, Quarto theme/document, flowcharts. Noted, not a gap.

**Placeholder scan:** No TBD/TODO/"handle edge cases"; every code step shows complete code. ✓

**Type/name consistency:** `geoid` id convention is uniform (`prep.normalize_source`, both redistribute modules, `combine`). Output column names (`agg_income`, `households`, `mean_income`, `tests`, `download_mbps`, `upload_mbps`, `income_speed_ratio`, `bivariate_class`) are consistent across Tasks 8→10 and the config path constants. `redistribute_direct` is called with the real signature confirmed from source (`source_df`, `source_geo`, `target_geos`, `count_cols`, `source_id`). ✓

**Known live-data caveats (not plan defects):** ACS aggregate-income / household tables must exist at block-group level for the 2021 5-year vintage (they do: B19025, B11001); `redistribute_direct`'s area-only weighting still assumes uniform distribution within block groups — the guide (Plan 3) states this limitation explicitly per spec §8.
