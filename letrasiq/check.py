"""Validate a font source and (optionally) its compiled binary."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pathops
from fontTools.ttLib import TTFont

from letrasiq.drawing import load_design
from letrasiq.outline import path_bounds, svg_path_to_pathops
from letrasiq.glyph import ASCII_GLYPHS, load_locked
from letrasiq.pipeline import font_dir, load_glyph_sources
from letrasiq.quality import quality_warnings
from letrasiq.spec import FontSpec


@dataclass
class CheckResult:
    name: str
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def _contour_is_open(path: pathops.Path) -> bool:
    """True if any contour lacks a closePath."""
    open_contour = False
    started = False
    for verb, _pts in path.segments:
        if verb == "moveTo":
            if started:
                open_contour = True
            started = True
        elif verb == "closePath":
            started = False
        elif verb == "endPath":
            if started:
                open_contour = True
            started = False
    if started:
        open_contour = True
    return open_contour


def check_font(name: str, root: Path | None = None) -> CheckResult:
    d = font_dir(name, root)
    result = CheckResult(name=name)

    if not d.exists():
        result.errors.append(f"font folder missing: {d}")
        return result

    spec_path = d / "spec.json"
    if not spec_path.exists():
        result.errors.append("missing spec.json")
        return result

    try:
        spec = FontSpec.load(spec_path)
    except Exception as e:
        result.errors.append(f"invalid spec.json: {e}")
        return result

    for err in spec.validate():
        result.errors.append(f"spec: {err}")

    for w in spec.classification_warnings():
        result.warnings.append(w)

    if spec.name != name:
        result.warnings.append(f"spec.name ({spec.name!r}) != folder name ({name!r})")

    sources = load_glyph_sources(d)
    locked = load_locked(d / "locked.txt")

    # All expected glyphs present
    expected = ASCII_GLYPHS
    missing = [g for g in expected if g not in sources]
    if missing:
        result.errors.append(f"missing glyphs ({len(missing)}): {', '.join(missing[:12])}"
                             + ("…" if len(missing) > 12 else ""))

    # Locked names should exist
    for gname in sorted(locked):
        if gname not in sources:
            result.errors.append(f"locked glyph missing from glyphs/: {gname}")

    # Per-glyph outline / metrics checks
    advances: list[int] = []
    for gname, src in sources.items():
        if gname == "space":
            advance = src.width or spec.space_advance()
            if advance <= 0:
                result.errors.append("space advance must be > 0")
            continue
        path = svg_path_to_pathops(src.path or "")
        if not path:
            result.errors.append(f"{gname}: empty outline")
            continue
        if _contour_is_open(path):
            result.errors.append(f"{gname}: open contour")
        bounds = path_bounds(path)
        if bounds is not None:
            if bounds[3] > spec.ascender + spec.upm * 0.5:
                result.warnings.append(f"{gname}: extends far above ascender ({bounds[3]:.0f})")
            if bounds[1] < spec.descender - spec.upm * 0.5:
                result.warnings.append(f"{gname}: extends far below descender ({bounds[1]:.0f})")
        is_mark = any(name.startswith("_") for name in src.anchors)
        if src.width is not None and src.width <= 0 and not is_mark:
            result.errors.append(f"{gname}: non-positive advance ({src.width})")
        elif src.width is not None:
            advances.append(src.width)

    if advances and sum(advances) / len(advances) < spec.upm * 0.05:
        result.warnings.append("mean advance unusually small")

    # Compiled font checks (if present)
    build_dir = d / "build"
    ttfs = list(build_dir.glob("*.ttf")) + list(build_dir.glob("*.otf"))
    if not ttfs:
        result.warnings.append("no compiled OTF/TTF in build/ — run `letrasiq build`")
    else:
        font_path = ttfs[0]
        try:
            ft = TTFont(font_path)
            order = set(ft.getGlyphOrder())
            for gname in expected:
                if gname not in order:
                    result.errors.append(f"compiled font missing glyph: {gname}")
            cmap = ft.getBestCmap() or {}
            for code, gname in ((ord("A"), "A"), (ord("a"), "a"), (ord("0"), "zero")):
                if cmap.get(code) != gname:
                    result.errors.append(f"cmap U+{code:04X} expected {gname}, got {cmap.get(code)}")
            # Metrics consistency vs spec
            if "hhea" in ft:
                if abs(ft["hhea"].ascent - spec.ascender) > 2:
                    result.warnings.append(
                        f"hhea.ascent {ft['hhea'].ascent} != spec.ascender {spec.ascender}"
                    )
        except Exception as e:
            result.errors.append(f"failed to open compiled font: {e}")

    if (d / "design.json").exists():
        result.warnings.extend(quality_warnings(sources, load_design(d, spec)))
    else:
        result.errors.append("missing design.json")

    if not (d / "OFL.txt").exists():
        result.warnings.append("missing OFL.txt")

    return result


def format_check_result(result: CheckResult) -> str:
    lines = [f"check {result.name}: {'OK' if result.ok else 'FAIL'}"]
    for e in result.errors:
        lines.append(f"  ERROR  {e}")
    for w in result.warnings:
        lines.append(f"  WARN   {w}")
    if result.ok and not result.warnings:
        lines.append("  (no issues)")
    return "\n".join(lines)
