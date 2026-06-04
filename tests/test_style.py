from pipeline import style


def test_palette_has_core_colors():
    for key in ("ink", "blue", "teal", "amber", "gray", "light"):
        assert key in style.PALETTE
        assert style.PALETTE[key].startswith("#") and len(style.PALETTE[key]) == 7


def test_bivariate_has_nine_classes():
    keys = {f"{i}-{j}" for i in (1, 2, 3) for j in (1, 2, 3)}
    assert set(style.BIVARIATE_COLORS) == keys


def test_bivariate_color_lookup():
    # high income (3), low speed (1) → the strong magenta corner
    assert style.BIVARIATE_COLORS["3-1"] == "#be64ac"
    assert style.BIVARIATE_COLORS["1-1"] == "#e8e8e8"
    assert style.BIVARIATE_COLORS["3-3"] == "#3b4994"


def test_apply_style_is_idempotent_and_sets_dpi():
    style.apply_style()
    import matplotlib as mpl
    assert mpl.rcParams["savefig.dpi"] == style.FIG_DPI
    style.apply_style()  # second call must not raise
