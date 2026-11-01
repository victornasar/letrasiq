"""Shared drawing library: spines + a nib model become true cubic outlines.

Each font's ``draw.py`` defines ``draw(d: Design) -> Drawing`` using these parts.
Values come from the font's design sheet (``design.json``) and ``spec.json``.
"""

from __future__ import annotations

import importlib.util
import json
import math
from dataclasses import dataclass, field
from pathlib import Path

import pathops

from letrasiq.expand import to_cubic_path
from letrasiq.glyph import GlyphSource, glyph_filename
from letrasiq.spec import FontSpec

Point = tuple[float, float]
Cubic = tuple[Point, Point, Point, Point]


@dataclass
class Design:
    """Numbers a font is drawn from: metrics from the spec, the rest from its sheet."""

    xh: float
    cap: float
    asc: float
    desc: float
    V: float
    H: float
    CV: float
    CH: float
    stress: float
    os: float
    fig: float
    join: float = 0.5
    tension: float = 1.0
    space: int = 240
    kern_gap: float = 60.0
    serif_t: float = 18.0
    serif_len: float = 60.0
    spacing: dict[str, float] = field(default_factory=dict)
    brief: str = ""
    why: dict[str, str] = field(default_factory=dict)
    samples: dict[str, str] = field(default_factory=dict)

    @property
    def T(self) -> float:
        """Lowercase top spine, including overshoot."""
        return self.xh + self.os - self.H / 2

    @property
    def B(self) -> float:
        return -self.os + self.H / 2

    @property
    def CT(self) -> float:
        """Capital top spine, including overshoot."""
        return self.cap + self.os - self.CH / 2

    @property
    def CB(self) -> float:
        return -self.os + self.CH / 2

    @classmethod
    def load(cls, font_dir: Path, spec: FontSpec) -> Design:
        sheet = json.loads((font_dir / "design.json").read_text(encoding="utf-8"))
        v = sheet["values"]
        return cls(
            xh=spec.x_height,
            cap=spec.cap_height,
            asc=spec.ascender,
            desc=spec.descender,
            V=v["stem"],
            H=v["thin"],
            CV=v["cap_stem"],
            CH=v["cap_thin"],
            stress=v["stress_deg"],
            os=v["overshoot"],
            fig=v["figure_height"],
            join=v.get("join", 0.5),
            tension=v.get("tension", 1.0),
            space=v.get("space", 240),
            kern_gap=v.get("kern_gap", 60),
            serif_t=v.get("serif_thickness", 18),
            serif_len=v.get("serif_length", 60),
            spacing=sheet.get("spacing", {}),
            brief=sheet.get("brief", ""),
            why=sheet.get("why", {}),
            samples=sheet.get("samples", {}),
        )


def _velocity(a: float, b: float) -> float:
    sa, ca, sb, cb = math.sin(a), math.cos(a), math.sin(b), math.cos(b)
    num = 2 + math.sqrt(2) * (sa - sb / 16) * (sb - sa / 16) * (ca - cb)
    den = 3 * (1 + 0.5 * (math.sqrt(5) - 1) * ca + 0.5 * (3 - math.sqrt(5)) * cb)
    return num / den


def _wrap(a: float) -> float:
    while a > math.pi:
        a -= 2 * math.pi
    while a < -math.pi:
        a += 2 * math.pi
    return a


def hobby(p0: Point, d0: float, p1: Point, d1: float, tension: float = 1.0) -> Cubic:
    """Cubic from p0 to p1 with given directions (degrees), using Hobby's velocities."""
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    length = math.hypot(dx, dy)
    chord = math.atan2(dy, dx)
    a0, a1 = math.radians(d0), math.radians(d1)
    r = _velocity(_wrap(a0 - chord), _wrap(chord - a1))
    s = _velocity(_wrap(chord - a1), _wrap(a0 - chord))
    return (
        p0,
        (p0[0] + math.cos(a0) * r * length / tension, p0[1] + math.sin(a0) * r * length / tension),
        (p1[0] - math.cos(a1) * s * length / tension, p1[1] - math.sin(a1) * s * length / tension),
        p1,
    )


