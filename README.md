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

## Method

Counts (aggregate income, households, broadband tests) are redistributed
area-weighted with `sdc-redistribute`; intensive rates (mean income, mean
speed) are derived from count ratios. See `docs/superpowers/specs/`.

## Tests

```bash
uv run pytest -m "not network"   # fast, deterministic
uv run pytest -m network         # live Census/Ookla acquisition
```
