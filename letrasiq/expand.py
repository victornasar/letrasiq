"""Expand parametric skeletons into outline contours."""

from __future__ import annotations

import math

import pathops
from fontTools.pens.recordingPen import RecordingPen

from letrasiq.glyph import GlyphSource, Stroke
from letrasiq.spec import FontSpec

Point = tuple[float, float]


def _prepare_for_ops(path: pathops.Path) -> pathops.Path:
    """Convert conics from stroke() so boolean ops can consume the path."""
    if not path:
        return path
    path.convertConicsToQuads()
    return path


def union_paths(parts: list[pathops.Path]) -> pathops.Path:
    prepared = [_prepare_for_ops(p) for p in parts if p]
    if not prepared:
        return pathops.Path()
    if len(prepared) == 1:
        return prepared[0]
    out = pathops.Path()
    pathops.union(prepared, out.getPen())
    return out


def _vsub(a: Point, b: Point) -> Point:
    return (a[0] - b[0], a[1] - b[1])


def _vlen(a: Point) -> float:
    return math.hypot(a[0], a[1])


def _vnorm(a: Point) -> Point:
    L = _vlen(a)
    if L < 1e-9:
        return (0.0, 0.0)
    return (a[0] / L, a[1] / L)


def _vperp(a: Point) -> Point:
    return (-a[1], a[0])


def _angle(a: Point, b: Point) -> float:
    d = _vsub(b, a)
    return math.atan2(d[1], d[0])


def densify_polyline(points: list[Point], step: float = 8.0) -> list[Point]:
    if len(points) < 2:
        return list(points)
    out: list[Point] = [points[0]]
    for i in range(1, len(points)):
        a, b = points[i - 1], points[i]
        dist = _vlen(_vsub(b, a))
        n = max(1, int(dist / step))
        for k in range(1, n + 1):
            t = k / n
            out.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
    return out


def cubic_to_polyline(points: list[Point], samples_per_seg: int = 12) -> list[Point]:
    if len(points) < 4:
        return densify_polyline(points)
    out: list[Point] = [points[0]]
    i = 0
    while i + 3 < len(points):
        p0, c1, c2, p1 = points[i], points[i + 1], points[i + 2], points[i + 3]
        for s in range(1, samples_per_seg + 1):
            t = s / samples_per_seg
            u = 1 - t
            x = (
                u**3 * p0[0]
                + 3 * u**2 * t * c1[0]
                + 3 * u * t**2 * c2[0]
                + t**3 * p1[0]
            )
            y = (
                u**3 * p0[1]
                + 3 * u**2 * t * c1[1]
                + 3 * u * t**2 * c2[1]
                + t**3 * p1[1]
            )
            out.append((x, y))
        i += 3
    return out


def stroke_to_polyline(stroke: Stroke) -> list[Point]:
    pts = [(float(p[0]), float(p[1])) for p in stroke.points]
    if stroke.kind == "curve":
        return cubic_to_polyline(pts)
    return densify_polyline(pts)


def _terminal_cap(spec: FontSpec) -> pathops.LineCap:
    if spec.terminal_style in ("round", "ball"):
        return pathops.LineCap.ROUND_CAP
    if spec.terminal_style == "sheared":
        return pathops.LineCap.BUTT_CAP
    return pathops.LineCap.SQUARE_CAP


def _join_style(spec: FontSpec) -> pathops.LineJoin:
    if spec.corner_roundness >= 0.5:
        return pathops.LineJoin.ROUND_JOIN
    if spec.corner_roundness >= 0.2:
        return pathops.LineJoin.MITER_JOIN
    return pathops.LineJoin.BEVEL_JOIN


def _polyline_path(pts: list[Point], closed: bool = False) -> pathops.Path:
    p = pathops.Path()
    if not pts:
        return p
    p.moveTo(*pts[0])
    for pt in pts[1:]:
        p.lineTo(*pt)
    if closed:
        p.close()
    return p