def _bez(c: Cubic, t: float) -> Point:
    u = 1 - t
    a, b, d, e = u**3, 3 * u * u * t, 3 * u * t * t, t**3
    return (
        a * c[0][0] + b * c[1][0] + d * c[2][0] + e * c[3][0],
        a * c[0][1] + b * c[1][1] + d * c[2][1] + e * c[3][1],
    )


def _dbez(c: Cubic, t: float) -> Point:
    u = 1 - t
    a, b, d = 3 * u * u, 6 * u * t, 3 * t * t
    return (
        a * (c[1][0] - c[0][0]) + b * (c[2][0] - c[1][0]) + d * (c[3][0] - c[2][0]),
        a * (c[1][1] - c[0][1]) + b * (c[2][1] - c[1][1]) + d * (c[3][1] - c[2][1]),
    )


def _ddbez(c: Cubic, t: float) -> Point:
    u = 1 - t
    return (
        6 * u * (c[2][0] - 2 * c[1][0] + c[0][0]) + 6 * t * (c[3][0] - 2 * c[2][0] + c[1][0]),
        6 * u * (c[2][1] - 2 * c[1][1] + c[0][1]) + 6 * t * (c[3][1] - 2 * c[2][1] + c[1][1]),
    )


def _unit(v: Point) -> Point:
    length = math.hypot(*v) or 1.0
    return v[0] / length, v[1] / length


def _solve(pts: list[Point], us: list[float], t0: Point, t1: Point, total: float) -> Cubic:
    """Least-squares handle lengths for a cubic with fixed end tangents."""
    p0, p3 = pts[0], pts[-1]
    c00 = c01 = c11 = x0 = x1 = 0.0
    for u, p in zip(us, pts):
        b0, b1, b2, b3 = (1 - u) ** 3, 3 * u * (1 - u) ** 2, 3 * u * u * (1 - u), u**3
        a0 = (t0[0] * b1, t0[1] * b1)
        a1 = (t1[0] * b2, t1[1] * b2)
        c00 += a0[0] ** 2 + a0[1] ** 2
        c01 += a0[0] * a1[0] + a0[1] * a1[1]
        c11 += a1[0] ** 2 + a1[1] ** 2
        tx = p[0] - (p0[0] * (b0 + b1) + p3[0] * (b2 + b3))
        ty = p[1] - (p0[1] * (b0 + b1) + p3[1] * (b2 + b3))
        x0 += a0[0] * tx + a0[1] * ty
        x1 += a1[0] * tx + a1[1] * ty
    det = c00 * c11 - c01 * c01
    if abs(det) < 1e-9:
        al = ar = total / 3
    else:
        al = (x0 * c11 - x1 * c01) / det
        ar = (c00 * x1 - c01 * x0) / det
    if al < total * 0.02 or ar < total * 0.02:
        al = ar = total / 3
    return (
        p0,
        (p0[0] + t0[0] * al, p0[1] + t0[1] * al),
        (p3[0] + t1[0] * ar, p3[1] + t1[1] * ar),
        p3,
    )


def _reparam(c: Cubic, pts: list[Point], us: list[float]) -> list[float]:
    """One Newton step moving each parameter toward its closest curve point."""
    out = []
    for u, p in zip(us, pts):
        q, d1, d2 = _bez(c, u), _dbez(c, u), _ddbez(c, u)
        rx, ry = q[0] - p[0], q[1] - p[1]
        den = d1[0] ** 2 + d1[1] ** 2 + rx * d2[0] + ry * d2[1]
        nu = u - (rx * d1[0] + ry * d1[1]) / den if abs(den) > 1e-9 else u
        out.append(min(1.0, max(0.0, nu)))
    out[0], out[-1] = 0.0, 1.0
    return out


