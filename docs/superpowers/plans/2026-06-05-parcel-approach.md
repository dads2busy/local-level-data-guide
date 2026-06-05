# Parcel-Based Redistribution (Second Approach) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a parcel-based dasymetric redistribution of income (unit-weighted, via the existing `redistribute_parcels`), compare it against the area-weighted result, generate a strong parcel figure set, and add a guide chapter — all reproducible from the pipeline.

**Architecture:** New pipeline modules acquire Arlington MHUD parcels, explode them by `Total_Units` into unit-points, redistribute block-group income through them to civic associations, and compare to the existing area-weighted income. New figures and a new Quarto chapter present the comparison. Pure logic (explosion, redistribution wiring, comparison arithmetic) is TDD'd with synthetic fixtures; acquisition/figures get smoke tests; the chapter and figures get a controller visual review.

**Tech Stack:** Python 3.12, `geopandas`, `pandas`, `sdc-redistribute` (existing `redistribute_parcels`), `matplotlib`, Quarto. Builds on the merged pipeline + guide on `main`.

---

## Verified facts this plan builds on

- MHUD FeatureServer `…/Open_Data/od_MHUD_Polygons/FeatureServer/0`: 34,340 polygons; fields `Total_Units` (int), `Unit_Type` (`SFD` 27,455 / `SFA` 6,210 / `MULTI` 675); supports `f=geojson` + `resultOffset`/`resultRecordCount` pagination; `outSR=4326`.
- `redistribute_parcels(source_df, parcel_centroids, source_geo, target_geos, count_cols, pct_specs=None, *, source_id="geoid", ...)`: assigns each parcel point to its source polygon (`within`), splits each source unit's counts **evenly across its points**, re-aggregates points within each target. Returns long format with measures suffixed `_parcels`. Reprojects geographic input to EPSG:3857 internally.
- `data/va013_acs_income_counts.geojson` (GEOID, agg_income, households), `data/civic_income.csv` (area-weighted: geoid, agg_income, households, mean_income), and `data/va013_geo_arl_2021_civic_associations.geojson` (geoid, region_name) already exist on `main`.
- `pipeline/maps.py` provides `to_plot_crs`, `choropleth`, `scatter`; `pipeline/style.py` provides `PALETTE`, `SEQUENTIAL`, `DIVERGING`, `MAP_CRS`, `apply_style`, `add_north_arrow`, `add_scale_bar`.

## File structure

```
pipeline/
  acquire_parcels.py             # MHUD FeatureServer (paged geojson) → parcel centroids
  redistribute_income_parcels.py # explode by units → redistribute_parcels → derive mean income
  compare_methods.py             # join area vs parcel income → diff/pct_diff + validation
  maps.py                        # + points_map helper
  figures.py                     # + 4 parcel figure functions
  build_figures.py               # EXPECTED += 4 figures
  run.py                         # + parcel acquisition/redistribution/compare steps
data/
  va013_parcels.geojson          # parcel centroids (Total_Units, Unit_Type)
  civic_income_parcels.csv       # parcel-weighted income per association
  civic_income_comparison.geojson# area vs parcel + diff
guide/
  parcel-approach.qmd            # new chapter
  _quarto.yml                    # chapters += parcel-approach.qmd (after 05-results)
scripts/build_code_appendix.py   # MODULES += acquire_parcels, redistribute_income_parcels, compare_methods
figures/  map_parcels.png  map_income_parcels.png  map_income_diff.png  scatter_area_vs_parcel.png
tests/  test_redistribute_income_parcels.py  test_compare_methods.py  (+ smoke additions)
```

---

## Task 1: Acquire MHUD parcels

**Files:** Create `pipeline/acquire_parcels.py`; add tests to `tests/test_acquire_smoke.py` and a deterministic test in `tests/test_acquire_parcels.py`.

- [ ] **Step 1: Write the deterministic cleaning-helper test**

```python
# tests/test_acquire_parcels.py
import geopandas as gpd
from shapely.geometry import box
from pipeline.acquire_parcels import to_centroids


def test_to_centroids_keeps_fields_and_makes_points():
    polys = gpd.GeoDataFrame(
        {"Total_Units": [1, 200], "Unit_Type": ["SFD", "MULTI"]},
        geometry=[box(0, 0, 1, 1), box(2, 2, 4, 4)],
        crs="EPSG:4326",
    )
    pts = to_centroids(polys)
    assert (pts.geometry.geom_type == "Point").all()
    assert list(pts.columns) == ["Total_Units", "Unit_Type", "geometry"]
    assert pts.crs.to_epsg() == 4326
```

