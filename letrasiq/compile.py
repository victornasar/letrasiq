"""Build UFO and compile OTF/TTF/WOFF2."""

from __future__ import annotations

from importlib import resources
from pathlib import Path

import pathops
import ufoLib2
from fontTools.ttLib import TTFont

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
    ufo.info.openTypeOS2WinAscent = spec.ascender
    ufo.info.openTypeOS2WinDescent = abs(spec.descender)

    from letrasiq.glyph import glyph_unicode

    for name, (path, advance) in glyphs.items():
        g = ufo.newGlyph(name)
        g.width = advance
        if path:
            pen = g.getPen()
            path.draw(pen)
        cp = glyph_unicode(name)
        if cp is not None:
            g.unicodes = [cp]

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
        woff2 = out_dir / f"{stem}.woff2"
        _ttf_to_woff2(produced["ttf"], woff2)
        produced["woff2"] = woff2

    produced["ufo"] = ufo_path
    return produced


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
        name.setName(string, nid, 1, 0, 0)
    font.save(font_path)
