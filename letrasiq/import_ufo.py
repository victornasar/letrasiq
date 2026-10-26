"""Import glyphs from an external UFO into a LetrasIQ font (locked custom)."""

from __future__ import annotations

from pathlib import Path

import ufoLib2

from letrasiq.glyph import GlyphSource, glyph_filename, load_locked, save_locked
from letrasiq.pipeline import font_dir
from letrasiq.spec import FontSpec


class ImportError_(RuntimeError):
    """Named ImportError_ to avoid shadowing builtins.ImportError."""


def _ufo_glyph_to_svg_d(glyph: ufoLib2.objects.Glyph) -> str:
    """Convert UFO contours to an SVG path d string (font Y-up coords)."""
    parts: list[str] = []
    for contour in glyph:
        pts = list(contour)
        if not pts:
            continue
        # UFO contours: first point begins; segmentType None = offcurve
        # Walk like fontTools
        started = False
        i = 0
        n = len(pts)
        # Find start
        while i < n:
            pt = pts[i]
            if pt.segmentType is not None:
                if not started:
                    parts.append(f"M {pt.x:.3f} {pt.y:.3f}")
                    started = True
                    i += 1
                    continue
                if pt.segmentType == "line":
                    parts.append(f"L {pt.x:.3f} {pt.y:.3f}")
                    i += 1
                elif pt.segmentType == "curve":
                    # previous two should be offcurves
                    if i < 2:
                        parts.append(f"L {pt.x:.3f} {pt.y:.3f}")
                        i += 1
                        continue
                    c1, c2 = pts[i - 2], pts[i - 1]
                    parts.append(
                        f"C {c1.x:.3f} {c1.y:.3f} {c2.x:.3f} {c2.y:.3f} {pt.x:.3f} {pt.y:.3f}"
                    )
                    i += 1
                elif pt.segmentType == "qcurve":
                    # Approximate as line to oncurve for robustness
                    parts.append(f"L {pt.x:.3f} {pt.y:.3f}")
                    i += 1
                else:
                    parts.append(f"L {pt.x:.3f} {pt.y:.3f}")
                    i += 1
            else:
                i += 1
        if started:
            parts.append("Z")
    return " ".join(parts)


def _ufo_glyph_to_svg_d_via_pen(glyph: ufoLib2.objects.Glyph) -> str:
    """Preferred: draw with RecordingPen-style via getPen into SVG commands."""
    commands: list[str] = []

    class _SvgPen:
        def moveTo(self, pt):  # noqa: N802
            commands.append(f"M {pt[0]:.3f} {pt[1]:.3f}")

        def lineTo(self, pt):  # noqa: N802
            commands.append(f"L {pt[0]:.3f} {pt[1]:.3f}")

        def curveTo(self, *pts):  # noqa: N802
            c1, c2, p = pts[0], pts[1], pts[2]
            commands.append(
                f"C {c1[0]:.3f} {c1[1]:.3f} {c2[0]:.3f} {c2[1]:.3f} {p[0]:.3f} {p[1]:.3f}"
            )

        def qCurveTo(self, *pts):  # noqa: N802
            cleaned = [p for p in pts if p is not None]
            if not cleaned:
                return
            # Flatten to lines through points (good enough for import MVP)
            for p in cleaned:
                commands.append(f"L {p[0]:.3f} {p[1]:.3f}")

        def closePath(self):  # noqa: N802
            commands.append("Z")

        def endPath(self):  # noqa: N802
            pass

        def addComponent(self, *args, **kwargs):  # noqa: N802
            pass

    pen = _SvgPen()
    glyph.draw(pen)
    return " ".join(commands)


def import_ufo(
    name: str,
    ufo_path: Path,
    root: Path | None = None,
    *,
    glyphs: list[str] | None = None,
) -> list[str]:
    """
    Import glyphs from a UFO into fonts/<name>/ as custom sources.
    Always appends imported names to locked.txt.
    Returns list of imported glyph names.
    """
    d = font_dir(name, root)
    if not d.exists():
        raise ImportError_(f"font not found: {d}")
    ufo_path = Path(ufo_path)
    if not ufo_path.exists():
        raise ImportError_(f"UFO not found: {ufo_path}")

    try:
        ufo = ufoLib2.Font.open(ufo_path)
    except Exception as e:
        raise ImportError_(f"failed to open UFO: {e}") from e

    # Optionally sync metrics from UFO if they look sane
    spec = FontSpec.load(d / "spec.json")
    if ufo.info.unitsPerEm:
        # keep our UPM; imported outlines stay in their coordinate space —
        # assume same UPM as the LetrasIQ font for MVP
        if ufo.info.unitsPerEm != spec.upm:
            # Scale note only — still import raw; user can rebuild after
            pass

    glyph_names = glyphs if glyphs is not None else list(ufo.keys())
    imported: list[str] = []
    locked = load_locked(d / "locked.txt")

    for gname in glyph_names:
        if gname not in ufo:
            continue
        if gname.startswith("_") or gname == ".notdef":
            continue
        glyph = ufo[gname]
        if not len(glyph) and not glyph.components:
            # empty (e.g. space) — still record advance
            if gname == "space" or glyph.width:
                src = GlyphSource(
                    name=gname,
                    type="custom",
                    path="",
                    width=int(glyph.width) if glyph.width else spec.space_advance(),
                )
                src.save(d / "glyphs" / glyph_filename(gname))
                locked.add(gname)
                imported.append(gname)
            continue

        d_attr = _ufo_glyph_to_svg_d_via_pen(glyph)
        if not d_attr.strip() and len(glyph):
            d_attr = _ufo_glyph_to_svg_d(glyph)
        if not d_attr.strip() and not glyph.components:
            continue

        src = GlyphSource(
            name=gname,
            type="custom",
            path=d_attr,
            width=int(glyph.width) if glyph.width is not None else None,
        )
        src.save(d / "glyphs" / glyph_filename(gname))
        locked.add(gname)
        imported.append(gname)

    save_locked(d / "locked.txt", locked)

    # Changelog line
    cl = d / "CHANGELOG.md"
    if imported:
        line = f"- Imported {len(imported)} glyph(s) from `{ufo_path.name}` and locked them\n"
        if cl.exists():
            cl.write_text(cl.read_text(encoding="utf-8") + line, encoding="utf-8")
        else:
            cl.write_text(f"# {spec.family_name()} Changelog\n\n{line}", encoding="utf-8")

    return imported