def expand_stroke(
    stroke: Stroke, spec: FontSpec, weight_scale: float = 1.0
) -> pathops.Path:
    pts = stroke_to_polyline(stroke)
    if not pts:
        return pathops.Path()

    cap = _terminal_cap(spec)
    join = _join_style(spec)
    miter = 4.0

    if len(pts) == 1:
        # Dot — tiny horizontal stub then stroke
        r = spec.stroke_base() * weight_scale
        stub = _polyline_path([pts[0], (pts[0][0] + 0.01, pts[0][1])])
        stub.stroke(r, pathops.LineCap.ROUND_CAP, pathops.LineJoin.ROUND_JOIN, miter)
        return stub

    # Stroke whole polyline at average thickness for clean joins, then
    # for high contrast, also stroke individual segments and union.
    angles = [_angle(pts[i - 1], pts[i]) for i in range(1, len(pts))]
    thicknesses = [spec.thickness_for_angle(a) * weight_scale for a in angles]
    avg_t = sum(thicknesses) / len(thicknesses)

    if spec.contrast < 0.08:
        path = _polyline_path(pts, closed=stroke.closed)
        path.stroke(avg_t, cap, join, miter)
        return path

    # Variable width: stroke each segment, union
    parts: list[pathops.Path] = []
    for i in range(1, len(pts)):
        seg = _polyline_path([pts[i - 1], pts[i]])
        t = thicknesses[i - 1]
        seg.stroke(t, pathops.LineCap.ROUND_CAP, pathops.LineJoin.ROUND_JOIN, miter)
        parts.append(seg)
    if not parts:
        return pathops.Path()
    return union_paths(parts)


def _attach_serifs(
    outline: pathops.Path, stroke: Stroke, spec: FontSpec
) -> pathops.Path:
    if spec.serif_style == "none" or len(stroke.points) < 2:
        return outline
    pts = stroke_to_polyline(stroke)
    if len(pts) < 2:
        return outline
    base = spec.stroke_base()
    serif_len = base * (1.2 if spec.serif_style == "slab" else 0.7)
    serif_thick = base * (0.55 if spec.serif_style != "hairline" else 0.25)
    ends = [(pts[0], pts[1]), (pts[-1], pts[-2])]
    parts = [outline]
    for tip, prev in ends:
        direction = _vnorm(_vsub(tip, prev))
        nrm = _vperp(direction)
        a = (tip[0] + nrm[0] * serif_len / 2, tip[1] + nrm[1] * serif_len / 2)
        b = (tip[0] - nrm[0] * serif_len / 2, tip[1] - nrm[1] * serif_len / 2)
        bar = _polyline_path([a, b])
        bar.stroke(serif_thick, pathops.LineCap.BUTT_CAP, pathops.LineJoin.BEVEL_JOIN, 2.0)
        parts.append(bar)
    return union_paths(parts)


def apply_width_slant(path: pathops.Path, spec: FontSpec) -> pathops.Path:
    # SVG-style affine (a, b, c, d, e, f): x' = a*x + c*y + e
    x_scale = 0.6 + spec.width * 0.8
    shear = math.tan(spec.slant * 0.35) if abs(spec.slant) > 1e-6 else 0.0
    return path.transform(x_scale, 0, shear, 1, 0, 0)


def path_bounds(path: pathops.Path) -> tuple[float, float, float, float] | None:
    if not path:
        return None
    try:
        b = path.bounds
        if b is None:
            return None
        # skia pathops bounds: (xMin, yMin, xMax, yMax) or Rect
        if hasattr(b, "xMin"):
            return float(b.xMin), float(b.yMin), float(b.xMax), float(b.yMax)
        return float(b[0]), float(b[1]), float(b[2]), float(b[3])
    except Exception:
        return None


def expand_glyph(glyph: GlyphSource, spec: FontSpec) -> pathops.Path:
    if glyph.type == "custom":
        return svg_path_to_pathops(glyph.path or "")

    weight_scale = float(glyph.overrides.get("weight_scale", 1.0))
    parts: list[pathops.Path] = []
    for stroke in glyph.skeleton:
        outline = expand_stroke(stroke, spec, weight_scale=weight_scale)
        serif_override = glyph.overrides.get("serif")
        use_serif = (
            serif_override
            if serif_override is not None
            else spec.serif_style != "none"
        )
        if use_serif and spec.serif_style != "none":
            outline = _attach_serifs(outline, stroke, spec)
        if outline:
            parts.append(outline)
    if not parts:
        return pathops.Path()
    merged = union_paths(parts)
    return apply_width_slant(merged, spec)


