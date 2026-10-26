from letrasiq.expand import expand_glyph, path_bounds
from letrasiq.glyph import GlyphSource, Stroke
from letrasiq.spec import FontSpec


def test_expand_simple_stem():
    spec = FontSpec(name="t")
    glyph = GlyphSource(
        name="I",
        type="parametric",
        skeleton=[Stroke(kind="stroke", points=[[100, 0], [100, 700]])],
    )
    path = expand_glyph(glyph, spec)
    bounds = path_bounds(path)
    assert bounds is not None
    x0, y0, x1, y1 = bounds
    assert y1 - y0 > 500
    assert x1 - x0 > 10


def test_custom_svg_path():
    spec = FontSpec(name="t")
    glyph = GlyphSource(
        name="box",
        type="custom",
        path="M 0 0 L 100 0 L 100 100 L 0 100 Z",
    )
    path = expand_glyph(glyph, spec)
    bounds = path_bounds(path)
    assert bounds is not None
    assert bounds[2] - bounds[0] >= 99