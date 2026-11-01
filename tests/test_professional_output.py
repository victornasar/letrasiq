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
    assert font["hhea"].ascent == os2.sTypoAscender == 760


def test_figures_are_equal_width_and_not_kerned_together(built):
    font = TTFont(built["ttf"])
    widths = {font["hmtx"][name][0] for name in FIGURES}
    assert len(widths) == 1
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


def test_ttf_requests_smart_dropout(built):
    font = TTFont(built["ttf"])
    assert any(line.startswith("SCANCTRL") for line in font["prep"].program.getAssembly())
    assert font["gasp"].gaspRange == {0xFFFF: 0x000F}


@pytest.fixture(scope="module", params=["letra-humanist", "letra-transitional", "letra-geo", "letra-slab", "letra-code"])
def each_font(request, tmp_path_factory) -> tuple[str, dict[str, Path]]:
    root = tmp_path_factory.mktemp("fonts")
    shutil.copytree(
        REPO / "fonts" / request.param,
        root / request.param,
        ignore=shutil.ignore_patterns("build", "glyphs", "__pycache__"),
    )
    return request.param, build_font(request.param, root=root, skip_preview=True)


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
