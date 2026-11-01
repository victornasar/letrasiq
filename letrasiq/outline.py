"""Outline helpers shared across the engine."""

from __future__ import annotations

import pathops
from fontTools.pens.recordingPen import RecordingPen

Point = tuple[float, float]


def path_bounds(path: pathops.Path) -> tuple[float, float, float, float] | None:
    if not path:
        return None
    b = path.bounds
    return (float(b[0]), float(b[1]), float(b[2]), float(b[3])) if b else None


def svg_path_to_pathops(d: str) -> pathops.Path:
    """Parse SVG path data into a pathops Path."""
    from fontTools.svgLib.path import parse_path

    out = pathops.Path()
    if d and d.strip():
        rec = RecordingPen()
        parse_path(d, rec)
        rec.replay(out.getPen())
    return out


def _quad_to_cubic(p0: Point, p1: Point, p2: Point) -> tuple[Point, Point, Point]:
    c1 = (p0[0] + 2 / 3 * (p1[0] - p0[0]), p0[1] + 2 / 3 * (p1[1] - p0[1]))
    c2 = (p2[0] + 2 / 3 * (p1[0] - p2[0]), p2[1] + 2 / 3 * (p1[1] - p2[1]))
    return c1, c2, p2


def _emit_qcurve(out: pathops.Path, start: Point, pts: tuple) -> Point:
    """Convert TrueType qCurveTo (off-curves, on-curve) to cubics."""
    points = [p for p in pts if p is not None]
    cur = start
    for i in range(len(points) - 1):
        off = points[i]
        if i + 1 == len(points) - 1:
            end = points[-1]
        else:
            end = ((off[0] + points[i + 1][0]) / 2, (off[1] + points[i + 1][1]) / 2)
        c1, c2, end = _quad_to_cubic(cur, off, end)
        out.cubicTo(*c1, *c2, *end)
        cur = end
    return cur


def to_cubic_path(path: pathops.Path) -> pathops.Path:
    """Rewrite a path using only move, line, cubic and close."""
    if not path:
        return path
    path.convertConicsToQuads()
    out = pathops.Path()
    current: Point | None = None
    for verb, pts in path.segments:
        if verb == "moveTo":
            current = pts[0]
            out.moveTo(*current)
        elif verb == "lineTo":
            current = pts[0]
            out.lineTo(*current)
        elif verb == "qCurveTo":
            if current is not None:
                current = _emit_qcurve(out, current, pts)
        elif verb == "curveTo":
            out.cubicTo(*pts[0], *pts[1], *pts[2])
            current = pts[2]
        elif verb == "closePath":
            out.close()
            current = None
    return out


def cleanup_path(path: pathops.Path) -> pathops.Path:
    """Remove overlaps and round coordinates, for traced and imported outlines."""
    if not path:
        return path
    cubic = to_cubic_path(pathops.simplify(path, clockwise=False))
    out = pathops.Path()
    for verb, pts in cubic.segments:
        if verb == "moveTo":
            out.moveTo(round(pts[0][0]), round(pts[0][1]))
        elif verb == "lineTo":
            out.lineTo(round(pts[0][0]), round(pts[0][1]))
        elif verb == "curveTo":
            out.cubicTo(*[round(v) for p in pts for v in p])
        elif verb == "closePath":
            out.close()
    return out