- [ ] **Step 2: Run it (fails — no module)**

Run: `uv run pytest tests/test_acquire_parcels.py -v` → FAIL (ModuleNotFoundError).

- [ ] **Step 3: Write `pipeline/acquire_parcels.py`**

```python
"""Acquire Arlington MHUD parcel polygons and reduce them to unit-bearing centroids."""
from __future__ import annotations

import json
import urllib.parse
import urllib.request

import geopandas as gpd
import pandas as pd

from pipeline import config

LAYER = (
    "https://arlgis.arlingtonva.us/arcgis/rest/services/Open_Data/"
    "od_MHUD_Polygons/FeatureServer/0/query"
)
PAGE = 2000


def _fetch_page(offset: int) -> gpd.GeoDataFrame | None:
    params = {
        "where": "1=1",
        "outFields": "Total_Units,Unit_Type",
        "outSR": "4326",
        "resultOffset": str(offset),
        "resultRecordCount": str(PAGE),
        "f": "geojson",
    }
    url = LAYER + "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=60) as resp:  # noqa: S310
        data = json.load(resp)
    feats = data.get("features", [])
    if not feats:
        return None
    return gpd.GeoDataFrame.from_features(feats, crs="EPSG:4326")


def fetch_parcels() -> gpd.GeoDataFrame:
    """Page through the MHUD FeatureServer and return all parcel polygons."""
    parts: list[gpd.GeoDataFrame] = []
    offset = 0
    while True:
        page = _fetch_page(offset)
        if page is None or len(page) == 0:
            break
        parts.append(page)
        if len(page) < PAGE:
            break
        offset += PAGE
    gdf = gpd.GeoDataFrame(pd.concat(parts, ignore_index=True), crs="EPSG:4326")
    return gdf


def to_centroids(polys: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Reduce parcel polygons to centroids, keeping Total_Units and Unit_Type."""
    cent = polys.copy()
    # representative_point() is guaranteed inside the polygon (unlike centroid)
    cent["geometry"] = cent.geometry.representative_point()
    return cent[["Total_Units", "Unit_Type", "geometry"]]


def main() -> None:
    polys = fetch_parcels()
    pts = to_centroids(polys)
    pts.to_file(config.PARCELS, driver="GeoJSON")
    print(f"Wrote {len(pts)} parcel centroids → {config.PARCELS}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Add `PARCELS` (and parcel output paths) to `pipeline/config.py`**

Add after the existing dataset paths:

```python
PARCELS = DATA / "va013_parcels.geojson"                   # produced by acquire_parcels
CIVIC_INCOME_PARCELS = DATA / "civic_income_parcels.csv"   # produced by redistribute_income_parcels
CIVIC_INCOME_COMPARISON = DATA / "civic_income_comparison.geojson"  # produced by compare_methods
```

- [ ] **Step 5: Run the deterministic test**

Run: `uv run pytest tests/test_acquire_parcels.py -v` → PASS (1).

- [ ] **Step 6: Add a network smoke test**

```python
# append to tests/test_acquire_smoke.py
@pytest.mark.network
def test_fetch_parcels_has_units_and_type():
    from pipeline.acquire_parcels import fetch_parcels

    gdf = fetch_parcels()
    assert len(gdf) > 30000
    assert {"Total_Units", "Unit_Type"} <= set(gdf.columns)
    assert gdf["Total_Units"].sum() > 100000  # exploded units ≈ household count
