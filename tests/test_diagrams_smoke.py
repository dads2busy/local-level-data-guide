# tests/test_diagrams_smoke.py
from pipeline import diagrams


def test_renders_three_diagrams_to_png_and_svg():
    outputs = diagrams.render_all()
    pngs = [o for o in outputs if o.suffix == ".png"]
    svgs = [o for o in outputs if o.suffix == ".svg"]
    assert len(pngs) == 3 and len(svgs) == 3
    for o in outputs:
        assert o.exists() and o.stat().st_size > 1000
