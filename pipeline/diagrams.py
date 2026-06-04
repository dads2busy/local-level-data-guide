"""Render the guide's Graphviz DOT diagrams to PNG + SVG."""
from __future__ import annotations

import subprocess
from pathlib import Path

DIAGRAMS = Path(__file__).resolve().parent.parent / "figures" / "diagrams"


def render_all() -> list[Path]:
    outputs: list[Path] = []
    for dot in sorted(DIAGRAMS.glob("*.dot")):
        for fmt in ("png", "svg"):
            out = dot.with_suffix(f".{fmt}")
            subprocess.run(
                ["dot", f"-T{fmt}", str(dot), "-o", str(out)], check=True
            )
            outputs.append(out)
    return outputs


def main() -> None:
    for out in render_all():
        print(f"rendered {out.relative_to(DIAGRAMS.parent.parent)}")


if __name__ == "__main__":
    main()
