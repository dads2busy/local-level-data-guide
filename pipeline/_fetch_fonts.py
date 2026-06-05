"""Best-effort download of the guide's OFL fonts into ./fonts.

Variable TTFs from the google/fonts repo. Failure is non-fatal; style.py falls
back to a generic sans-serif when a font is absent.
"""
from __future__ import annotations

import urllib.request
from pathlib import Path

FONTS = {
    "LibreFranklin.ttf": "https://github.com/google/fonts/raw/main/ofl/librefranklin/LibreFranklin%5Bwght%5D.ttf",
    "SourceSerif4.ttf": "https://github.com/google/fonts/raw/main/ofl/sourceserif4/SourceSerif4%5Bopsz,wght%5D.ttf",
    "JetBrainsMono.ttf": "https://github.com/google/fonts/raw/main/ofl/jetbrainsmono/JetBrainsMono%5Bwght%5D.ttf",
}


def main() -> None:
    out = Path(__file__).resolve().parent.parent / "fonts"
    out.mkdir(exist_ok=True)
    for name, url in FONTS.items():
        dest = out / name
        if dest.exists():
            print(f"have {name}")
            continue
        try:
            urllib.request.urlretrieve(url, dest)
            size = dest.stat().st_size
            if size < 5_000:
                print(f"WARN {name} too small ({size} bytes), likely an error page, deleting")
                dest.unlink()
                continue
            print(f"fetched {name} ({size} bytes)")
        except Exception as e:  # noqa: BLE001 - best effort
            print(f"WARN could not fetch {name}: {e}")


if __name__ == "__main__":
    main()
