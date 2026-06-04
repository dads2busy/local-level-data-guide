# tests/test_assets.py
from pathlib import Path
from pipeline.build_figures import EXPECTED

ROOT = Path(__file__).resolve().parent.parent


def test_every_expected_asset_exists():
    missing = [p for p in EXPECTED if not (ROOT / p).exists()]
    assert not missing, f"missing assets: {missing}"
