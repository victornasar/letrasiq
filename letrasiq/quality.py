"""Outline and consistency checks for fonts drawn with draw.py."""

from __future__ import annotations

import math

import pathops

from letrasiq.drawing import Design, _bez
from letrasiq.outline import path_bounds, svg_path_to_pathops, to_cubic_path
from letrasiq.glyph import GlyphSource

Point = tuple[float, float]

# Letters whose leftmost stroke at the given height should measure the sheet's stem value.
LOWER_STEMS = "bhilmnpr"
CAP_STEMS = "BDEFHIKLPRT"
ROUND_LOWER = "aceosq"
ROUND_CAPS = "CGOQS"
FLAT_LOWER = "vwxz"
FLAT_CAPS = "EFHILTZ"

STEM_TOLERANCE = 8.0
MONO_STEM_TOLERANCE = 0.2
KINK_MIN_DEG, KINK_MAX_DEG = 4.0, 15.0
TINY_SEGMENT = 3.0
MIN_SELF_GAP = 34.0
MIN_KINK_HANDLE = 20.0


def _contours(path: pathops.Path) -> list[list[tuple]]:
    contours: list[list[tuple]] = []
    cur: list[tuple] = []
    last: Point | None = None
    start: Point | None = None
    for verb, pts in to_cubic_path(path).segments:
        if verb == "moveTo":
            cur, last, start = [], pts[0], pts[0]
        elif verb == "lineTo":
            cur.append(("l", last, pts[0]))
            last = pts[0]
        elif verb == "curveTo":
            cur.append(("c", (last, pts[0], pts[1], pts[2])))
            last = pts[2]
        elif verb == "closePath":
            if last != start:
                cur.append(("l", last, start))
            contours.append(cur)
    return contours


def _polyline(contour: list[tuple]) -> list[Point]:
    pts: list[Point] = []
    for s in contour:
        if s[0] == "l":
            pts.append(s[1])
        else:
            pts.extend(_bez(s[1], i / 16) for i in range(16))
    return pts


def stem_at(path: pathops.Path, y: float) -> float | None:
    """Width of the leftmost solid run where a horizontal line at y crosses the outline."""
    crossings: list[float] = []
    for contour in _contours(path):
        pts = _polyline(contour)
        for a, b in zip(pts, pts[1:] + pts[:1]):
            if (a[1] <= y) != (b[1] <= y):
                crossings.append(a[0] + (y - a[1]) / (b[1] - a[1]) * (b[0] - a[0]))
    crossings.sort()
    return crossings[1] - crossings[0] if len(crossings) >= 2 else None


def _outline_problems(name: str, path: pathops.Path) -> list[str]:
    missed_extreme = tiny = kinks = 0
    for contour in _contours(path):
        ends = []
        for s in contour:
            start, end = (s[1], s[2]) if s[0] == "l" else (s[1][0], s[1][3])
            if math.hypot(end[0] - start[0], end[1] - start[1]) < TINY_SEGMENT:
                tiny += 1
            if s[0] == "c":
                c = s[1]
                samples = [_bez(c, i / 24) for i in range(25)]
                for axis in (0, 1):
                    lo, hi = sorted((c[0][axis], c[3][axis]))
                    if max(p[axis] for p in samples) > hi + 1.5 or min(p[axis] for p in samples) < lo - 1.5:
                        missed_extreme += 1
                        break
            ends.append(s)
        for a, b in zip(ends, ends[1:] + ends[:1]):
            if a[0] != "c" or b[0] != "c":
                continue
            ax, ay = a[1][3][0] - a[1][2][0], a[1][3][1] - a[1][2][1]
            bx, by = b[1][1][0] - b[1][0][0], b[1][1][1] - b[1][0][1]
            la, lb = math.hypot(ax, ay), math.hypot(bx, by)
            if la < MIN_KINK_HANDLE or lb < MIN_KINK_HANDLE:
                continue
            angle = abs(math.degrees(math.atan2(ax * by - ay * bx, ax * bx + ay * by)))
            if KINK_MIN_DEG < angle < KINK_MAX_DEG:
                kinks += 1
    out = []
    if missed_extreme:
        out.append(f"{name}: {missed_extreme} curve(s) pass an extreme without a point")
    if tiny:
        out.append(f"{name}: {tiny} tiny segment(s)")
    if kinks:
        out.append(f"{name}: {kinks} slight kink(s) between curves")
    return out


def quality_warnings(sources: dict[str, GlyphSource], d: Design) -> list[str]:
    warnings: list[str] = []
    paths = {n: svg_path_to_pathops(s.path or "") for n, s in sources.items() if s.type == "drawn" and n != "space"}
    for name, path in paths.items():
        warnings.extend(_outline_problems(name, path))

    # Serif tips and rounds that nearly touch show up first in doubled letters.
    if not d.advance:
        for ch in "HnoO":
            if ch in paths and sources[ch].width:
                x0, _, x1, _ = path_bounds(paths[ch])
                gap = sources[ch].width - x1 + x0
                if gap < MIN_SELF_GAP:
                    warnings.append(f"{ch}: only {gap:.0f} units between {ch}{ch}, which risks touching in text")

    def stems(letters: str, y: float, target: float, label: str) -> None:
        for ch in letters:
            if ch not in paths:
                continue
            width = stem_at(paths[ch], y)
            # Monospace letters like m are lighter on purpose, to fit their cell.
            tolerance = target * MONO_STEM_TOLERANCE if d.advance else STEM_TOLERANCE
            if width is not None and abs(width - target) > tolerance:
                warnings.append(f"{ch}: {label} stem {width:.0f} differs from sheet value {target:g}")

    stems(LOWER_STEMS, d.xh * 0.3, d.V, "lowercase")
    stems(CAP_STEMS, d.cap * 0.25, d.CV, "capital")

    def zones(letters: str, height: float, rounded: bool) -> None:
        for ch in letters:
            bounds = path_bounds(paths[ch]) if ch in paths else None
            if bounds is None:
                continue
            _, y0, _, y1 = bounds
            if rounded:
                if not height < y1 <= height + d.os + 6:
                    warnings.append(f"{ch}: top {y1:.0f} has wrong overshoot above {height:g}")
                # Descending letters have no overshoot to check at the baseline.
                if ch not in "gqQ" and not -d.os - 6 <= y0 < 0:
                    warnings.append(f"{ch}: bottom {y0:.0f} has wrong overshoot below the baseline")
            else:
                if abs(y1 - height) > 0.5:
                    warnings.append(f"{ch}: top {y1:.0f} should sit exactly on {height:g}")
                if abs(y0) > 0.5:
                    warnings.append(f"{ch}: bottom {y0:.0f} should sit exactly on the baseline")

    zones(ROUND_LOWER, d.xh, True)
    zones(ROUND_CAPS, d.cap, True)
    zones(FLAT_LOWER, d.xh, False)
    zones(FLAT_CAPS, d.cap, False)
    return warnings