```

- [ ] **Step 7: Run the smoke test + materialize**

Run: `uv run pytest tests/test_acquire_smoke.py::test_fetch_parcels_has_units_and_type -v -m network` → PASS (paged download; may take ~30–60s). Then `uv run python -m pipeline.acquire_parcels` writes `data/va013_parcels.geojson` (~34,340 points). Report the count and total `Total_Units`.

- [ ] **Step 8: Commit**

```bash
git add pipeline/acquire_parcels.py pipeline/config.py tests/test_acquire_parcels.py tests/test_acquire_smoke.py data/va013_parcels.geojson
git commit -m "feat: acquire Arlington MHUD parcel centroids"
```

---

## Task 2: Unit-weighted parcel redistribution of income

**Files:** Create `pipeline/redistribute_income_parcels.py`, `tests/test_redistribute_income_parcels.py`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_redistribute_income_parcels.py
import geopandas as gpd
import pandas as pd
from shapely.geometry import box, Point
from pipeline.redistribute_income_parcels import explode_by_units, redistribute_income_parcels


def test_explode_by_units_replicates_and_drops_nonpositive():
    parcels = gpd.GeoDataFrame(
        {"Total_Units": [1, 3, 0]},
        geometry=[Point(0, 0), Point(1, 1), Point(2, 2)],
        crs="EPSG:3857",
    )
    out = explode_by_units(parcels)
    assert len(out) == 4              # 1 + 3, the 0-unit parcel dropped
    assert (out.geometry == Point(1, 1)).sum() == 3


def _write(tmp_path):
    src = gpd.GeoDataFrame({"geoid": ["BG1"]}, geometry=[box(0, 0, 10, 10)], crs="EPSG:3857")
    tgt = gpd.GeoDataFrame(
        {"geoid": ["CA1", "CA2"]},
        geometry=[box(0, 0, 5, 10), box(5, 0, 10, 10)], crs="EPSG:3857",
    )
    sp = tmp_path / "bg.geojson"; tp = tmp_path / "ca.geojson"
    src.to_file(sp, driver="GeoJSON"); tgt.to_file(tp, driver="GeoJSON")
    return sp, tp


def test_parcel_redistribution_splits_by_unit_points(tmp_path):
    # BG1: $1,000,000 income / 10 households spread over 10 unit-points:
    # 6 points in CA1 (left), 4 in CA2 (right). Each point => 100,000 income, 1 hh.
    sp, tp = _write(tmp_path)
    pts = [Point(x, 5) for x in (1, 1.5, 2, 2.5, 3, 3.5)] + [Point(x, 5) for x in (6, 7, 8, 9)]
    parcels = gpd.GeoDataFrame({"Total_Units": [1] * 10}, geometry=pts, crs="EPSG:3857")
    counts = pd.DataFrame({
        "geoid": ["BG1", "BG1"], "year": [2021, 2021],
        "measure": ["agg_income", "households"], "value": [1_000_000.0, 10.0],
    })
    out = redistribute_income_parcels(counts, parcels, sp, tp).set_index("geoid").sort_index()
    assert out.loc["CA1", "households"] == 6.0
    assert out.loc["CA2", "households"] == 4.0
    assert round(out.loc["CA1", "mean_income"], 2) == 100_000.0
```

- [ ] **Step 2: Run (fails — no module)**

Run: `uv run pytest tests/test_redistribute_income_parcels.py -v` → FAIL.

- [ ] **Step 3: Write `pipeline/redistribute_income_parcels.py`**

```python
"""Redistribute income through unit-weighted parcels (dasymetric), derive mean income."""
from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import pandas as pd
from sdc_redistribute import redistribute_parcels

from pipeline import config


def explode_by_units(parcels: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Replicate each parcel into Total_Units identical points; drop units <= 0."""
    p = parcels[parcels["Total_Units"] > 0].copy()
    reps = p["Total_Units"].astype(int).to_numpy()
    out = p.loc[p.index.repeat(reps)].reset_index(drop=True)
    return out


def redistribute_income_parcels(
    counts_long: pd.DataFrame,
    parcels: gpd.GeoDataFrame,
    source_geo: Path,
    target_geo: Path,
) -> pd.DataFrame:
    """Return per-civic-association agg_income, households, derived mean_income."""
    points = explode_by_units(parcels)
    result = redistribute_parcels(
        source_df=counts_long,
        parcel_centroids=points,
        source_geo=source_geo,
        target_geos={"civic_association": target_geo},
        count_cols=["agg_income", "households"],
        source_id="geoid",
    )
    wide = result.pivot_table(
        index="geoid", columns="measure", values="value", aggfunc="first"
    ).reset_index()
    wide.columns.name = None
    wide = wide.rename(
        columns={"agg_income_parcels": "agg_income", "households_parcels": "households"}
    )
    wide["mean_income"] = wide["agg_income"] / wide["households"].where(
        wide["households"] > 0
    )
    return wide[["geoid", "agg_income", "households", "mean_income"]]


def main() -> None:
    parcels = gpd.read_file(config.PARCELS)
    bg = gpd.read_file(config.ACS_COUNTS).rename(columns={"GEOID": "geoid"})
    long = bg[["geoid", "agg_income", "households"]].melt(
        id_vars="geoid", var_name="measure", value_name="value"
    )
    long["year"] = config.ACS_YEAR

    src_path = config.DATA / "_acs_src_parcels.geojson"
    bg[["geoid", "geometry"]].to_file(src_path, driver="GeoJSON")
    out = redistribute_income_parcels(long, parcels, src_path, config.CIVIC_ASSOC)
    src_path.unlink(missing_ok=True)

    out.to_csv(config.CIVIC_INCOME_PARCELS, index=False)
    print(f"Wrote {len(out)} parcel-weighted income rows → {config.CIVIC_INCOME_PARCELS}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests (pass)**

Run: `uv run pytest tests/test_redistribute_income_parcels.py -v` → PASS (2).

- [ ] **Step 5: Real-data smoke run**

Run: `uv run python -m pipeline.redistribute_income_parcels` → writes `data/civic_income_parcels.csv` (62 rows). Report row count, the `mean_income` range, and how many associations are NaN (parcels-free). Commit the materialized CSV if reasonable.

- [ ] **Step 6: Commit**

```bash
git add pipeline/redistribute_income_parcels.py tests/test_redistribute_income_parcels.py data/civic_income_parcels.csv
git commit -m "feat: unit-weighted parcel redistribution of income"
```

---

## Task 3: Compare area vs parcel

**Files:** Create `pipeline/compare_methods.py`, `tests/test_compare_methods.py`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_compare_methods.py
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
```