def _fit(pts: list[Point], t0: Point, t1: Point, tol: float = 1.0, depth: int = 0) -> list[Cubic]:
    """Fit cubics to sampled points, splitting only when the fit stays over tolerance."""
    n = len(pts)
    ds = [0.0]
    for i in range(1, n):
        ds.append(ds[-1] + math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]))
    total = ds[-1] or 1.0
    us = [v / total for v in ds]
    c = _solve(pts, us, t0, t1, total)
    worst, wi = 0.0, n // 2
    for _ in range(5):
        worst, wi = 0.0, n // 2
        for i, (u, p) in enumerate(zip(us, pts)):
            q = _bez(c, u)
            e = math.hypot(q[0] - p[0], q[1] - p[1])
            if e > worst:
                worst, wi = e, i
        if worst <= tol:
            return [c]
        us = _reparam(c, pts, us)
        c = _solve(pts, us, t0, t1, total)
    if depth > 3 or n < 8:
        return [c]
    wi = min(max(wi, 3), n - 4)
    mid = _unit((pts[wi + 1][0] - pts[wi - 1][0], pts[wi + 1][1] - pts[wi - 1][1]))
    return _fit(pts[: wi + 1], t0, (-mid[0], -mid[1]), tol, depth + 1) + _fit(
        pts[wi:], mid, t1, tol, depth + 1
    )


def _fit_side(runs: list[list[Point]], closed: bool) -> list[Cubic]:
    """Fit one side of a stroke, sharing one tangent where neighbouring runs meet."""
    starts = [_unit((r[1][0] - r[0][0], r[1][1] - r[0][1])) for r in runs]
    ends = [_unit((r[-1][0] - r[-2][0], r[-1][1] - r[-2][1])) for r in runs]
    count = len(runs)
    out: list[Cubic] = []
    for i, run in enumerate(runs):
        t0 = starts[i]
        if i > 0 or closed:
            t0 = _unit((ends[i - 1][0] + starts[i][0], ends[i - 1][1] + starts[i][1]))
        t1 = ends[i]
        if i < count - 1 or closed:
            nxt = starts[(i + 1) % count]
            t1 = _unit((ends[i][0] + nxt[0], ends[i][1] + nxt[1]))
        out.extend(_fit(run, t0, (-t1[0], -t1[1])))
    return out


def stroke(
    d: Design,
    nodes: list[tuple],
    closed: bool = False,
    v: float | None = None,
    h: float | None = None,
    tension: float | None = None,
) -> pathops.Path:
    """Outline a spine. Nodes are (x, y, direction_deg[, width_scale]).

    Thickness follows direction (v when travelling vertically, h when horizontally,
    with the axis tilted by ``d.stress``). Place nodes at the spine's extremes.
    """
    v = d.V if v is None else v
    h = d.H if h is None else h
    tn = d.tension if tension is None else tension
    ns = [(n[0], n[1], n[2], n[3] if len(n) > 3 else 1.0) for n in nodes]
    if closed:
        ns = ns + [ns[0]]
    left_samples: list[list[Point]] = []
    right_samples: list[list[Point]] = []
    phi = math.radians(d.stress)
    for a, b in zip(ns, ns[1:]):
        c = hobby(a[:2], a[2], b[:2], b[2], tn)
        lp, rp = [], []
        samples = 40
        for i in range(samples + 1):
            t = i / samples
            p, dv = _bez(c, t), _dbez(c, t)
            if math.hypot(*dv) < 1e-6:
                dv = _dbez(c, min(max(t, 0.01), 0.99))
            ux, uy = _unit(dv)
            th = math.atan2(uy, ux) - phi
            w = math.hypot(v * math.sin(th), h * math.cos(th))
            w *= a[3] + (b[3] - a[3]) * (t * t * (3 - 2 * t))
            lp.append((p[0] - uy * w / 2, p[1] + ux * w / 2))
            rp.append((p[0] + uy * w / 2, p[1] - ux * w / 2))
        left_samples.append(lp)
        right_samples.append(rp)
    left = _fit_side(left_samples, closed)
    right = _fit_side(right_samples, closed)
    path = pathops.Path()
    pen = path.getPen()
    if closed:
        for side, rev in ((left, False), (right, True)):
            segs = [(s[3], s[2], s[1], s[0]) for s in reversed(side)] if rev else side
            pen.moveTo(segs[0][0])
            for s in segs:
                pen.curveTo(s[1], s[2], s[3])
            pen.closePath()
        return path
    pen.moveTo(left[0][0])
    for s in left:
        pen.curveTo(s[1], s[2], s[3])
    pen.lineTo(right[-1][3])
    for s in reversed(right):
        pen.curveTo(s[2], s[1], s[0])
    pen.closePath()
    return path


