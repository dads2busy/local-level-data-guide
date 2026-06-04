"""Convert the archived guide's numbered Sources list into BibTeX @online entries.

Reads archive/guide_consolidated.md, finds the '## Sources' section, parses
lines like 'N. [optional title] https://url', and writes guide/references.bib
with keys ref1..refN.

Special-character handling:
- Markdown escapes (backslash before [, ], |, _) are stripped/unescaped in titles
- '&' in titles is escaped as backslash-& for BibTeX
- '%' in titles (outside URLs) is escaped as backslash-% for BibTeX
- '{' and '}' in titles are replaced with '(' and ')' to avoid BibTeX parse errors
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "archive" / "guide_consolidated.md"
OUT = ROOT / "guide" / "references.bib"

URL_RE = re.compile(r"(https?://\S+)")
NUM_RE = re.compile(r"^\s*(\d+)\.\s+(.*)$")


def clean_title(title: str) -> str:
    """Clean a raw title string for use in a BibTeX field."""
    # Remove markdown escape backslashes before [, ], |, _
    title = re.sub(r"\\([\[\]|_])", r"\1", title)
    # Remove [PDF] prefix/tags (with or without brackets)
    title = re.sub(r"\[PDF\]\s*", "", title, flags=re.IGNORECASE)
    # Remove [AM-02-040] style bracketed codes at the start
    title = re.sub(r"^\[[\w\-]+\]\s*", "", title)
    # Replace { and } to avoid BibTeX brace issues
    title = title.replace("{", "(").replace("}", ")")
    # Escape & for LaTeX/BibTeX (but not if already escaped)
    title = re.sub(r"(?<!\\)&", r"\\&", title)
    # Escape % for LaTeX/BibTeX (only in non-URL portions — handled after URL removal)
    title = re.sub(r"(?<!\\)%", r"\\%", title)
    # Clean up leading/trailing punctuation and whitespace
    return title.strip(" -[]")


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
        # Extract title: everything before the URL
        if url:
            raw_title = rest[: um.start()].strip()
        else:
            raw_title = rest
        title = clean_title(raw_title)
        if not title:
            # No descriptive title in the archive — use the URL host (e.g.
            # "stacks.cdc.gov") rather than a meaningless "Source N" placeholder.
            if url:
                title = re.sub(r"^https?://(www\.)?", "", url).split("/")[0]
            else:
                title = f"Source {num}"
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