- [ ] **Step 2: Run (fails)**

Run: `uv run pytest tests/test_compare_methods.py -v` → FAIL.

- [ ] **Step 3: Write `pipeline/compare_methods.py`**

```python
"""Compare area-weighted vs parcel-weighted income per civic association."""
from __future__ import annotations

import geopandas as gpd
import pandas as pd

from pipeline import config


def compare_income(area: pd.DataFrame, parcel: pd.DataFrame) -> pd.DataFrame:
    """Join the two methods' mean income; add diff (parcel - area) and pct_diff."""
    a = area[["geoid", "mean_income"]].rename(columns={"mean_income": "mean_income_area"})
    p = parcel[["geoid", "mean_income"]].rename(columns={"mean_income": "mean_income_parcel"})
    out = a.merge(p, on="geoid", how="outer")
    out["diff"] = out["mean_income_parcel"] - out["mean_income_area"]
    out["pct_diff"] = 100 * out["diff"] / out["mean_income_area"].where(
        out["mean_income_area"] > 0
    )
    return out


def main() -> None:
    civ = gpd.read_file(config.CIVIC_ASSOC)[["geoid", "region_name", "geometry"]]
    area = pd.read_csv(config.CIVIC_INCOME, dtype={"geoid": str})
    parcel = pd.read_csv(config.CIVIC_INCOME_PARCELS, dtype={"geoid": str})
    cmp = compare_income(area, parcel)
    gdf = civ.merge(cmp, on="geoid", how="left")
    gdf = gpd.GeoDataFrame(gdf, geometry="geometry", crs=civ.crs)

    # Honest accounting: report parcel-method household total vs ACS source.
    acs = gpd.read_file(config.ACS_COUNTS)
    src_hh = float(acs["households"].sum())
    parcel_hh = float(pd.read_csv(config.CIVIC_INCOME_PARCELS)["households"].sum())
    pct = 100 * (parcel_hh - src_hh) / src_hh if src_hh else 0.0
    print(f"Household totals — ACS source: {src_hh:,.0f}; parcel method: {parcel_hh:,.0f} ({pct:+.1f}%)")

    gdf.to_file(config.CIVIC_INCOME_COMPARISON, driver="GeoJSON")
    print(f"Wrote {len(gdf)} comparison rows → {config.CIVIC_INCOME_COMPARISON}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test (pass)**

Run: `uv run pytest tests/test_compare_methods.py -v` → PASS.

- [ ] **Step 5: Real-data run**

Run: `uv run python -m pipeline.compare_methods`. Report the household-total line (shortfall %), the diff range, and the 3 associations that gain most and lose most under parcels (expect dense multifamily corridors to gain, large low-density associations to drop). Commit `data/civic_income_comparison.geojson`.

- [ ] **Step 6: Commit**

```bash
git add pipeline/compare_methods.py tests/test_compare_methods.py data/civic_income_comparison.geojson
git commit -m "feat: compare area vs parcel income with totals accounting"
```

---

## Task 4: Parcel figures

**Files:** Modify `pipeline/maps.py` (add `points_map`), `pipeline/figures.py` (4 figures + ALL_FIGURES), `pipeline/build_figures.py` (EXPECTED); add smoke params.

- [ ] **Step 1: Add `points_map` to `pipeline/maps.py`**

```python
def points_map(
    gdf: gpd.GeoDataFrame,
    *,
    size_col: str,
    cat_col: str,
    title: str,
    ax=None,
):
    """Return a Figure of points sized by ``size_col`` and coloured by ``cat_col``."""
    g = to_plot_crs(gdf)
    if ax is None:
        fig, ax = plt.subplots(figsize=(7, 8))
    else:
        fig = ax.figure
    cats = list(g[cat_col].unique())
    colors = {cats[0]: style.PALETTE["blue"]}
    for c in cats[1:]:
        colors[c] = style.PALETTE["amber"]
    # draw the smaller-count category last so it sits on top
    order = sorted(cats, key=lambda c: -(g[cat_col] == c).sum())
    for c in order:
        sub = g[g[cat_col] == c]
        ax.scatter(
            sub.geometry.x, sub.geometry.y,
            s=2 + (sub[size_col].clip(lower=1) ** 0.5),
            c=colors[c], label=str(c), alpha=0.5, edgecolor="none",
        )
    ax.set_aspect("equal")
    ax.set_title(title)
    ax.set_axis_off()
    ax.legend(loc="lower right", frameon=True, markerscale=2)
    style.add_north_arrow(ax)
    style.add_scale_bar(ax)
    return fig