def poly(*pts: Point) -> pathops.Path:
    p = pathops.Path()
    pen = p.getPen()
    pen.moveTo(pts[0])
    for q in pts[1:]:
        pen.lineTo(q)
    pen.closePath()
    return p


def rect(x0: float, y0: float, x1: float, y1: float) -> pathops.Path:
    return poly((x0, y0), (x1, y0), (x1, y1), (x0, y1))


def diag(x0: float, y0: float, x1: float, y1: float, w0: float, w1: float | None = None) -> pathops.Path:
    """Straight diagonal with its left edge from (x0, y0) to (x1, y1) and horizontal widths."""
    w1 = w0 if w1 is None else w1
    return poly((x0, y0), (x0 + w0, y0), (x1 + w1, y1), (x1, y1))


def oval(cx: float, cy: float, rx: float, ry: float, k: float = 0.5523) -> pathops.Path:
    p = pathops.Path()
    pen = p.getPen()
    pen.moveTo((cx + rx, cy))
    pen.curveTo((cx + rx, cy + ry * k), (cx + rx * k, cy + ry), (cx, cy + ry))
    pen.curveTo((cx - rx * k, cy + ry), (cx - rx, cy + ry * k), (cx - rx, cy))
    pen.curveTo((cx - rx, cy - ry * k), (cx - rx * k, cy - ry), (cx, cy - ry))
    pen.curveTo((cx + rx * k, cy - ry), (cx + rx, cy - ry * k), (cx + rx, cy))
    pen.closePath()
    return p


def shape(start: Point, *segs: tuple) -> pathops.Path:
    """Free outline: segments are ('l', pt) or ('c', c1, c2, pt)."""
    p = pathops.Path()
    pen = p.getPen()
    pen.moveTo(start)
    for s in segs:
        if s[0] == "l":
            pen.lineTo(s[1])
        else:
            pen.curveTo(s[1], s[2], s[3])
    pen.closePath()
    return p


def foot(d: Design, x0: float, x1: float, y: float = 0.0, left: bool = True, right: bool = True) -> pathops.Path:
    """Bracketed serif under a stem spanning x0..x1 at height y."""
    t, length, br = d.serif_t, d.serif_len, 46
    lx = x0 - length if left else x0
    rx = x1 + length if right else x1
    segs: list[tuple] = [("l", (rx, y))]
    if right:
        segs += [
            ("l", (rx, y + t)),
            ("c", (x1 + length * 0.45, y + t + 2), (x1, y + t + 8), (x1, y + t + br)),
        ]
    else:
        segs += [("l", (x1, y + t + br))]
    segs += [("l", (x0, y + t + br))]
    if left:
        segs += [("c", (x0, y + t + 8), (x0 - length * 0.45, y + t + 2), (lx, y + t))]
    return shape((lx, y), *segs)


