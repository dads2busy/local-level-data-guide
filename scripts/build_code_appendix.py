"""Generate the guide's code appendix chapter from the real pipeline source.

Single source of truth is `pipeline/*.py`. This script embeds those modules,
verbatim, into `guide/08-code.qmd` as labelled code blocks, so the guide's final
chapter always shows the actual runnable implementation behind the worked
example. Re-run after changing pipeline code:

    uv run python scripts/build_code_appendix.py
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PIPELINE = ROOT / "pipeline"
OUT = ROOT / "guide" / "08-code.qmd"

# Modules in pipeline-run order, each with a short subsection blurb.
MODULES: list[tuple[str, str, str]] = [
    ("config.py", "Configuration",
     "Central settings — the Arlington FIPS codes, the ACS count variables "
     "(aggregate income and households), and the dataset paths every other "
     "module reads."),
    ("acquire_geographies.py", "Acquire census geographies",
     "Download Arlington's census block groups — the source geography for the "
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

HEADER = """\
# The Complete Pipeline Code {#sec-code}

This appendix reproduces the full, runnable Python pipeline behind the worked
example — the actual source, not a simplified sketch. It is generated directly
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


def main() -> None:
    parts: list[str] = [HEADER]
    for filename, title, blurb in MODULES:
        src = (PIPELINE / filename).read_text(encoding="utf-8").rstrip()
        # NOTE: plain ```python blocks (not the `filename=` attribute). The
        # filename attribute wraps each block in a captioned float
        # (\begin{codelisting}), and floats taller than a page are silently
        # dropped by LaTeX — so long modules vanish from the PDF. A plain code
        # block renders in a framed (Shaded) environment that breaks across
        # pages. The filename is shown as a bold label instead.
        parts.append(f"\n## {title}\n\n{blurb}\n")
        parts.append(f"**`pipeline/{filename}`**\n")
        parts.append(f"```python\n{src}\n```\n")
    OUT.write_text("\n".join(parts) + "\n", encoding="utf-8")
    print(f"Wrote {OUT} from {len(MODULES)} pipeline modules")


if __name__ == "__main__":
    main()
