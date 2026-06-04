# Quarto Guide Document — Implementation Plan (Plan 3)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Author the professional, illustrated Quarto guide — chapters of trimmed narrative carrying the *real* findings, embedding Plan 2's figures and flowcharts, folded inline Python snippets at the pivotal steps, a migrated bibliography — rendering to a print-quality PDF (primary) and an HTML site (bonus).

**Architecture:** A Quarto **book** project under `guide/`, one `.qmd` per chapter (clean separation, one task writes one chapter), assembled by `_quarto.yml` into a single combined PDF and a multi-page HTML site. The brand identity lives in `guide/theme.scss` (HTML) and LaTeX `include-in-header` (PDF), both pointing at the `fonts/` TTFs. Figures are pre-generated PNGs from Plan 2 (embedded, not executed); code snippets are **static** display blocks in collapsible callouts (no kernel needed → fast, robust renders). References migrate to `guide/references.bib`.

**Tech Stack:** Quarto 1.7, xelatex (system TeX Live — verified available), the Plan 2 visual assets in `figures/`, the brand fonts in `fonts/`.

---

## CRITICAL: the narrative must tell the REAL, recomputed story (verified from `data/civic_combined.geojson`)

The old archived draft (`archive/guide_consolidated.md`) contains **hand-written numbers that the real pipeline contradicts**. Every chapter MUST use the figures below, not the archived claims. Do not copy any neighborhood numbers or the "positive correlation / low-income = low-speed" framing from the archive.

**Headline facts (62 civic associations, ACS 2021 5-yr × Ookla 2023 Q2):**
- Mean of association mean-incomes ≈ **$215,600**; median ≈ **$191,500**. Total redistributed households ≈ **109,528**.
- Mean download ≈ **246.8 Mbps**, median **251.9**; mean upload ≈ **105 Mbps**.
- **Correlation(mean income, download speed) = −0.11** → income and broadband speed are essentially **decoupled** in Arlington. This is the central, counter-intuitive finding.
- Income-to-speed ratio spans **$238 – $2,490 per Mbps**.

