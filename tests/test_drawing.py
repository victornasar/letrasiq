import json
import shutil
from pathlib import Path

from letrasiq.check import check_font
from letrasiq.drawing import Design, Drawing, poly, rect, stroke, tidy, union
from letrasiq.glyph import ASCII_GLYPHS, GlyphSource, glyph_char, glyph_filename
from letrasiq.pipeline import build_font
from letrasiq.quality import quality_warnings, stem_at

REPO = Path(__file__).resolve().parent.parent


def design() -> Design:
    return Design(xh=500, cap=700, asc=750, desc=-200, V=90, H=70, CV=100, CH=80, stress=0, os=12, fig=680)


def verbs(path) -> list[str]:
    return [v for v, _ in path.segments]


def test_ascii_set_covers_every_printable_character():
    assert len(ASCII_GLYPHS) == 95
    assert {glyph_char(n) for n in ASCII_GLYPHS} == {chr(c) for c in range(32, 127)}


def test_stroke_outlines_are_real_curves():
    d = design()
    ring = stroke(d, [(200, 0, 0), (400, 250, 90), (200, 500, 180), (0, 250, 270)], closed=True)
    out = tidy(union(ring))
    # Two contours of a few cubics each, not a densely sampled polygon.
    assert verbs(out).count("moveTo") == 2
    assert 8 <= verbs(out).count("curveTo") <= 16
    assert "lineTo" not in verbs(out)


def test_stroke_thickness_follows_direction():
    d = design()
    upright = union(stroke(d, [(0, 0, 90), (0, 400, 90)]))
    level = union(stroke(d, [(0, 0, 0), (400, 0, 0)]))
    assert round(upright.bounds[2] - upright.bounds[0]) == d.V
    assert round(level.bounds[3] - level.bounds[1]) == d.H


def test_union_merges_parts_with_opposite_winding():
    crossing = union(rect(0, 0, 100, 300), rect(100, 100, 0, 200), rect(-50, 100, 150, 200))
    assert verbs(crossing).count("moveTo") == 1


def test_tidy_adds_points_at_extremes():
    d = design()
    tilted = Design(**{**d.__dict__, "stress": -20})
    ring = stroke(tilted, [(200, 0, 0), (400, 250, 90), (200, 500, 180), (0, 250, 270)], closed=True)
    out = tidy(union(ring))
    source = GlyphSource(name="o", type="drawn", path=_svg(out), width=500)
    assert not [w for w in quality_warnings({"o": source}, tilted) if "extreme" in w]


def test_drawing_places_glyph_by_spacing_values():
    d = design()
    d.spacing = {"S": 70}
    f = Drawing(d)
    f.add("I", [rect(500, 0, 600, 700)], ("S", "S"))
    placed = f.glyphs["I"]
    assert placed.path.bounds[0] == 70
    assert placed.width == 240


def test_fixed_advance_centres_outline():
    f = Drawing(design())
    f.add("one", [rect(0, 0, 100, 680)], advance=500)
    assert f.glyphs["one"].width == 500
    assert f.glyphs["one"].path.bounds[0] == 200


def test_stem_measurement_and_warning():
    assert stem_at(rect(10, 0, 100, 500), 250) == 90
    d = design()
    source = GlyphSource(name="n", type="drawn", path=_svg(tidy(union(rect(0, 0, 140, 500)))), width=300)
    assert any("stem 140" in w for w in quality_warnings({"n": source}, d))


def test_overshoot_warning_for_flat_round_letter():
    d = design()
    source = GlyphSource(name="o", type="drawn", path=_svg(tidy(union(rect(0, 0, 400, 500)))), width=500)
    warnings = quality_warnings({"o": source}, d)
    assert any("overshoot" in w for w in warnings)


def test_kerning_closes_open_pairs_and_leaves_straight_pairs(tmp_path):
    from letrasiq.kerning import kern_value

    f = Drawing(design())
    f.add("A", [poly((0, 0), (100, 0), (350, 700), (250, 700)), poly((600, 0), (500, 0), (350, 700), (250, 700))])
    f.add("V", [poly((250, 0), (350, 0), (100, 700), (0, 700)), poly((250, 0), (350, 0), (600, 700), (500, 700))])
    f.add("H", [rect(0, 0, 100, 700), rect(400, 0, 500, 700)], (80, 80))
    a, v, h = f.glyphs["A"], f.glyphs["V"], f.glyphs["H"]
    assert kern_value(a.path, a.width, v.path, target_gap=95, clamp=(-90, 0), damping=0.75) == -90
    assert kern_value(h.path, h.width, h.path, target_gap=160, clamp=(-90, 0), damping=0.75) == 0


def _svg(path) -> str:
    from letrasiq.drawing import path_to_svg

    return path_to_svg(path)


def _copy_font(tmp_path: Path) -> Path:
    src = REPO / "fonts" / "letra-humanist"
    dest = tmp_path / "letra-humanist"
    shutil.copytree(src, dest, ignore=shutil.ignore_patterns("build", "glyphs"))
    return dest


def test_build_generates_full_font_and_tester(tmp_path):
    _copy_font(tmp_path)
    outputs = build_font("letra-humanist", root=tmp_path)
    for key in ("otf", "ttf", "woff2", "review", "detail", "tester"):
        assert outputs[key].exists()
    page = outputs["tester"].read_text(encoding="utf-8")
    assert "__FONT__" not in page and "__SAMPLES__" not in page
    assert "font/woff2;base64," in page
    assert check_font("letra-humanist", root=tmp_path).ok


def test_build_leaves_locked_glyphs_alone(tmp_path):
    d = _copy_font(tmp_path)
    (d / "glyphs").mkdir()
    (d / "locked.txt").write_text("H\n", encoding="utf-8")
    hand_edit = {"type": "drawn", "path": "M0 0L100 0L100 700L0 700Z", "width": 200}
    target = d / "glyphs" / glyph_filename("H")
    target.write_text(json.dumps(hand_edit), encoding="utf-8")
    build_font("letra-humanist", root=tmp_path, skip_preview=True)
    assert json.loads(target.read_text(encoding="utf-8")) == hand_edit
