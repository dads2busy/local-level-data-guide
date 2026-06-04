# tests/test_figures_smoke.py
import pytest
from pipeline import figures


@pytest.mark.parametrize("fn", figures.ALL_FIGURES, ids=lambda f: f.__name__)
def test_figure_produces_nontrivial_png(fn):
    out = fn()
    assert out.exists()
    assert out.suffix == ".png"
    assert out.stat().st_size > 5000  # a real rendered map, not an empty canvas
