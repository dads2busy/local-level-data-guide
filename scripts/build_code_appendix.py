"""Generate the guide's code appendix chapters from the real pipeline sources.

Single source of truth: `pipeline/*.py` (Python) and `pipeline-r/*.R` (R). This
embeds those modules verbatim into `guide/08-code.qmd` and `guide/09-code-r.qmd`,
so the appendices always match the runnable implementations. Re-run after
changing pipeline code:

    uv run python scripts/build_code_appendix.py
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

PY_MODULES: list[tuple[str, str, str]] = [
    ("config.py", "Configuration",
     "Central settings: the Arlington FIPS codes, the ACS count variables "
     "(aggregate income and households), and the dataset paths every other "
     "module reads."),
    ("acquire_geographies.py", "Acquire census geographies",
     "Download Arlington's census block groups, the source geography for the "
     "income redistribution."),
    ("acquire_acs.py", "Acquire ACS income counts",
     "Pull aggregate household income and household counts from the Census API. "
     "These are *counts* (extensive measures); mean income is derived later."),
    ("acquire_ookla.py", "Acquire Ookla broadband tiles",
     "Read the Ookla open-data broadband tiles from S3 and clip them to "
     "Arlington."),
    ("redistribute_income.py", "Redistribute income",
     "Area-weight the income and household counts onto civic associations with "
     "`sdc-redistribute`, then derive mean household income."),
    ("redistribute_broadband.py", "Redistribute broadband",
     "Redistribute test counts and the speed×tests product, then derive the "
     "count-weighted mean download and upload speeds."),
    ("combine.py", "Combine and derive metrics",
     "Join the redistributed income and broadband measures onto the civic "
     "association polygons and compute the income-to-speed ratio and the "
     "bivariate income×speed classes."),
    ("acquire_parcels.py", "Acquire parcels",
     "Page through the Arlington MHUD FeatureServer and reduce parcel polygons "
     "to unit-bearing centroids."),
    ("redistribute_income_parcels.py", "Redistribute income through parcels",
     "Explode parcels into per-unit points and redistribute block-group income "
     "through them (the dasymetric second approach)."),
    ("compare_methods.py", "Compare methods",
     "Join the area-weighted and parcel-weighted income and quantify the "
     "difference per civic association."),
    ("validate.py", "Validate",
     "Confirm household totals are preserved by the redistribution and that no "
     "speeds or incomes are negative."),
    ("run.py", "Run the full pipeline",
     "Wire every stage into one command: `uv run python -m pipeline.run`."),
]

R_MODULES: list[tuple[str, str, str]] = [
    ("config.R", "Configuration",
     "Shared paths, the projected CRS used for area weighting, and the count "
     "constants. Mirrors the Python configuration."),
    ("redistribute_income.R", "Redistribute income",
     "Area-weight aggregate income and households onto civic associations with "
     "`sdc.redistribute::redistribute_direct()`, then derive mean income."),
    ("redistribute_broadband.R", "Redistribute broadband",
     "Rebuild the speed×tests product, redistribute it with the test counts, "
     "then derive the count-weighted mean download and upload speeds."),
    ("combine.R", "Combine and derive metrics",
     "Join redistributed income and broadband onto the civic polygons and "
     "compute the income-to-speed ratio and bivariate income×speed classes."),
    ("redistribute_income_parcels.R", "Redistribute income through parcels",
     "Dasymetric income via `redistribute_parcels()`, weighting parcels by "
     "their unit count (the second approach)."),
    ("compare_methods.R", "Compare methods",
     "Join the area-weighted and parcel-weighted income and quantify the "
     "difference per civic association."),
    ("validate.R", "Validate",
     "Confirm household totals are preserved and that no speeds or incomes are "
     "negative."),
    ("run.R", "Run the R pipeline",
     "Run the redistribute/combine/validate stages end to end: "
     "`Rscript pipeline-r/run.R`."),
    ("acquire-recipe.R", "Acquisition recipe",
     "How the same inputs would be produced in R (`tidycensus`/`tigris`/"
     "`ooklaOpenDataR`). Shown for reference; not executed by the pipeline."),
    ("compare_to_python.R", "Parity with the Python pipeline",
     "Confirm the R outputs match the Python pipeline's mean income and "
     "download speed within tolerance."),
]

PY_HEADER = """\
# The Complete Pipeline Code (Python) {#sec-code}

This appendix reproduces the full, runnable Python pipeline behind the worked
example: the actual source, not a simplified sketch. It is generated directly
from the `pipeline/` package in the companion repository, so it always matches
the code that produced every figure and number in this guide.

The pipeline is built on the [`sdc-redistribute`](https://pypi.org/project/sdc-redistribute/)
package and runs end to end with a single command:

```bash
uv run python -m pipeline.run
```

The modules below appear in execution order. Figure generation
(`pipeline/style.py`, `pipeline/maps.py`, `pipeline/figures.py`) lives in the
same repository and is omitted here to keep the focus on the data method.
"""

R_HEADER = """\
# The Complete Pipeline Code (R) {#sec-code-r}

This appendix reproduces the runnable R counterpart to the worked example. It is
generated directly from the `pipeline-r/` directory in the companion repository.
The R pipeline reads the same intermediate data the Python pipeline produces and
performs the redistribution, combination, and validation in R, built on the
[`sdc.redistribute`](https://github.com/dads2busy/sdc.redistribute) package:

```r
# install.packages("pak"); pak::pak("dads2busy/sdc.redistribute")
# from the repository root:
# Rscript pipeline-r/run.R
```

Data acquisition is shown as a recipe (`acquire-recipe.R`) rather than re-run.
The `compare_to_python.R` module confirms the R results match the Python results.
"""


def _render(modules, src_dir: Path, src_label: str, lang: str, header: str) -> str:
    parts = [header]
    for filename, title, blurb in modules:
        src = (src_dir / filename).read_text(encoding="utf-8").rstrip()
        parts.append(f"\n## {title}\n\n{blurb}\n")
        parts.append(f"**`{src_label}/{filename}`**\n")
        parts.append(f"```{lang}\n{src}\n```\n")
    return "\n".join(parts) + "\n"


def main() -> None:
    py = _render(PY_MODULES, ROOT / "pipeline", "pipeline", "python", PY_HEADER)
    (ROOT / "guide" / "08-code.qmd").write_text(py, encoding="utf-8")
    r = _render(R_MODULES, ROOT / "pipeline-r", "pipeline-r", "r", R_HEADER)
    (ROOT / "guide" / "09-code-r.qmd").write_text(r, encoding="utf-8")
    print(f"Wrote 08-code.qmd ({len(PY_MODULES)} modules) and 09-code-r.qmd ({len(R_MODULES)} modules)")


if __name__ == "__main__":
    main()
