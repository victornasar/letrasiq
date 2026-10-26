from letrasiq.glyph import MVP_GLYPHS
from letrasiq.spec import FontSpec
from letrasiq.templates import build_mvp_glyphs


def test_mvp_coverage():
    glyphs = build_mvp_glyphs(FontSpec(name="letra-sans"))
    for name in MVP_GLYPHS:
        assert name in glyphs
    assert glyphs["A"].type == "parametric"
    assert len(glyphs["A"].skeleton) >= 1
    assert glyphs["space"].skeleton == []