"""The design sheet's shape settings really change construction, without changing stem weight."""

from __future__ import annotations

from dataclasses import replace

from letrasiq.check import check_font
from letrasiq.drawing import Design
from letrasiq.latin import draw_latin
from letrasiq.pipeline import build_font, create_font
from letrasiq.quality import stem_at
from letrasiq.spec import FontSpec
import json


def design(**shape) -> Design:
    return Design(
        xh=480, cap=700, asc=760, desc=-210, V=90, H=80, CV=96, CH=86, stress=0, os=12, fig=680,
        spacing={"S": 72, "R": 40, "O": 28, "D": 12, "T": 16}, shape=shape,
    )


def _contours(font, name: str) -> int:
    return [v for v, _ in font.glyphs[name].path.segments].count("moveTo")


def _ratio(font, name: str) -> float:
    x0, y0, x1, y1 = font.glyphs[name].path.bounds
    return (x1 - x0) / (y1 - y0)


def test_geometric_proportions_make_rounds_circular_and_keep_stems():
    plain, geo = draw_latin(design()), draw_latin(design(proportions="geometric"))
    assert abs(_ratio(geo, "o") - 1.0) < 0.02
    assert abs(_ratio(geo, "O") - 1.0) < 0.02
    assert _ratio(geo, "E") < _ratio(plain, "E")
    assert abs(stem_at(geo.glyphs["E"].path, 150) - 96) < 3


def test_width_overrides_adjust_a_preset():
    even = draw_latin(design(proportions="even"))
    wider = draw_latin(design(proportions="even", widths={"o_ratio": 0.95}))
    assert _ratio(wider, "o") > _ratio(even, "o")


def test_letter_forms_follow_the_sheet():
    double, single = draw_latin(design()), draw_latin(design(a="single", g="single"))
    assert _contours(double, "a") == _contours(single, "a") == 2
    assert _contours(double, "g") > _contours(single, "g")
    assert double.glyphs["a"].path.bounds != single.glyphs["a"].path.bounds


def test_aperture_and_dots_follow_the_sheet():
    open_c = draw_latin(design()).glyphs["c"].path
    closed_c = draw_latin(design(aperture="closed")).glyphs["c"].path
    assert open_c.bounds != closed_c.bounds
    assert list(draw_latin(design(dots="square")).glyphs["period"].path.segments)[1][0] == "lineTo"


def test_slab_serifs_add_width_beyond_the_stem():
    d = replace(design(), serifs="slab", H=60, CH=64)
    assert _ratio(draw_latin(d), "I") > _ratio(draw_latin(design()), "I")


def test_an_unseen_combination_builds_a_complete_clean_font(tmp_path):
    create_font("trial", FontSpec(name="trial", x_height=500), root=tmp_path)
    path = tmp_path / "trial" / "design.json"
    sheet = json.loads(path.read_text(encoding="utf-8"))
    sheet["style"] = {"serifs": "slab", "terminals": "cut"}
    sheet["shape"] = {"proportions": "even", "aperture": "closed", "dots": "square", "l": "plain"}
    sheet["values"].update(stem=110, thin=70, cap_stem=118, cap_thin=74, serif_thickness=60, serif_length=44)
    path.write_text(json.dumps(sheet), encoding="utf-8")
    build_font("trial", root=tmp_path, skip_preview=True)
    result = check_font("trial", root=tmp_path)
    assert result.ok, result.errors