def head(d: Design, x0: float, x1: float, top: float) -> pathops.Path:
    """Sloped, bracketed lowercase head serif on the left of a stem."""
    length = d.serif_len + 8
    return shape(
        (x1, top),
        ("l", (x1, top - 90)),
        ("l", (x0, top - 90)),
        ("c", (x0, top - 62), (x0 - length * 0.4, top - 48), (x0 - length, top - 44)),
        ("l", (x0 - length, top - 28)),
        ("l", (x0 - 2, top + 4)),
    )


def union(*parts: pathops.Path) -> pathops.Path:
    """Merge parts one at a time so opposite winding can't cancel at overlaps."""
    out = pathops.Path()
    for p in parts:
        out = pathops.op(out, p, pathops.PathOp.UNION, fix_winding=True)
    return out


def _split(c: Cubic, t: float) -> tuple[Cubic, Cubic]:
    def lerp(a: Point, b: Point) -> Point:
        return a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t

    ab, bc, cd = lerp(c[0], c[1]), lerp(c[1], c[2]), lerp(c[2], c[3])
    abc, bcd = lerp(ab, bc), lerp(bc, cd)
    m = lerp(abc, bcd)
    return (c[0], ab, abc, m), (m, bcd, cd, c[3])


def _extrema(c: Cubic) -> list[float]:
    """Parameters where the curve passes a horizontal or vertical extreme."""
    ts: list[float] = []
    for i in (0, 1):
        a = -c[0][i] + 3 * c[1][i] - 3 * c[2][i] + c[3][i]
        b = 2 * (c[0][i] - 2 * c[1][i] + c[2][i])
        e = c[1][i] - c[0][i]
        if abs(a) < 1e-9:
            roots = [-e / b] if abs(b) > 1e-9 else []
        else:
            disc = b * b - 4 * a * e
            if disc < 0:
                continue
            s = math.sqrt(disc)
            roots = [(-b + s) / (2 * a), (-b - s) / (2 * a)]
        for t in roots:
            if 0.02 < t < 0.98:
                lo, hi = sorted((c[0][i], c[3][i]))
                if _bez(c, t)[i] > hi + 0.7 or _bez(c, t)[i] < lo - 0.7:
                    ts.append(t)
    return sorted(ts)


def _is_straight(c: Cubic) -> bool:
    dx, dy = c[3][0] - c[0][0], c[3][1] - c[0][1]
    length = math.hypot(dx, dy)
    if length < 1e-6:
        return True
    return all(abs((q[0] - c[0][0]) * dy - (q[1] - c[0][1]) * dx) / length < 0.4 for q in (c[1], c[2]))


def tidy(path: pathops.Path) -> pathops.Path:
    """Add points at extremes, drop tiny segments, turn flat curves into lines, round."""
    contours: list[tuple[Point, list[tuple]]] = []
    start: Point | None = None
    segs: list[tuple] = []
    last: Point | None = None
    for verb, pts in to_cubic_path(path).segments:
        if verb == "moveTo":
            start, segs, last = pts[0], [], pts[0]
        elif verb == "lineTo":
            segs.append(("l", last, pts[0]))
            last = pts[0]
        elif verb == "curveTo":
            segs.append(("c", (last, pts[0], pts[1], pts[2])))
            last = pts[2]
        elif verb == "closePath" and start is not None:
            if last != start and math.hypot(last[0] - start[0], last[1] - start[1]) > 1e-6:
                segs.append(("l", last, start))
            contours.append((start, segs))
            start = None

    out = pathops.Path()
    pen = out.getPen()

    def rnd(p: Point) -> tuple[int, int]:
        return round(p[0]), round(p[1])

    for start, segs in contours:
        pieces: list[tuple] = []
        for s in segs:
            if s[0] == "l":
                pieces.append(s)
                continue
            c = s[1]
            if _is_straight(c):
                pieces.append(("l", c[0], c[3]))
                continue
            rest, offset = c, 0.0
            for t in _extrema(c):
                a, rest = _split(rest, (t - offset) / (1 - offset))
                offset = t
                pieces.append(("c", a))
            pieces.append(("c", rest))

        def endpoint(s: tuple) -> Point:
            return s[2] if s[0] == "l" else s[1][3]

        def begin(s: tuple) -> Point:
            return s[1] if s[0] == "l" else s[1][0]

        kept = [s for s in pieces if math.hypot(endpoint(s)[0] - begin(s)[0], endpoint(s)[1] - begin(s)[1]) >= 2.5]
        if len(kept) < 2:
            continue
        origin = begin(kept[0])
        pen.moveTo(rnd(origin))
        for i, s in enumerate(kept):
            # Each segment ends where the next begins, closing gaps left by dropped tiny ones.
            nxt = begin(kept[i + 1]) if i + 1 < len(kept) else origin
            if s[0] == "l":
                if i + 1 < len(kept):
                    pen.lineTo(rnd(nxt))
            else:
                pen.curveTo(rnd(s[1][1]), rnd(s[1][2]), rnd(nxt))
        pen.closePath()
    return out