def svg_path_to_pathops(d: str) -> pathops.Path:
    """Parse a subset of SVG path data into a pathops Path."""
    from fontTools.svgLib.path import parse_path

    if not d or not d.strip():
        return pathops.Path()
    out = pathops.Path()
    try:
        parse_path(d, out)
    except Exception:
        # RecordingPen fallback with method name mapping
        rec = RecordingPen()
        try:
            parse_path(d, rec)
        except Exception:
            return pathops.Path()
        for op, args in rec.value:
            if op == "moveTo":
                out.moveTo(*args[0])
            elif op == "lineTo":
                out.lineTo(*args[0])
            elif op == "curveTo":
                out.cubicTo(*args[0], *args[1], *args[2])
            elif op == "qCurveTo":
                pts = [p for p in args if p is not None]
                if len(pts) >= 2:
                    out.quadTo(*pts[0], *pts[1])
            elif op == "closePath":
                out.close()
    return out


def _quad_to_cubic(p0: Point, p1: Point, p2: Point) -> tuple[Point, Point, Point]:
    c1 = (p0[0] + 2 / 3 * (p1[0] - p0[0]), p0[1] + 2 / 3 * (p1[1] - p0[1]))
    c2 = (p2[0] + 2 / 3 * (p1[0] - p2[0]), p2[1] + 2 / 3 * (p1[1] - p2[1]))
    return c1, c2, p2


def _emit_qcurve(out: pathops.Path, start: Point, pts: tuple) -> Point:
    """Convert TrueType qCurveTo (offcurves…, oncurve) to cubics."""
    points = [p for p in pts if p is not None]
    if not points:
        return start
    cur = start
    i = 0
    while i < len(points) - 1:
        off = points[i]
        if i + 1 == len(points) - 1:
            end = points[-1]
            c1, c2, end = _quad_to_cubic(cur, off, end)
            out.cubicTo(*c1, *c2, *end)
            return end
        end = ((off[0] + points[i + 1][0]) / 2, (off[1] + points[i + 1][1]) / 2)
        c1, c2, end = _quad_to_cubic(cur, off, end)
        out.cubicTo(*c1, *c2, *end)
        cur = end
        i += 1
    out.lineTo(*points[-1])
    return points[-1]


def to_cubic_path(path: pathops.Path) -> pathops.Path:
    """Rewrite path using only move/line/cubic/close (no conics/quads)."""
    if not path:
        return path
    path = _prepare_for_ops(path)
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
            if current is None:
                continue
            current = _emit_qcurve(out, current, pts)
        elif verb == "curveTo":
            out.cubicTo(*pts[0], *pts[1], *pts[2])
            current = pts[2]
        elif verb == "closePath":
            out.close()
            current = None
        elif verb == "endPath":
            current = None
    return out


def round_path_coords(path: pathops.Path, ndigits: int = 0) -> pathops.Path:
    """Round coordinates; keep cubics/lines only."""
    cubic = to_cubic_path(path) if path else path
    out = pathops.Path()
    for verb, pts in cubic.segments:
        if verb == "moveTo":
            out.moveTo(round(pts[0][0], ndigits), round(pts[0][1], ndigits))
        elif verb == "lineTo":
            out.lineTo(round(pts[0][0], ndigits), round(pts[0][1], ndigits))
        elif verb == "curveTo":
            out.cubicTo(
                round(pts[0][0], ndigits), round(pts[0][1], ndigits),
                round(pts[1][0], ndigits), round(pts[1][1], ndigits),
                round(pts[2][0], ndigits), round(pts[2][1], ndigits),
            )
        elif verb == "closePath":
            out.close()
    return out
