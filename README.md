# Local-Level Data Guide — Pipeline

Reproducible Python pipeline behind the illustrated guide to creating
sub-county geographic datasets (Arlington County: broadband × income →
civic associations).

## Setup

```bash
uv venv --python 3.12 && uv sync
export CENSUS_API_KEY=your_key   # free: https://api.census.gov/data/key_signup.html
# or put CENSUS_API_KEY=your_key in a .env file (gitignored)
```

## Run

```bash
uv run python -m pipeline.run
```

Outputs land in `data/`:
- `civic_income.csv`, `civic_broadband.csv` — redistributed measures
- `civic_combined.geojson` — joined + derived metrics (ratio, bivariate class)
- `civic_income_parcels.csv` — parcel-centroid income redistribution via `pipeline.acquire_parcels` + `redistribute_income_parcels`
- `civic_income_comparison.geojson` — side-by-side comparison of area-weighted vs parcel-based estimates (`compare_methods`)

## Method

Counts (aggregate income, households, broadband tests) are redistributed
area-weighted with `sdc-redistribute`; intensive rates (mean income, mean
speed) are derived from count ratios. The guide now includes a second,
parcel-based approach that assigns block-group income to civic associations
using parcel centroids as a spatial proxy, with a comparison chapter showing
where the two methods agree and diverge. See `docs/superpowers/specs/`.

## Figures

Regenerate every map, bivariate chart, scatter, and flowchart used in the guide:

```bash
uv run python -m pipeline.build_figures   # writes figures/ and figures/diagrams/
```

Requires the Graphviz `dot` binary (`brew install graphviz`) for the flowcharts.

## Tests

```bash
uv run pytest -m "not network"   # fast, deterministic
uv run pytest -m network         # live Census/Ookla acquisition
```

## The Guide

The illustrated guide lives in `guide/` (Quarto book). Render it:

```bash
cd guide && quarto render          # PDF (primary) + HTML site -> guide/_output/
```

Figures come from `pipeline.build_figures`; the data from `pipeline.run`.

The final chapter is the full pipeline source, generated from `pipeline/*.py`.
Regenerate it after changing pipeline code:

```bash
uv run python scripts/build_code_appendix.py   # rewrites guide/08-code.qmd
```

Published site: <https://dads2busy.github.io/local-level-data-guide/>