@dataclass
class Placed:
    path: pathops.Path
    width: int


class Drawing:
    """Collects a font's glyphs and places each one using the sheet's spacing values."""

    def __init__(self, d: Design) -> None:
        self.d = d
        self.glyphs: dict[str, Placed] = {"space": Placed(pathops.Path(), d.space)}

    def _sb(self, v: float | str) -> float:
        return self.d.spacing[v] if isinstance(v, str) else float(v)

    def add(
        self,
        name: str,
        parts: list[pathops.Path],
        sb: tuple[float | str, float | str] = (40, 40),
        advance: int | None = None,
    ) -> None:
        """Add a glyph. ``advance`` fixes the width and centres the outline in it."""
        path = union(*parts)
        x0, _, x1, _ = path.bounds
        if advance is None:
            left = self._sb(sb[0])
            width = round(x1 - x0 + left + self._sb(sb[1]))
        else:
            left = (advance - (x1 - x0)) / 2
            width = advance
        self.glyphs[name] = Placed(tidy(path.transform(1, 0, 0, 1, left - x0, 0)), width)


def path_to_svg(path: pathops.Path) -> str:
    out: list[str] = []
    for verb, pts in path.segments:
        if verb == "moveTo":
            out.append(f"M{pts[0][0]:g} {pts[0][1]:g}")
        elif verb == "lineTo":
            out.append(f"L{pts[0][0]:g} {pts[0][1]:g}")
        elif verb == "curveTo":
            out.append("C" + " ".join(f"{p[0]:g} {p[1]:g}" for p in pts))
        elif verb == "closePath":
            out.append("Z")
    return "".join(out)


def load_design(font_dir: Path, spec: FontSpec | None = None) -> Design:
    return Design.load(font_dir, spec or FontSpec.load(font_dir / "spec.json"))


def regenerate_drawn(font_dir: Path, spec: FontSpec, locked: set[str]) -> int:
    """Run a font's draw.py and rewrite glyphs/*.json, leaving locked glyphs alone."""
    module_spec = importlib.util.spec_from_file_location(
        f"letrasiq_draw_{font_dir.name.replace('-', '_')}", font_dir / "draw.py"
    )
    if module_spec is None or module_spec.loader is None:
        raise ImportError(f"cannot load {font_dir / 'draw.py'}")
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    drawing: Drawing = module.draw(load_design(font_dir, spec))
    count = 0
    (font_dir / "glyphs").mkdir(exist_ok=True)
    for name, placed in drawing.glyphs.items():
        if name in locked:
            continue
        source = GlyphSource(name=name, type="drawn", path=path_to_svg(placed.path), width=placed.width)
        source.save(font_dir / "glyphs" / glyph_filename(name))
        count += 1
    return count