**The real spatial story (this REPLACES the archive's inverted claims):**
- Highest incomes are leafy, low-density **north Arlington**: Gulf Branch ($468k), Rivercrest ($467k), Bellevue Forest ($466k), **Old Glebe ($447k)** — and these have **middling-to-low** broadband relative to income → the **highest $/Mbps ratios** (Arlingwood $2,490, Bellevue Forest $2,107, Gulf Branch $1,752, Old Glebe $1,713). Note: the archive wrongly called Old Glebe a "30.6 Mbps crisis"; in the real data Old Glebe is high-income with merely *relatively* low speed.
- Highest *speeds* are in **dense, lower/mid-income southern corridors**: Rivercrest aside, the fastest include Columbia Forest (320.8), Long Branch Creek (307.9), **Arlington Mill (307.0** — the **lowest-income** association at $73k), Fairlington (293.4). Arlington Mill has the **best** $/Mbps ratio ($238).
- Slowest: Foxcroft Heights (100.8), Arlingwood (117.3), Dominion Hills (176.2).
- Bivariate class counts (income tercile – speed tercile): `1-1:4, 1-2:8, 1-3:9, 2-1:6, 2-2:7, 2-3:7, 3-1:11, 3-2:5, 3-3:5`.
  - Largest class is **3-1 (high income, low speed): 11** — Williamsburg, Maywood, Dominion Hills, Arlingwood, Bellevue Forest, Donaldson Run … the north-Arlington low-density pattern.
  - **1-3 (low income, high speed): 9** — Columbia Heights, Forest Glen, Columbia Forest, Westover Village, Long Branch Creek, Arlington Mill … dense multifamily corridors with strong infrastructure.

**The honest interpretation the guide should teach:** in a uniformly affluent county, the digital-divide axis is **housing density / infrastructure build-out, not household income**. Dense multifamily areas attract competitive fiber/cable; low-density single-family enclaves see less. This is a more sophisticated, defensible, MAUP-aware conclusion than the archive's — and it is what the data shows.

**Two methodology points to state plainly:**
- The interpolated income measure is **mean household income** (aggregate income ÷ households), the spatially-additive quantity — **not** a median (medians cannot be areally redistributed). Say so explicitly.
- Speeds are **test-count-weighted** means derived from redistributed counts, not area-averages.

## File structure

```
local_level_data/
  guide/
    _quarto.yml            # book project: chapters, formats (pdf primary, html), bibliography
    theme.scss             # HTML brand theme (palette + fonts)
    in-header.tex          # PDF LaTeX brand setup (fonts, colors, spacing)
    references.bib         # migrated bibliography
    index.qmd              # title + Ch.1 The sub-county data gap
    01-boundary-problem.qmd
    02-the-data.qmd
    03-method.qmd
    04-worked-example.qmd
    05-results.qmd
    06-limitations.qmd
    07-apply-it.qmd
  scripts/
    build_bib.py           # one-shot: archive Sources list → references.bib
```

Figures are referenced from the chapters as `../figures/<name>.png` and `../figures/diagrams/<name>.png` (Quarto resolves relative to each `.qmd`).

---

## Task 1: Quarto book scaffolding + brand theme

**Files:**
- Create: `guide/_quarto.yml`, `guide/theme.scss`, `guide/in-header.tex`, `guide/index.qmd` (minimal placeholder), `guide/references.bib` (empty placeholder)

- [ ] **Step 1: Install brand fonts for the PDF engine (best-effort)**

macOS: copy the TTFs so xelatex/fontspec can resolve them by family name.
```bash
mkdir -p ~/Library/Fonts && cp fonts/*.ttf ~/Library/Fonts/ 2>/dev/null || true
```
Verify availability (informational): `fc-list 2>/dev/null | grep -iE "franklin|source serif|jetbrains" || echo "fontconfig not present (xelatex may still resolve via Library/Fonts)"`.

- [ ] **Step 2: Write `guide/_quarto.yml`**

```yaml
project:
  type: book
  output-dir: _output

book:
  title: "Creating Local-Level Geographic Datasets"
  subtitle: "A practical, illustrated guide for sub-county policy analysis"
  author: "Aaron Schroeder"
  date: "2026-06-04"
  chapters:
    - index.qmd
    - 01-boundary-problem.qmd
    - 02-the-data.qmd
    - 03-method.qmd
    - 04-worked-example.qmd
    - 05-results.qmd
    - 06-limitations.qmd
    - 07-apply-it.qmd
    - references.qmd

bibliography: references.bib

format:
  pdf:
    documentclass: scrreprt
    pdf-engine: xelatex
    toc: true
    number-sections: true
    colorlinks: true
    linkcolor: "RoyalBlue"
    keep-tex: true
    include-in-header: in-header.tex
    mainfont: "Source Serif 4"
    sansfont: "Libre Franklin"
    monofont: "JetBrains Mono"
    fig-pos: "H"
  html:
    theme: [cosmo, theme.scss]
    toc: true
    fig-cap-location: bottom
    code-fold: true
```

- [ ] **Step 3: Write `guide/theme.scss`**

```scss
/*-- scss:defaults --*/
$font-family-sans-serif: "Libre Franklin", system-ui, sans-serif;
$font-family-serif: "Source Serif 4", Georgia, serif;
$body-color: #1B2A4A;
$link-color: #2166AC;
$primary: #2166AC;

/*-- scss:rules --*/
body { font-family: $font-family-serif; line-height: 1.6; }
h1, h2, h3, h4, .sidebar, .quarto-title-block { font-family: $font-family-sans-serif; color: #1B2A4A; }
h2 { border-bottom: 2px solid #E5E7EB; padding-bottom: .3rem; }
.callout { border-left-color: #2A7F7F; }
a { color: #2166AC; }
figure figcaption { color: #6B7280; font-size: .9rem; }
```

- [ ] **Step 4: Write `guide/in-header.tex`**

```latex
% Brand colors and spacing for the PDF build
\usepackage{xcolor}
\definecolor{ink}{HTML}{1B2A4A}
\definecolor{civicblue}{HTML}{2166AC}
\definecolor{teal}{HTML}{2A7F7F}
\addtokomafont{disposition}{\color{ink}}   % headings in ink
\addtokomafont{title}{\color{ink}}
\usepackage{microtype}
\usepackage{setspace}
\onehalfspacing
```

- [ ] **Step 5: Write a minimal `guide/index.qmd` and empty `guide/references.bib`**

`guide/index.qmd`:
```markdown
# The Sub-County Data Gap {#sec-gap}

*Placeholder — populated in Task 3.*
```

`guide/references.bib`: a single comment line `% migrated in Task 2`.

- [ ] **Step 6: Smoke-render both formats**

Run from the repo root:
```bash
cd guide && quarto render --to html && quarto render --to pdf && cd ..
```
Expected: `guide/_output/` contains an HTML site and a PDF. If the PDF font setup fails (xelatex can't find "Source Serif 4" etc.), REMOVE the `mainfont/sansfont/monofont` lines from `_quarto.yml` (falls back to Latin Modern — still renders) and note this in your report; do NOT block on fonts. If `scrreprt`/`koma` commands error, report the exact error.

- [ ] **Step 7: Commit**

```bash
git add guide/ && git commit -m "feat: scaffold Quarto book project with brand theme"
```

---

## Task 2: Migrate the bibliography

Convert the archived Sources list into `guide/references.bib` so the guide can cite sources by key.

**Files:**
- Create: `scripts/build_bib.py`
- Create/overwrite: `guide/references.bib`

- [ ] **Step 1: Write `scripts/build_bib.py`**

```python
"""Convert the archived guide's numbered Sources list into BibTeX @online entries.

Reads archive/guide_consolidated.md, finds the '## Sources' section, parses
lines like 'N. [optional title] https://url', and writes guide/references.bib
with keys ref1..refN.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "archive" / "guide_consolidated.md"
OUT = ROOT / "guide" / "references.bib"

URL_RE = re.compile(r"(https?://\S+)")
NUM_RE = re.compile(r"^\s*(\d+)\.\s+(.*)$")


def main() -> None:
    text = SRC.read_text(encoding="utf-8")
    after = text.split("## Sources", 1)
    body = after[1] if len(after) > 1 else text
    entries: list[str] = []
    for line in body.splitlines():
        m = NUM_RE.match(line)
        if not m:
            continue
        num, rest = m.group(1), m.group(2).strip()
        um = URL_RE.search(rest)
        url = um.group(1).rstrip(").,") if um else ""
        title = rest.replace(url, "").strip(" -[]") if url else rest
        title = title.replace("{", "(").replace("}", ")") or f"Source {num}"
        key = f"ref{num}"
        if url:
            entries.append(
                f"@online{{{key},\n  title = {{{title}}},\n  url = {{{url}}},\n"
                f"  urldate = {{2026-06-04}}\n}}\n"
            )
        else:
            entries.append(f"@misc{{{key},\n  title = {{{title}}}\n}}\n")
    OUT.write_text("\n".join(entries), encoding="utf-8")
    print(f"Wrote {len(entries)} references → {OUT}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run it and sanity-check**

```bash
uv run python scripts/build_bib.py
grep -c '^@' guide/references.bib   # expect ~150+ entries
```
Expected: prints `Wrote N references` (N ≈ 150–163) and the grep count matches. Spot-check a couple of entries are well-formed (`head -20 guide/references.bib`).

- [ ] **Step 3: Add a `references.qmd` stub so Quarto renders the bibliography**

`guide/references.qmd`:
```markdown
# References {.unnumbered}

::: {#refs}
:::
```

- [ ] **Step 4: Commit**

```bash
git add scripts/build_bib.py guide/references.bib guide/references.qmd
git commit -m "feat: migrate archived sources to references.bib"
```

---

## Task 3: Chapters 1–2 (the data gap & the boundary problem)

Write `index.qmd` (Ch.1) and `01-boundary-problem.qmd` (Ch.2) and `02-the-data.qmd` (Ch.3). Trimmed prose from the archive's conceptual front-matter — but concise, broken up with figures. **Use real facts; cite sources via `[@refNN]` where natural.**

**Files:**
- Overwrite: `guide/index.qmd`
- Create: `guide/01-boundary-problem.qmd`, `guide/02-the-data.qmd`

- [ ] **Step 1: Write `guide/index.qmd` (Ch.1 — The Sub-County Data Gap)**

Content brief (write ~500–800 words of clean prose):
- Open with the problem: county-level data hides within-county variation that local officials (county/city/town/township) must act on. Neighborhoods, civic associations, corridors, service zones are the real decision units.
- Why sub-county data is scarce (small-numerator reliability, confidentiality, no standard collection). Keep it tight; cite a couple of `[@refNN]` from the bib (e.g. CDC sub-county tracking, Urban Institute neighborhood data).
- End by previewing the worked example (Arlington broadband × income → 62 civic associations) and that the guide shows the method in Python (R companion forthcoming).
- Include a short callout box: "Who this guide is for" (analysts + decision-makers).

Begin the file with the chapter heading `# The Sub-County Data Gap {#sec-gap}`.

- [ ] **Step 2: Write `guide/01-boundary-problem.qmd` (Ch.2 — Misaligned Boundaries / MAUP)**

Content brief (~500–700 words):
- Define the Modifiable Areal Unit Problem plainly: source datasets come on boundaries that match neither each other nor the policy unit.
- Introduce the three geographies (Ookla ~610 m tiles, ACS block groups, civic associations) and why none align.
- Embed the hero figure:
  ```markdown
  ![Transforming misaligned source data (Ookla tiles, ACS block groups) onto the policy-relevant civic-association geography.](../figures/fig_transformation_3panel.png){#fig-transform width=100%}
  ```
- Reference it with `@fig-transform` in the text.
- Start the file with `# The Problem of Misaligned Boundaries {#sec-maup}`.

- [ ] **Step 3: Write `guide/02-the-data.qmd` (Ch.3 — The Data)**

Content brief (~500 words + 2 figures):
- Three short subsections: **Ookla** (open speed-test tiles, zoom-16 web-mercator ~610 m, download/upload/tests; cite `[@refNN]`), **ACS** (block-group aggregate household income B19025 + households B11001 — note we use COUNTS, not the median; cite), **Civic associations** (62 community-defined neighborhoods, Arlington's formal channels of input; cite).
- Embed the locator and the Ookla-tiles figures:
  ```markdown
  ![Arlington's 62 civic associations — the policy-relevant target geography.](../figures/fig_locator_civic.png){#fig-locator width=90%}

  ![Ookla fixed-broadband speed-test tiles over Arlington (download Mbps).](../figures/fig_ookla_tiles.png){#fig-tiles width=90%}
  ```
- Start with `# The Data {#sec-data}`.

- [ ] **Step 4: Render to HTML and visually review**

Run: `cd guide && quarto render --to html && cd ..`
Expected: renders without error; the three chapters show their figures. Report any broken figure links (path issues) or render errors.

- [ ] **Step 5: Commit**

```bash
git add guide/index.qmd guide/01-boundary-problem.qmd guide/02-the-data.qmd
git commit -m "feat: write guide chapters 1-3 (gap, boundaries, data)"
```

---

## Task 4: Chapters 4–5 (the method & the worked example)

**Files:**
- Create: `guide/03-method.qmd`, `guide/04-worked-example.qmd`

- [ ] **Step 1: Write `guide/03-method.qmd` (Ch.4 — The Core Method)**

Content brief (~700 words + 1 diagram + 1 folded snippet):
- Explain areal interpolation in plain terms (allocate source values to overlapping targets by area).
- **The key teaching point — extensive vs. intensive:** counts (households, aggregate income, test counts) are *extensive* and redistribute by area; rates/averages (mean income, mean speed) are *intensive* and must be **derived** from redistributed counts, never area-averaged. State that mean income = aggregate income ÷ households, and that a **median cannot** be redistributed.
- Embed the data-flow diagram:
  ```markdown
  ![The redistribution method: extensive counts move area-weighted; intensive rates are derived from them.](../figures/diagrams/dataflow.png){#fig-dataflow width=100%}
  ```
- One **folded** Python snippet in a collapsible callout showing the core call (static display — NOT executed):
  ```markdown
  ::: {.callout-note collapse="true" title="Python: the redistribution call"}
  ​```python
  from sdc_redistribute import redistribute_direct

  result = redistribute_direct(
      source_df=counts_long,            # geoid, year, measure, value
      source_geo="block_groups.geojson",
      target_geos={"civic_association": "civic_assoc.geojson"},
      count_cols=["agg_income", "households"],   # EXTENSIVE counts
      source_id="geoid",
  )
  # mean income (INTENSIVE) is derived afterwards:
  #   mean_income = agg_income / households
  ​```
  :::
  ```
  (Use real triple backticks; the `​` zero-width marks are only to show nesting here.)
- Start with `# The Core Method: Areal Interpolation {#sec-method}`.

- [ ] **Step 2: Write `guide/04-worked-example.qmd` (Ch.5 — Worked Example)**

Content brief (~800 words, the two transform diagrams, 1–2 folded snippets):
- Walk the pipeline end to end at a high level: acquire (block groups via pygris, ACS counts via the Census API, Ookla tiles from S3) → redistribute income → redistribute broadband → combine → validate.
- Embed the two transform diagrams:
  ```markdown
  ![Income transform: redistribute aggregate income + households, then derive mean income.](../figures/diagrams/acs_transform.png){#fig-acs width=95%}

  ![Broadband transform: redistribute tests and speed×tests, then derive count-weighted speed.](../figures/diagrams/ookla_transform.png){#fig-ookla width=95%}
  ```
- One folded snippet for the broadband count-weighting trick (static), and one short note that household totals are **preserved within 2%** (validation).
- Point readers to the companion repo for the complete runnable pipeline (the `local_level_data` repo; `uv run python -m pipeline.run`).
- Start with `# Worked Example: Arlington, Step by Step {#sec-example}`.

- [ ] **Step 3: Render to HTML, visually review, commit**

Run: `cd guide && quarto render --to html && cd ..` — confirm diagrams + folded callouts render. Commit:
```bash
git add guide/03-method.qmd guide/04-worked-example.qmd
git commit -m "feat: write guide chapters 4-5 (method, worked example)"
```

---

## Task 5: Chapters 6–8 (results, limitations, apply-it)

This is where the **real findings** land. The implementer MUST use the verified facts at the top of this plan and must NOT reproduce the archive's inverted claims.

**Files:**
- Create: `guide/05-results.qmd`, `guide/06-limitations.qmd`, `guide/07-apply-it.qmd`

- [ ] **Step 1: Write `guide/05-results.qmd` (Ch.6 — Results & Interpretation)**

Content brief (~900 words, 4 figures). Tell the REAL story:
- **Income** distribution across associations (mean ≈ $215.6k, median ≈ $191.5k; range $73k Arlington Mill → $468k Gulf Branch). Embed:
  ```markdown
  ![Mean household income by civic association.](../figures/map_income.png){#fig-income width=85%}
  ```
- **Speed** distribution (mean ≈ 247 Mbps; fastest in dense southern corridors, slowest in low-density Foxcroft Heights / Arlingwood). Embed `../figures/map_speed.png` as `#fig-speed`.
- **The decoupling** — embed the scatter and state `**r = −0.11**`: income and speed are essentially unrelated in Arlington. Explicitly contrast with the naive expectation. Embed `../figures/scatter_income_speed.png` as `#fig-scatter`.
- **Income-to-speed ratio** ($238 Arlington Mill → $2,490 Arlingwood): the highest-ratio (most income per Mbps, i.e. weakest relative broadband) areas are the wealthy low-density north (Bellevue Forest, Gulf Branch, Old Glebe). Embed `../figures/map_ratio.png` as `#fig-ratio`.
- **Bivariate synthesis** — embed `../figures/map_bivariate.png` as `#fig-bivariate`; report the class counts; explain that the largest group is high-income/low-speed (north Arlington, 11 associations) and a notable low-income/high-speed group (dense corridors, 9) — so the divide tracks **housing density / infrastructure build-out, not income**.
- A short "policy implications" subsection grounded in THIS finding: target fiber/competition incentives at low-density single-family areas; dense multifamily corridors are already well served; income-based subsidy targeting would *miss* the actual speed gaps.
- Start with `# Results & Interpretation {#sec-results}`.

- [ ] **Step 2: Write `guide/06-limitations.qmd` (Ch.7 — Limitations & Uncertainty)**

Content brief (~400 words):
- Area-weighting assumes uniform distribution within source units (block groups, tiles); honest about this.
- Ookla coverage bias (volunteer speed tests skew to active users); ACS sampling error at block-group level.
- Mean (not median) income is what's interpolable; mean is sensitive to high earners — relevant in Arlington's very-high-income tails.
- Per-measure rescaling in `redistribute_direct` slightly perturbs derived ratios at county edges (the Plan 1 review note).
- Start with `# Limitations & Uncertainty {#sec-limits}`.

- [ ] **Step 3: Write `guide/07-apply-it.qmd` (Ch.8 — Apply It to Your Jurisdiction)**

Content brief (~400 words):
- A short recipe: define your target geography (GeoJSON with a `geoid`); get source counts on their native geography; redistribute counts; derive rates; validate totals; map.
- Link to the companion repo and `uv run python -m pipeline.run` / `pipeline.build_figures`.
- Note the R implementation is forthcoming (mirroring `sdc-redistribute`).
- Start with `# Apply It to Your Own Jurisdiction {#sec-apply}`.

- [ ] **Step 4: Render to HTML, visually review, commit**

Run: `cd guide && quarto render --to html && cd ..`. Verify all five result figures appear and the narrative cites the real numbers (grep the file for "−0.11"/"-0.11", "Arlington Mill", "Bellevue Forest" to confirm the real story is told, not the archive's). Commit:
```bash
git add guide/05-results.qmd guide/06-limitations.qmd guide/07-apply-it.qmd
git commit -m "feat: write guide chapters 6-8 (results, limitations, apply-it)"
```

---

## Task 6: Full render (PDF + HTML), verification, README

**Files:**
- Modify: `README.md` (add a "Guide" section)
- Produce: `guide/_output/` PDF + HTML (the PDF is committed as the deliverable)

- [ ] **Step 1: Render both formats from scratch**

```bash
cd guide && quarto render && cd ..
```
Expected: produces `guide/_output/<...>.pdf` (the combined book PDF) and the HTML site under `guide/_output/`. If PDF render fails on fonts, apply the Task 1 Step 6 fallback (drop the `mainfont` lines) and re-render; report what was needed.

- [ ] **Step 2: Verify the build**

- Confirm the PDF exists and is non-trivial (`ls -la guide/_output/*.pdf`; size > 500 KB given the figures).
- Confirm every embedded figure resolved (no "missing image" boxes): `grep -ri "could not" guide/_output/*.log 2>/dev/null || echo "no latex image errors"`.
- Confirm the bibliography rendered (the References chapter is non-empty).

- [ ] **Step 3: Add a "Guide" section to `README.md`**

Append (real triple backticks in the file):
```
## The Guide

The illustrated guide lives in `guide/` (Quarto book). Render it:

<fenced bash block>
cd guide && quarto render          # PDF (primary) + HTML site → guide/_output/
<end fence>

Figures come from `pipeline.build_figures`; the data from `pipeline.run`.
```

- [ ] **Step 4: Decide what to commit**

Commit the source and the PDF deliverable; ignore the bulky HTML site build:
```bash
printf "\nguide/_output/_book/\nguide/.quarto/\n" >> .gitignore
git add README.md .gitignore guide/_output/*.pdf 2>/dev/null || true
git add guide/
git commit -m "feat: render guide PDF + HTML; document build"
```
(If the PDF path differs, adjust; the goal is to commit the source `guide/*.qmd|yml|scss|tex|bib` and the rendered PDF, not the HTML `_book/` tree.)

- [ ] **Step 5: Report for controller visual review**

Report the PDF path and page count. The controller will open the PDF/first pages to visually confirm the professional appearance (typography, figures placed well, the bivariate/result maps present, the real numbers in the prose).

---

## Self-Review

**Spec coverage (design spec):**
- §2/§7 Quarto, PDF-primary + HTML, keep-tex → Task 1 `_quarto.yml`. ✓
- §1/§8 real-data narrative, mean-not-median, extensive/intensive → Tasks 3–5 content briefs + the verified-facts block. ✓
- §9 brand identity (fonts, palette) in both HTML (theme.scss) and PDF (in-header.tex) → Task 1. ✓
- §9 embed code-generated figures + flowcharts (Plan 2 assets) → Tasks 3–5. ✓
- §10 hybrid code: folded inline snippets at pivotal steps; full pipeline in companion repo → Task 4 callouts + Task 5 apply-it link. ✓
- §7 references migrated to .bib and cited → Task 2. ✓
- "Regenerate everything; rewrite narrative to match" → the CRITICAL facts block forces the real story and explicitly bars the archive's inverted claims. ✓
- R implementation explicitly noted as forthcoming (out of scope) → Task 5 apply-it. ✓

**Placeholder scan:** Config files, theme, the bib script, and every figure-embed path are concrete. Prose is delegated via detailed content briefs WITH the exact real numbers to use — not "write something here". The only deliberate placeholders are the Task-1 minimal `index.qmd` (overwritten in Task 3) and empty `references.bib` (filled in Task 2), both explicitly replaced. ✓

**Consistency:** Figure paths (`../figures/*.png`, `../figures/diagrams/*.png`) match Plan 2's committed asset names exactly (verified against the EXPECTED manifest: map_income, map_speed, map_ratio, map_bivariate, scatter_income_speed, fig_transformation_3panel, fig_locator_civic, fig_ookla_tiles, diagrams/dataflow|acs_transform|ookla_transform). Chapter filenames match `_quarto.yml` `chapters:` order. Fonts named in `_quarto.yml`/theme.scss/in-header.tex match the `fonts/` TTFs. ✓

**Known risks (flagged, with fallbacks in-plan):**
- PDF font resolution with variable TTFs under xelatex is the main risk; Task 1 Step 6 and Task 6 Step 1 give an explicit drop-the-mainfont fallback that still renders.
- `scrreprt` (book → chapters) renders each chapter on a new page; acceptable for a guide. If a continuous-article look is preferred later, switch `type: book`→single `index.qmd` with `##` sections (a future change, not needed now).
- The bib migration is heuristic (URL/title parsing); a few entries may have imperfect titles, but keys `refNN` are stable and citations resolve. Task 2 Step 2 spot-checks.
