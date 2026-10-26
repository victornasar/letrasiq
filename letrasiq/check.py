"""Validate a font source and (optionally) its compiled binary."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pathops
from fontTools.ttLib import TTFont

from letrasiq.cleanup import cleanup_path
from letrasiq.expand import expand_glyph, path_bounds
from letrasiq.glyph import MVP_GLYPHS, load_locked
from letrasiq.pipeline import font_dir, load_glyph_sources
from letrasiq.spacing import advance_width
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

    if spec.name != name:
        result.warnings.append(f"spec.name ({spec.name!r}) != folder name ({name!r})")

    sources = load_glyph_sources(d)
    locked = load_locked(d / "locked.txt")

    # All MVP glyphs present
    missing = [g for g in MVP_GLYPHS if g not in sources]
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
            adv = spec.space_advance()
            if adv <= 0:
                result.errors.append("space advance must be > 0")
            advances.append(adv)
            continue

        if src.type == "custom":
            if not (src.path or "").strip():
                result.errors.append(f"{gname}: custom glyph has empty path")
                continue
        elif src.type == "parametric":
            if not src.skeleton and gname != "space":
                result.warnings.append(f"{gname}: parametric glyph has empty skeleton")

        try:
            path = cleanup_path(expand_glyph(src, spec))
        except Exception as e:
            result.errors.append(f"{gname}: expand failed: {e}")
            continue

        if path and _contour_is_open(path):
            result.errors.append(f"{gname}: open contour")

        bounds = path_bounds(path)
        if bounds is None and src.skeleton:
            result.warnings.append(f"{gname}: no outline bounds")
        elif bounds is not None:
            x0, y0, x1, y1 = bounds
            if x1 < x0 or y1 < y0:
                result.errors.append(f"{gname}: inverted bounds")
            # Extreme outliers vs UPM
            if y1 > spec.ascender + spec.upm * 0.5:
                result.warnings.append(f"{gname}: extends far above ascender ({y1:.0f})")
            if y0 < spec.descender - spec.upm * 0.5:
                result.warnings.append(f"{gname}: extends far below descender ({y0:.0f})")

            adv, left, right = advance_width(gname, path, spec, explicit_width=src.width)
            advances.append(adv)
            if adv <= 0:
                result.errors.append(f"{gname}: non-positive advance ({adv})")
            if left < 0 or right < 0:
                result.errors.append(f"{gname}: negative sidebearing")
            # Spacing sanity: sidebearings shouldn't dwarf the glyph
            bw = max(1.0, x1 - x0)
            if left + right > bw * 4 and gname not in ("period", "comma", "quotesingle", "colon", "exclam"):
                result.warnings.append(
                    f"{gname}: sidebearings very large vs outline ({left}+{right} vs width {bw:.0f})"
                )

    if advances:
        mean = sum(advances) / len(advances)
        for gname, src in sources.items():
            if gname == "space":
                continue
            # Recompute quickly from earlier would be better; skip heavy — warn on extreme
            pass
        if mean < spec.upm * 0.05:
            result.warnings.append(f"mean advance unusually small ({mean:.0f})")

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
            for gname in MVP_GLYPHS:
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
