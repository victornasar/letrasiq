"""Build UFO and compile OTF/TTF/WOFF2."""

from __future__ import annotations

import math
from importlib import resources
from pathlib import Path

import pathops
import ufoLib2
from fontTools.ttLib import TTFont, newTable
from fontTools.ttLib.tables.ttProgram import Program

from letrasiq.outline import path_bounds
from letrasiq.spec import FontSpec


def ofl_text() -> str:
    return resources.files("letrasiq").joinpath("data/OFL.txt").read_text(encoding="utf-8")


def ensure_ofl(font_dir: Path) -> None:
    dest = font_dir / "OFL.txt"
    if not dest.exists():
        dest.write_text(ofl_text(), encoding="utf-8")


def build_ufo(
    spec: FontSpec,
    glyphs: dict[str, tuple[pathops.Path, int]],
    kerning: dict[tuple[str, str], int] | None = None,
    fixed_advance: int = 0,
) -> ufoLib2.Font:
    ufo = ufoLib2.Font()
    ufo.info.familyName = spec.family_name()
    ufo.info.styleName = spec.style_name
    ufo.info.unitsPerEm = spec.upm
    ufo.info.ascender = spec.ascender
    ufo.info.descender = spec.descender
    ufo.info.capHeight = spec.cap_height
    ufo.info.xHeight = spec.x_height
    ufo.info.versionMajor, ufo.info.versionMinor = _parse_version(spec.version)
    ufo.info.openTypeNameLicense = "SIL Open Font License 1.1"
    ufo.info.openTypeNameLicenseURL = "https://scripts.sil.org/OFL"
    ufo.info.copyright = f"Copyright (c) 2026, {spec.family_name()} Authors"
    ufo.info.openTypeOS2TypoAscender = spec.ascender
    ufo.info.openTypeOS2TypoDescender = spec.descender
    ufo.info.openTypeOS2TypoLineGap = 0
    # Windows clips anything outside its ascent and descent, so they must cover
    # every glyph. Typo metrics then keep line spacing independent of those values.
    bounds = [b for b in (path_bounds(path) for path, _ in glyphs.values()) if b]
    ufo.info.openTypeOS2WinAscent = max([spec.ascender, *(math.ceil(b[3]) for b in bounds)])
    ufo.info.openTypeOS2WinDescent = max([abs(spec.descender), *(math.ceil(-b[1]) for b in bounds)])
    ufo.info.openTypeOS2Selection = [7]
    ufo.info.openTypeHheaAscender = spec.ascender
    ufo.info.openTypeHheaDescender = spec.descender
    ufo.info.openTypeHheaLineGap = 0

    from letrasiq.glyph import glyph_unicode

    for name, (path, advance) in glyphs.items():
        g = ufo.newGlyph(name)
        g.width = advance
        if path:
            pen = g.getPen()
            path.draw(pen)
        cp = glyph_unicode(name)
        if cp is not None:
            # The non-breaking space shares the space glyph.
            g.unicodes = [cp, 0x00A0] if name == "space" else [cp]

    if fixed_advance:
        ufo.info.postscriptIsFixedPitch = True
        ufo.info.openTypeOS2Panose = [2, 11, 5, 9, 0, 0, 0, 0, 0, 0]

    # The fallback glyph is a visible box, on the font's single width if it has one.
    notdef = ufo.newGlyph(".notdef")
    notdef.width = fixed_advance or 500
    box = (notdef.width - 400) / 2
    pen = notdef.getPen()
    for contour in (
        [(box, 0), (box + 400, 0), (box + 400, spec.cap_height), (box, spec.cap_height)],
        [(box + 40, 40), (box + 40, spec.cap_height - 40), (box + 360, spec.cap_height - 40), (box + 360, 40)],
    ):
        pen.moveTo(contour[0])
        for point in contour[1:]:
            pen.lineTo(point)
        pen.closePath()

    if kerning:
        for (a, b), val in kerning.items():
            ufo.kerning[a, b] = val

    # public.default names
    ufo.lib["public.skipExportGlyphs"] = []
    return ufo


def _parse_version(version: str) -> tuple[int, int]:
    parts = version.split(".")
    major = int(parts[0]) if parts else 0
    minor = int(parts[1]) if len(parts) > 1 else 0
    return major, minor


def compile_otf_ttf(
    ufo: ufoLib2.Font,
    out_dir: Path,
    family: str,
    style: str = "Regular",
) -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{family.replace(' ', '')}-{style}"
    ufo_path = out_dir / f"{stem}.ufo"
    # remove existing
    if ufo_path.exists():
        import shutil

        shutil.rmtree(ufo_path)
    ufo.save(ufo_path)

    # Use fontmake for OTF (CFF) and TTF
    from fontmake.font_project import FontProject

    project = FontProject()
    otf_path = out_dir / f"{stem}.otf"
    ttf_path = out_dir / f"{stem}.ttf"

    # Overlaps already removed via pathops in cleanup; booleanOperations
    # chokes on some stroked contours, so skip a second remove-overlaps pass.
    project.run_from_ufos(
        [str(ufo_path)],
        output=("otf", "ttf"),
        output_dir=str(out_dir),
        remove_overlaps=False,
        use_production_names=False,
    )

    # fontmake names files as Family-Style.otf based on UFO info
    # Normalize to our stem if needed
    produced = {}
    for ext in ("otf", "ttf"):
        candidates = list(out_dir.glob(f"*.{ext}"))
        # prefer exact stem
        exact = out_dir / f"{stem}.{ext}"
        if exact.exists():
            produced[ext] = exact
        elif candidates:
            # rename newest
            newest = max(candidates, key=lambda p: p.stat().st_mtime)
            if newest.name != exact.name:
                newest.replace(exact)
            produced[ext] = exact

    if "ttf" in produced:
        _set_unhinted_rendering(produced["ttf"])
        woff2 = out_dir / f"{stem}.woff2"
        _ttf_to_woff2(produced["ttf"], woff2)
        produced["woff2"] = woff2

    produced["ufo"] = ufo_path
    return produced


def _set_unhinted_rendering(ttf_path: Path) -> None:
    """Ask rasterizers for smart dropout and smoothing, as an unhinted TrueType font should."""
    font = TTFont(ttf_path)
    prep = newTable("prep")
    prep.program = Program()
    prep.program.fromAssembly(["PUSHW[]", "511", "SCANCTRL[]", "PUSHB[]", "4", "SCANTYPE[]"])
    font["prep"] = prep
    gasp = newTable("gasp")
    gasp.gaspRange = {0xFFFF: 0x000F}
    font["gasp"] = gasp
    font["head"].flags |= 1 << 3
    font.save(ttf_path)


def _ttf_to_woff2(ttf_path: Path, woff2_path: Path) -> None:
    try:
        import brotli  # noqa: F401
    except ImportError as e:
        raise ImportError(
            "WOFF2 export requires the brotli package (`pip install brotli`)"
        ) from e
    font = TTFont(ttf_path)
    font.flavor = "woff2"
    font.save(woff2_path)


def set_name_table_license(font_path: Path, family: str) -> None:
    font = TTFont(font_path)
    name = font["name"]
    from fontTools.ttLib.tables._n_a_m_e import makeName

    # name IDs: 0 copyright, 13 license, 14 license URL
    for nid, string in (
        (0, f"Copyright (c) 2026, {family} Authors"),
        (13, "SIL Open Font License 1.1"),
        (14, "https://scripts.sil.org/OFL"),
    ):
        name.setName(string, nid, 3, 1, 0x409)
    name.names = [n for n in name.names if n.platformID != 1]
    font.save(font_path)
