"""Font-file standards: fixes for Font Bakery failures, and Font Bakery itself."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from fontTools.ttLib import TTFont

from letrasiq.outline import path_bounds, svg_path_to_pathops
from letrasiq.pipeline import build_font, load_glyph_sources
from letrasiq.report import FONT_BAKERY_EXCLUDE, latin_core

REPO = Path(__file__).resolve().parent.parent
FIGURES = ("zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine")


@pytest.fixture(scope="module")
def built(tmp_path_factory) -> dict[str, Path]:
    root = tmp_path_factory.mktemp("fonts")
    shutil.copytree(
        REPO / "fonts" / "letra-humanist",
        root / "letra-humanist",
        ignore=shutil.ignore_patterns("build", "glyphs", "__pycache__"),
    )
    outputs = build_font("letra-humanist", root=root, skip_preview=True)
    return {**outputs, "font_dir": root / "letra-humanist"}


def test_windows_metrics_cover_every_glyph_without_changing_line_spacing(built):
    font = TTFont(built["ttf"])
    bounds = [
        path_bounds(svg_path_to_pathops(s.path or ""))
        for s in load_glyph_sources(built["font_dir"]).values()
    ]
    bounds = [b for b in bounds if b]
    os2 = font["OS/2"]
    assert os2.usWinAscent >= max(b[3] for b in bounds)
    assert os2.usWinDescent >= max(-b[1] for b in bounds)
    assert os2.fsSelection & (1 << 7)
    assert font["hhea"].ascent == os2.sTypoAscender
    assert font["hhea"].ascent + abs(font["hhea"].descent) >= 1.2 * font["head"].unitsPerEm


def test_figures_are_proportional_by_default_with_equal_width_tabular_forms(built):
    font = TTFont(built["ttf"])
    assert len({font["hmtx"][name][0] for name in FIGURES}) > 1
    assert len({font["hmtx"][f"{name}.tf"][0] for name in FIGURES}) == 1
    import ufoLib2

    kerning = ufoLib2.Font.open(built["ufo"]).kerning
    assert not [pair for pair in kerning if pair[0] in FIGURES and pair[1] in FIGURES]


def test_non_breaking_space_shares_the_space_glyph(built):
    cmap = TTFont(built["ttf"]).getBestCmap()
    assert cmap[0x00A0] == cmap[0x0020] == "space"


def test_every_format_drops_mac_names_and_keeps_the_license(built):
    for key in ("otf", "ttf", "woff2"):
        name = TTFont(built[key])["name"]
        assert not [n for n in name.names if n.platformID == 1], key
        assert "Open Font License" in name.getDebugName(13), key


def test_both_formats_are_autohinted(built):
    pytest.importorskip("ttfautohint")
    pytest.importorskip("afdko")
    ttf = TTFont(built["ttf"])
    assert "fpgm" in ttf and "prep" in ttf
    assert len(ttf["glyf"]["n"].program.getBytecode()) > 0
    otf = TTFont(built["otf"])
    charstring = otf["CFF "].cff.topDictIndex[0].CharStrings["n"]
    charstring.decompile()
    assert any(op in charstring.program for op in ("hstem", "vstem", "hstemhm", "vstemhm", "hintmask"))


def test_a_missing_autohinter_leaves_a_working_unhinted_font(tmp_path):
    from unittest.mock import patch

    root = tmp_path / "fonts"
    root.mkdir()
    shutil.copytree(REPO / "fonts" / "letra-code", root / "letra-code", ignore=shutil.ignore_patterns("build", "glyphs", "__pycache__"))
    with patch("letrasiq.compile._autohint_ttf"), patch("letrasiq.compile._autohint_otf"):
        outputs = build_font("letra-code", root=root, skip_preview=True)
    font = TTFont(outputs["ttf"])
    assert "fpgm" not in font
    assert 0x41 in font.getBestCmap()


@pytest.fixture(scope="module", params=["letra-humanist", "letra-transitional", "letra-geo", "letra-slab", "letra-code"])
def each_font(request, tmp_path_factory) -> tuple[str, dict[str, Path]]:
    root = tmp_path_factory.mktemp("fonts")
    shutil.copytree(
        REPO / "fonts" / request.param,
        root / request.param,
        ignore=shutil.ignore_patterns("build", "glyphs", "__pycache__"),
    )
    return request.param, build_font(request.param, root=root, skip_preview=True)


def _kern(ufo, a: str, b: str) -> int:
    """The value a text engine applies: an exception first, then the class rule."""
    if (a, b) in ufo.kerning:
        return ufo.kerning[(a, b)]
    group1 = next((g for g, ms in ufo.groups.items() if g.startswith("public.kern1.") and a in ms), None)
    group2 = next((g for g, ms in ufo.groups.items() if g.startswith("public.kern2.") and b in ms), None)
    return ufo.kerning.get((group1, group2), 0)


def test_accented_letters_inherit_kerning_from_their_base(each_font):
    import ufoLib2

    name, outputs = each_font
    ufo = ufoLib2.Font.open(outputs["ufo"])
    if name == "letra-code":
        assert not ufo.groups and not ufo.kerning
        return
    assert ufo.groups
    assert _kern(ufo, "A", "V") < 0
    assert _kern(ufo, "Aacute", "V") == _kern(ufo, "A", "V")
    assert _kern(ufo, "T", "oacute") < 0


def test_kerning_never_makes_accented_pairs_touch(each_font):
    import ufoLib2

    from letrasiq.kerning import _Profiles

    name, outputs = each_font
    if name == "letra-code":
        return
    root = outputs["ufo"].parent.parent
    sources = load_glyph_sources(root)
    placed = {n: (svg_path_to_pathops(s.path or ""), s.width or 0) for n, s in sources.items() if s.path}
    profiles = _Profiles(placed)
    ufo = ufoLib2.Font.open(outputs["ufo"])
    for a, b in (("T", "odieresis"), ("T", "adieresis"), ("T", "edieresis"), ("V", "adieresis"), ("Y", "odieresis"), ("F", "adieresis"), ("P", "adieresis")):
        gap = profiles.gap(a, b)
        assert gap + _kern(ufo, a, b) >= 20, (a, b, gap, _kern(ufo, a, b))


def test_only_the_monospace_font_declares_a_fixed_width(each_font):
    name, outputs = each_font
    font = TTFont(outputs["ttf"])
    widths = {font["hmtx"][g][0] for g in font.getGlyphOrder()}
    if name == "letra-code":
        assert widths <= {0, 600}  # combining marks have no width of their own
        assert font["post"].isFixedPitch == 1
    else:
        assert len(widths) > 1
        assert font["post"].isFixedPitch == 0


def test_every_font_covers_ascii_from_its_sheet_alone(each_font):
    _, outputs = each_font
    cmap = TTFont(outputs["ttf"]).getBestCmap()
    assert all(code in cmap for code in range(32, 127))


def test_every_font_covers_latin_core_from_its_sheet_alone(each_font):
    _, outputs = each_font
    assert latin_core() <= set(TTFont(outputs["ttf"]).getBestCmap())


def test_accents_stay_clear_of_their_letters(each_font):
    _, outputs = each_font
    glyf = TTFont(outputs["ttf"])["glyf"]
    for base, accented in (("o", "oacute"), ("n", "ntilde"), ("O", "Odieresis"), ("A", "Aring")):
        glyf[base].recalcBounds(glyf)
        glyf[accented].recalcBounds(glyf)
        assert glyf[accented].yMax > glyf[base].yMax + 40, accented


def test_bases_and_marks_carry_anchors(each_font):
    import ufoLib2

    _, outputs = each_font
    ufo = ufoLib2.Font.open(outputs["ufo"])
    assert {a.name for a in ufo["a"].anchors} >= {"top", "bottom"}
    assert {a.name for a in ufo["acutecomb"].anchors} >= {"_top"}


def test_fallback_glyph_is_drawn(each_font):
    _, outputs = each_font
    font = TTFont(outputs["ttf"])
    assert font["glyf"][".notdef"].numberOfContours == 2


@pytest.mark.parametrize("key", ["ttf", "otf"])
def test_font_bakery_universal_profile_has_no_failures(each_font, key, tmp_path):
    pytest.importorskip("fontbakery")
    name, outputs = each_font
    report = tmp_path / "report.json"
    subprocess.run(
        [sys.executable, "-m", "fontbakery", "check-universal", str(outputs[key]), "-q", "--json", str(report), *FONT_BAKERY_EXCLUDE],
        capture_output=True,
    )
    data = json.loads(report.read_text(encoding="utf-8"))
    failed = [
        check["key"][1]
        for section in data["sections"]
        for check in section["checks"]
        if check["result"] in ("FAIL", "ERROR", "FATAL")
    ]
    # Font Bakery 1.1.0's monospace check crashes on CFF (KeyError: 'glyf'), so it only runs on the TTF.
    if key == "otf" and name == "letra-code":
        failed = [c for c in failed if "opentype/monospace" not in c]
    assert not failed


def _shape(font_path: Path, text: str, features: dict | None = None) -> list[tuple[str, int, int]]:
    """Run real text shaping: (glyph, x offset, advance) for each output glyph."""
    hb = pytest.importorskip("uharfbuzz")
    blob = hb.Blob.from_file_path(str(font_path))
    font = hb.Font(hb.Face(blob))
    buf = hb.Buffer()
    buf.add_str(text)
    buf.guess_segment_properties()
    hb.shape(font, buf, features or {})
    return [
        (font.glyph_to_string(info.codepoint), pos.x_offset, pos.x_advance)
        for info, pos in zip(buf.glyph_infos, buf.glyph_positions)
    ]


def test_marks_attach_and_i_loses_its_dot_when_shaped(each_font):
    _, outputs = each_font
    for path in (outputs["ttf"], outputs["otf"]):
        # j + acute has no ready-made character, so this exercises ccmp and mark together.
        shaped = _shape(path, "j\u0301")
        assert shaped[0][0] == "uni0237"
        assert shaped[1][0] == "acutecomb" and shaped[1][2] == 0
        # The mark moves to sit over the letter, whatever its own position.
        assert _shape(path, "J\u0301")[1][1] != 0


def test_ligatures_and_figure_styles_when_shaped(each_font):
    name, outputs = each_font
    path = outputs["ttf"]
    if name == "letra-code":
        assert [g for g, _, _ in _shape(path, "fi")] == ["f", "i"]
        assert len({a for _, _, a in _shape(path, "0123456789")}) == 1
        return
    assert [g for g, _, _ in _shape(path, "fi")] == ["fi"]
    assert [g for g, _, _ in _shape(path, "fl")] == ["fl"]
    proportional = _shape(path, "0123456789")
    tabular = _shape(path, "0123456789", {"tnum": True})
    assert len({a for _, _, a in proportional}) > 1
    assert len({a for _, _, a in tabular}) == 1
    assert [g for g, _, _ in _shape(path, "0123456789", {"tnum": True, "pnum": True})] != []


def test_case_forms_and_kerning_when_shaped(each_font):
    name, outputs = each_font
    path = outputs["ttf"]
    assert _shape(path, "(", {"case": True})[0][0] == "parenleft.case"
    if name != "letra-code":
        pair = _shape(path, "AV")
        default_a = _shape(path, "A")[0][2]
        assert pair[0][2] < default_a


def test_kerning_stays_off_with_the_kern_feature_disabled(built):
    pair = _shape(built["ttf"], "AV", {"kern": False})
    assert pair[0][2] == _shape(built["ttf"], "A")[0][2]