```

- [ ] **Step 2: Add the 4 figure functions to `pipeline/figures.py`**

Add these functions and append them to `ALL_FIGURES`:

```python
def fig_parcels() -> Path:
    parcels = gpd.read_file(config.PARCELS)
    parcels["category"] = parcels["Unit_Type"].where(
        parcels["Unit_Type"] == "MULTI", "Single-family"
    ).replace({"MULTI": "Multifamily"})
    fig = maps.points_map(
        parcels, size_col="Total_Units", cat_col="category",
        title="Arlington Housing Units by Parcel (size = units)",
    )
    return _save(fig, "map_parcels.png")


def fig_income_parcels() -> Path:
    cmp = gpd.read_file(config.CIVIC_INCOME_COMPARISON)
    fig = maps.choropleth(
        cmp, "mean_income_parcel",
        title="Mean Household Income — Parcel Method",
        legend_label="Mean income ($)", fmt="${:,.0f}",
    )
    return _save(fig, "map_income_parcels.png")


def fig_income_diff() -> Path:
    cmp = gpd.read_file(config.CIVIC_INCOME_COMPARISON)
    fig = maps.choropleth(
        cmp, "diff",
        title="Income Difference: Parcel − Area Method",
        legend_label="$ difference", cmap=style.DIVERGING, fmt="${:,.0f}",
    )
    return _save(fig, "map_income_diff.png")


def fig_scatter_area_vs_parcel() -> Path:
    cmp = gpd.read_file(config.CIVIC_INCOME_COMPARISON)
    fig = maps.scatter(
        cmp, "mean_income_area", "mean_income_parcel",
        title="Area vs. Parcel Mean Income",
        xlabel="Area-weighted ($)", ylabel="Parcel-weighted ($)",
    )
    ax = fig.axes[0]
    lo = float(min(cmp["mean_income_area"].min(), cmp["mean_income_parcel"].min()))
    hi = float(max(cmp["mean_income_area"].max(), cmp["mean_income_parcel"].max()))
    ax.plot([lo, hi], [lo, hi], color=style.PALETTE["gray"], ls="--", lw=1)
    return _save(fig, "scatter_area_vs_parcel.png")
```

And update:
```python
ALL_FIGURES = [
    fig_transformation_3panel,
    fig_locator,
    fig_ookla_tiles,
    fig_income,
    fig_speed,
    fig_ratio,
    fig_bivariate,
    fig_scatter,
    fig_parcels,
    fig_income_parcels,
    fig_income_diff,
    fig_scatter_area_vs_parcel,
]
```

- [ ] **Step 3: Extend the figures smoke test (already parametrized over `ALL_FIGURES`)**

No change needed — `tests/test_figures_smoke.py` parametrizes over `figures.ALL_FIGURES`, so the 4 new figures are covered automatically. Run: `uv run pytest tests/test_figures_smoke.py -v` → 12 pass (needs `data/va013_parcels.geojson` + `data/civic_income_comparison.geojson` from Tasks 1–3).

- [ ] **Step 4: Add the 4 figures to `pipeline/build_figures.py` `EXPECTED`**

Insert before the diagrams entries:
```python
    "figures/map_parcels.png",
    "figures/map_income_parcels.png",
    "figures/map_income_diff.png",
    "figures/scatter_area_vs_parcel.png",
```

- [ ] **Step 5: Generate + controller visual review**

Run: `uv run python -m pipeline.figures`. Then the controller opens the 4 PNGs and confirms: `map_parcels` shows dense multifamily points (amber, large) over single-family (blue, small) and reads clearly; the parcel income choropleth matches the income palette; the diff map is centered/legible on the diverging palette; the scatter shows points around the 1:1 line. Report any over-plotting or legend issues; fix and regenerate if needed.

- [ ] **Step 6: Commit**

```bash
git add pipeline/maps.py pipeline/figures.py pipeline/build_figures.py figures/map_parcels.png figures/map_income_parcels.png figures/map_income_diff.png figures/scatter_area_vs_parcel.png
git commit -m "feat: add parcel figures (parcels, parcel income, difference, scatter)"
```

---

## Task 5: Guide chapter

**Files:** Create `guide/parcel-approach.qmd`; modify `guide/_quarto.yml`, `scripts/build_code_appendix.py`.

- [ ] **Step 1: Write `guide/parcel-approach.qmd`** (heading `# A Second Approach: Parcel-Based Redistribution {#sec-parcels}`), ~700–900 words. Content brief:
  - Motivate dasymetric redistribution: area-weighting assumes income is spread uniformly over a block group — including parks, roads, parking. Parcels are a "where the housing actually is" mask.
  - The MHUD data (34,340 parcels; `Total_Units`, single-family `SFD`/`SFA` vs `MULTI`). Embed the hero:
    `![Arlington housing units by parcel — point size is unit count; multifamily parcels (few but unit-dense) carry most of the housing.](figures/map_parcels.png){#fig-parcels width=90%}`
  - The method: explode each parcel into `Total_Units` points, then redistribute block-group income through them with `redistribute_parcels`. Folded static snippet:

    `::: {.callout-note collapse="true" title="Python: parcel redistribution"}`
    ```python
    from sdc_redistribute import redistribute_parcels
    # explode each parcel into Total_Units identical points first, then:
    result = redistribute_parcels(
        source_df=counts_long, parcel_centroids=unit_points,
        source_geo="block_groups.geojson",
        target_geos={"civic_association": "civic_assoc.geojson"},
        count_cols=["agg_income", "households"], source_id="geoid",
    )
    ```
    `:::`
  - Results & comparison: embed `map_income_parcels.png` (#fig-income-parcels), `map_income_diff.png` (#fig-income-diff), `scatter_area_vs_parcel.png` (#fig-area-parcel). State the **real** biggest gainers/losers and diff range from the Task 3 output (fill from computed numbers — do NOT invent).
  - Limitation: every *unit* is weighted equally, so household-size differences (single-family households are larger than apartment households) are not yet captured. Forward pointer: the R package's `redistribute_parcel_pums_adj` weights by PUMS household sizes; porting that to `sdc-redistribute` is planned future work.

- [ ] **Step 2: Order the chapter in `guide/_quarto.yml`** — insert `- parcel-approach.qmd` immediately after `- 05-results.qmd`:

```yaml
    - 05-results.qmd
    - parcel-approach.qmd
    - 06-limitations.qmd
```

- [ ] **Step 3: Add the new modules to the code appendix generator** — in `scripts/build_code_appendix.py`, extend `MODULES` (after `combine.py`, before `validate.py`):

```python
    ("acquire_parcels.py", "Acquire parcels",
     "Page through the Arlington MHUD FeatureServer and reduce parcel polygons "
     "to unit-bearing centroids."),
    ("redistribute_income_parcels.py", "Redistribute income through parcels",
     "Explode parcels into per-unit points and redistribute block-group income "
     "through them (the dasymetric second approach)."),
    ("compare_methods.py", "Compare methods",
     "Join the area-weighted and parcel-weighted income and quantify the "
     "difference per civic association."),
```

- [ ] **Step 4: Regenerate the appendix + render HTML**

Run: `uv run python scripts/build_code_appendix.py` then `cd guide && quarto render --to html 2>&1 | tail -8 && cd ..`. Confirm `parcel-approach.html` builds, the 4 figures resolve (paths `figures/...` — copied in by the existing pre-render hook), and citations/refs are clean. Controller may review.

- [ ] **Step 5: Commit**

```bash
git add guide/parcel-approach.qmd guide/_quarto.yml scripts/build_code_appendix.py guide/08-code.qmd
git commit -m "feat: add parcel-approach guide chapter; extend code appendix"
```

---

## Task 6: Wire into the pipeline, full render, README

**Files:** Modify `pipeline/run.py`, `README.md`.

- [ ] **Step 1: Add the parcel steps to `pipeline/run.py`**

Import the new modules and call them in order — parcels after `acquire_ookla`, the parcel redistribution + compare after `combine`, before `validate`:

```python
from pipeline import (
    acquire_acs, acquire_geographies, acquire_ookla, acquire_parcels,
    combine, compare_methods, redistribute_broadband, redistribute_income,
    redistribute_income_parcels, validate,
)

def main() -> None:
    acquire_geographies.main()
    acquire_acs.main()
    acquire_ookla.main()
    acquire_parcels.main()
    redistribute_income.main()
    redistribute_broadband.main()
    combine.main()
    redistribute_income_parcels.main()
    compare_methods.main()
    validate.main()
    print("Pipeline complete.")
```

- [ ] **Step 2: Full deterministic suite + full build**

Run: `uv run pytest -m "not network" -q` → all green. Then `uv run python -m pipeline.build_figures` → prints `All N guide assets present.` (N is now 15). Then `cd guide && quarto render && cd ..` → PDF + HTML build.

- [ ] **Step 3: Verify the new chapter in the PDF (controller)**

Controller opens the parcel chapter pages in the rendered PDF and confirms the figures render (recall the float-drop caveat applies only to `filename=` code blocks; these are images + a folded callout) and the real comparison numbers read correctly.

- [ ] **Step 4: Update `README.md`** — add `pipeline.acquire_parcels` / parcel outputs to the data description, and note the guide now has a parcel-based second approach. Keep it brief.

- [ ] **Step 5: Commit**

```bash
git add pipeline/run.py README.md guide/_output/Creating-Local-Level-Geographic-Datasets.pdf guide/Creating-Local-Level-Geographic-Datasets.tex
git commit -m "feat: wire parcel steps into the pipeline runner; render guide; docs"
```

---

## Self-Review

**Spec coverage (2026-06-05 parcel-approach-design):**
- §4 MHUD acquisition (paged) → Task 1. ✓
- §5 unit-explosion + `redistribute_parcels` income + derived mean → Task 2. ✓
- §6 compare + honest totals accounting → Task 3. ✓
- §7 four figures (parcels hero, parcel income, diff, scatter) + `points_map` → Task 4. ✓
- §8 new chapter ordered after results + appendix auto-update → Task 5. ✓
- §10 pipeline-run/build-figures/render integration → Task 6. ✓
- §11 tests (explode, parcel redistribution, compare, smoke) → Tasks 1–4. ✓
- §3 non-goals respected: no `sdc-redistribute` change; broadband untouched; income only. ✓

**Placeholder scan:** No TBD/TODO. All code complete. Chapter prose is delegated via a content brief that requires the *computed* comparison numbers (explicitly "do not invent") — the only deferred values, filled from Task 3 output.

**Consistency:** `config.PARCELS`/`CIVIC_INCOME_PARCELS`/`CIVIC_INCOME_COMPARISON` defined in Task 1 Step 4 and used in Tasks 2–4. Column names (`mean_income_area`, `mean_income_parcel`, `diff`, `pct_diff`, `Total_Units`, `Unit_Type`) consistent across compare → figures → chapter. Figure filenames match `EXPECTED` (Task 4) and the chapter embeds (Task 5). `redistribute_parcels` return suffix `_parcels` handled in Task 2. New modules added to both `run.py` (Task 6) and the appendix `MODULES` (Task 5).

**Known risks (from spec §12, carried):** exploded-points `sjoin` cost (~110k points — fine at county scale); parcels outside associations reported by the compare step; diff-map classification on a diverging palette validated visually in Task 4 Step 5.
