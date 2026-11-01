"""Construction of the printable ASCII set from a design sheet.

Every font starts here: ``draw_latin(d)`` builds all glyphs from the sheet's values and style.
A font's ``draw.py`` replaces only what should differ from this default construction.
"""

from __future__ import annotations

import math
from dataclasses import replace

import pathops

from letrasiq.drawing import Design, Drawing, diag, foot, head, oval, poly, rect, shape, stroke


class Kit:
    """Parts that change with the sheet's style, so recipes stay the same across styles."""

    def __init__(self, d: Design) -> None:
        self.d = d
        self.serif = d.serifs != "none"
        self.ball_terminals = d.terminals == "ball"

    def lstem(self, x: float, top: float, bottom: float = 0.0, top_serif: bool = True, foot_serif: bool = True) -> list[pathops.Path]:
        """Lowercase stem: a pen-cut top on sans, a head and foot on serif."""
        d = self.d
        if not self.serif:
            return [poly((x, bottom), (x + d.V, bottom), (x + d.V, top), (x, top - 14))]
        parts = [rect(x, bottom, x + d.V, top)]
        if top_serif:
            parts.append(head(d, x, x + d.V, top))
        if foot_serif:
            parts.append(foot(d, x, x + d.V, bottom))
        return parts

    def cstem(self, x: float, top_serif: bool = True, foot_serif: bool = True, v: float | None = None) -> list[pathops.Path]:
        d = self.d
        v = d.CV if v is None else v
        parts = [rect(x, 0, x + v, d.cap)]
        if self.serif and foot_serif:
            parts.append(foot(d, x, x + v))
        if self.serif and top_serif:
            parts.append(foot(d, x, x + v).transform(1, 0, 0, -1, 0, d.cap))
        return parts

    def feet(self, *xs: float) -> list[pathops.Path]:
        """Serif feet under lowercase stems whose left edges are at xs."""
        return [foot(self.d, x, x + self.d.V) for x in xs] if self.serif else []

    def slab(self, x0: float, x1: float, y: float, overhang: float = 44.0) -> list[pathops.Path]:
        """Plain serif across a diagonal's end; y is the outer edge, inward is toward mid-height."""
        if not self.serif:
            return []
        t = self.d.serif_t
        y1 = y + t if y < self.d.xh * 0.5 else y - t
        return [rect(x0 - overhang, min(y, y1), x1 + overhang, max(y, y1))]

    def beak(self, x: float, y: float, h: float, length: float = 74.0, flip_x: bool = False, flip_y: bool = False) -> list[pathops.Path]:
        """Vertical serif on an arm's end, hanging from an outer edge at height y."""
        if not self.serif:
            return []
        t = self.d.CH
        p = shape((0, 0), ("l", (0, -h)), ("l", (-13, -h)), ("c", (-20, -h * 0.45), (-length * 0.45, -t - 3), (-length, -t)), ("l", (-length, 0)))
        sx, sy = (-1 if flip_x else 1), (-1 if flip_y else 1)
        return [p.transform(sx, 0, 0, sy, x, y)]

    def spur(self, x: float, y0: float, y1: float, width: float = 34.0, left: bool = False) -> list[pathops.Path]:
        """Upright wedge at a curve's open end (C, G, S, s). x is its outer edge."""
        if not self.serif:
            return []
        if left:
            return [poly((x + width, y0), (x, y0), (x - 3, y1), (x + 10, y1))]
        return [poly((x - width, y0), (x, y0), (x + 3, y1), (x - 10, y1))]

    def ball(self, x: float, y: float, r: float) -> list[pathops.Path]:
        return [oval(x, y, r, r)] if self.ball_terminals else []


# Letter groups whose widths move together, as designers think of them.
WIDTH_GROUPS = {
    "round_lower": "abcdegopq",
    "arch_lower": "hmnu",
    "narrow_lower": "s",
    "diagonal_lower": "kvwxyz",
    "round_caps": "CDGOQ",
    "narrow_caps": "BEFLPRS",
    "wide_caps": "AHKMNTUVWXYZ",
}

# o_ratio and O_ratio set round letters by shape: width over height, with 1.0 a circle.
# The other values scale a group's width, with 1.0 leaving it alone.
PROPORTIONS = {
    "humanist": {},
    "geometric": {"o_ratio": 1.0, "O_ratio": 1.0, "narrow_caps": 0.8, "wide_caps": 0.94, "narrow_lower": 0.92},
    "even": {"o_ratio": 0.84, "O_ratio": 0.84, "narrow_caps": 1.04, "wide_caps": 0.9, "arch_lower": 0.96, "diagonal_lower": 0.96},
}


def _width_scales(d: Design, base: Drawing) -> dict[str, float]:
    """Width scale for each letter, from the sheet's proportions preset plus any overrides."""
    settings = {**PROPORTIONS[d.shape.get("proportions", "humanist")], **d.shape.get("widths", {})}
    scales: dict[str, float] = {}
    for group, letters in WIDTH_GROUPS.items():
        scale = settings.get(group, 1.0)
        ratio = settings.get({"round_lower": "o_ratio", "round_caps": "O_ratio"}.get(group, ""))
        if ratio is not None:
            x0, y0, x1, y1 = base.glyphs["o" if group == "round_lower" else "O"].path.bounds
            scale = ratio * (y1 - y0) / (x1 - x0)
        for letter in letters:
            scales[letter] = scale
    return scales


def draw_latin(d: Design) -> Drawing:
    """All glyphs at the sheet's proportions, with stems redrawn so they keep their weight."""
    base = construct(d)
    out = Drawing(d)
    out.glyphs = dict(base.glyphs)
    redrawn: dict[float, Drawing] = {}
    for name, scale in _width_scales(d, base).items():
        scale = round(scale, 3)
        if scale == 1.0:
            continue
        if scale not in redrawn:
            redrawn[scale] = construct(replace(d, V=d.V / scale, CV=d.CV / scale))
        out.add(name, [redrawn[scale].glyphs[name].path.transform(scale, 0, 0, 1, 0, 0)])
    return out


def construct(d: Design) -> Drawing:
    """Every glyph at the recipes' own proportions."""
    f = Drawing(d)
    k = Kit(d)
    closed = d.shape.get("aperture", "open") == "closed"
    square_dots = d.shape.get("dots", "round") == "square"

    def round_dot(x: float, y: float, r: float) -> pathops.Path:
        return rect(x - r, y - r, x + r, y + r) if square_dots else oval(x, y, r, r)

    S = k.serif
    V, H, CV, CH = d.V, d.H, d.CV, d.CH
    xh, cap, asc, desc, fig = d.xh, d.cap, d.asc, d.desc, d.fig
    T, B, CT, CB = d.T, d.B, d.CT, d.CB
    cy = (T + B) / 2
    ccy = cap / 2
    low = desc + d.os + H / 2
    # Recipes were first drawn at x-height 520 and cap height 710; absolute heights scale with the metrics.
    Y = xh / 520
    C = cap / 710
    L = d.serif_len

    # Diagonal weights: the sans values below, or the sheet's contrast on serif faces.
    def cap_thick(v: float) -> float:
        return v if not S else CV * 1.06

    def cap_thin(v: float) -> float:
        return v if not S else CH * 1.2

    def lc_thick(v: float) -> float:
        return v if not S else V * 1.04

    def lc_thin(v: float) -> float:
        return v if not S else H * 1.2

    def cs(nodes, **kw):
        kw.setdefault("v", CV)
        kw.setdefault("h", CH)
        return stroke(d, nodes, **kw)

    def arch(xl, xr, apex):
        """Shoulder from a stem's right edge into a right stem centred on xr."""
        return stroke(d, [(xl + V - 14, xh - 118 * Y, 66, d.join), (apex, T, 0), (xr, xh - 190 * Y, 270), (xr, 0, 270)])

    def bowl_right(R, xs=0.0):
        """Bowl closing against a stem on its left (b, p)."""
        apex = xs + (R - xs) * 0.56
        return stroke(d, [(xs + V - 14, xh - 125 * Y, 62, d.join), (apex, T, 0), (R, cy, 270), (apex, B, 180),
                          (xs + V - 14, 110 * Y, 118, d.join)])

    def bowl_left(xs):
        """Bowl closing against a stem on its right (d, q)."""
        apex = V / 2 + (xs + 14 - V / 2) * 0.54
        return stroke(d, [(xs + 14, xh - 125 * Y, 118, d.join), (apex, T, 180), (V / 2, cy, 270), (apex, B, 0),
                          (xs + 14, 110 * Y, 62, d.join)])

    # ---- Capitals -----------------------------------------------------------------------------
    W = 660
    wl, wr, apex = cap_thin(CV * 0.86), cap_thick(CV * 1.04), 110 if not S else 62
    lx0, rx0 = W / 2 - apex / 2, W / 2 + apex / 2 - wr

    def a_x(y):
        return (lx0 * y / cap + wl / 2, (W - wr) + (rx0 - (W - wr)) * y / cap + wr / 2)

    bar_y = 205 * C
    f.add("A", [diag(0, 0, lx0, cap, wl), diag(W - wr, 0, rx0, cap, wr),
                rect(a_x(bar_y)[0], bar_y, a_x(bar_y)[1], bar_y + CH * 0.92),
                *k.slab(0, wl, 0), *k.slab(W - wr, W, 0)])

    top_b, bot_b, my = cap - CH / 2, CH / 2, cap * 0.53
    f.add("B", [*k.cstem(0),
                cs([(CV - 5, top_b, 0), (245, top_b, 0), (385, (top_b + my) / 2, 270), (235, my, 180), (CV - 5, my, 180)]),
                cs([(CV - 5, my, 0), (262, my, 0), (425, (my + bot_b) / 2, 270), (252, bot_b, 180), (CV - 5, bot_b, 180)])])
    c_top = [*k.spur(580, cap * 0.68, cap + d.os - 4)]
    # Closed apertures end their curves pointing back toward the letter's centre.
    round_cap_top = (578, cap * 0.72, 112, 0.86) if closed else (562, cap * 0.8, 142, 0.82)
    f.add("C", [cs([round_cap_top, (345, CT, 180), (CV / 2, ccy, 270), (345, CB, 0),
                    (586, cap * 0.25, 68, 0.86) if closed else (574, cap * 0.17, 38, 0.82)]), *c_top])
    f.add("D", [*k.cstem(0),
                cs([(CV - 5, top_b, 0), (262, top_b, 0), (590, ccy, 270), (262, bot_b, 180), (CV - 5, bot_b, 180)])])
    f.add("E", [*k.cstem(0), rect(0, cap - CH, 432, cap), rect(0, my - CH * 0.46, 385, my + CH * 0.46), rect(0, 0, 446, CH),
                *k.beak(446, cap, 150), *k.beak(460, 0, 170, flip_y=True)])
    f.add("F", [*k.cstem(0), rect(0, cap - CH, 420, cap), rect(0, cap * 0.51 - CH * 0.46, 372, cap * 0.51 + CH * 0.46),
                *k.beak(434, cap, 150)])
    g_stem = [rect(525, 105 * C, 525 + CV, 335 * C)]
    f.add("G", [cs([round_cap_top, (345, CT, 180), (CV / 2, ccy, 270), (345, CB, 0), (574, 118 * C, 72, 0.84)]),
                *g_stem, rect(392, 335 * C - CH * 0.92, 525 + CV, 335 * C), *c_top])
    f.add("H", [*k.cstem(0), *k.cstem(502), rect(CV - 5, my - CH * 0.46, 507, my + CH * 0.46)])
    f.add("I", k.cstem(0))
    f.add("J", [cs([(215, cap, 270), (215, 175 * C, 270), (90, CB, 180), (-22, 92 * C, 145, 0.82)]),
                *k.ball(0, 74 * C, 46), *([foot(d, 215 - CV / 2, 215 + CV / 2).transform(1, 0, 0, -1, 0, cap)] if S else [])])
    arm_t = cap_thin(106)
    if S:
        arm = poly((90, 262 * C), (432 + arm_t, cap), (432, cap), (90, 314 * C))
        leg = poly((440, 0), (440 + cap_thick(114), 0), (245, 449 * C), (185, 383 * C))
    else:
        arm = poly((90, 190 * C), (538, cap), (432, cap), (90, 314 * C))
        leg = poly((440, 0), (554, 0), (278, 408 * C), (169, 400 * C))
    f.add("K", [*k.cstem(0), arm, leg, *k.slab(432, 432 + arm_t, cap), *k.slab(440, 440 + cap_thick(114), 0)])
    f.add("L", [*k.cstem(0), rect(0, 0, 432, CH), *k.beak(446, 0, 170, flip_y=True)])
    m_t = CV * 0.9 if not S else CH * 1.3
    f.add("M", [*k.cstem(0, v=m_t), *k.cstem(668, v=CV * 0.9 if not S else CV),
                diag(328, 0, 0, cap, cap_thick(102)), diag(344, 0, 675, cap, cap_thin(82))])
    n_t = CV * 0.88 if not S else CH * 1.3
    f.add("N", [*k.cstem(0, v=n_t), *k.cstem(516, v=n_t),
                diag(490, 0, 0, cap, cap_thick(112))])

    def big_o(r=302):
        return cs([(CV / 2 + r, CB, 0), (CV / 2 + 2 * r, ccy, 90), (CV / 2 + r, CT, 180), (CV / 2, ccy, 270)], closed=True)

    f.add("O", [big_o()])
    pm = cap * 0.42
    f.add("P", [*k.cstem(0),
                cs([(CV - 5, top_b, 0), (268, top_b, 0), (440, (top_b + pm) / 2, 270), (258, pm, 180), (CV - 5, pm, 180)])])
    f.add("Q", [big_o(), poly((372, 170 * C), (468, 170 * C), (690, -82), (586, -82))])
    rm = cap * 0.46
    f.add("R", [*k.cstem(0),
                cs([(CV - 5, top_b, 0), (258, top_b, 0), (425, (top_b + rm) / 2, 270), (248, rm, 180), (CV - 5, rm, 180)]),
                diag(432, 0, 198, rm + 18, cap_thick(112)), *k.slab(432, 432 + cap_thick(112), 0)])
    f.add("S", [cs([(440, cap * 0.74, 112, 0.84) if closed else (428, cap * 0.82, 148, 0.8), (236, CT, 180), (52, cap * 0.74, 270),
                    (232, ccy + 6, 335), (418, cap * 0.25, 270), (210, CB, 180),
                    (-4, cap * 0.26, 112, 0.84) if closed else (6, cap * 0.17, 152, 0.8)], v=CV * 0.96),
                *k.spur(446, cap * 0.7, cap + d.os - 4), *k.spur(-12, cap * 0.3, -d.os + 4, 42, left=True)])
    f.add("T", [*k.cstem(228, top_serif=False), rect(0, cap - CH, 228 * 2 + CV, cap),
                *k.beak(228 * 2 + CV, cap, 170), *k.beak(0, cap, 170, flip_x=True)])
    u_r = 551 if not S else 560
    u_scale = 1.0 if not S else 0.46  # the right side of U is the thin stroke on contrasted faces
    u_half = CV * u_scale / 2
    f.add("U", [cs([(CV / 2, cap, 270), (CV / 2, 235 * C, 270), (300, CB, 0), (u_r, 235 * C, 90, u_scale), (u_r, cap, 90, u_scale)]),
                *([foot(d, 0, CV).transform(1, 0, 0, -1, 0, cap), foot(d, u_r - u_half, u_r + u_half).transform(1, 0, 0, -1, 0, cap)] if S else [])])
    f.add("V", [diag(268, 0, 0, cap, cap_thick(102), cap_thick(106)), diag(280, 0, 562, cap, cap_thin(84)),
                *k.slab(0, cap_thick(106), cap), *k.slab(562, 562 + cap_thin(84), cap)])
    f.add("W", [diag(195, 0, 0, cap, cap_thick(100), cap_thick(104)), diag(210, 0, 400, cap, cap_thin(82)),
                diag(615, 0, 408, cap, cap_thick(100), cap_thick(104)), diag(628, 0, 835, cap, cap_thin(82)),
                *k.slab(0, cap_thick(104), cap), *k.slab(408, 408 + cap_thick(104), cap, 30), *k.slab(835, 835 + cap_thin(82), cap)])
    f.add("X", [diag(478, 0, 6, cap, cap_thick(112)), diag(0, 0, 472, cap, cap_thin(92)),
                *k.slab(6, 6 + cap_thick(112), cap), *k.slab(472, 472 + cap_thin(92), cap),
                *k.slab(0, cap_thin(92), 0), *k.slab(478, 478 + cap_thick(112), 0)])
    y_join = 300 * C
    f.add("Y", [rect(246, 0, 246 + CV, y_join), diag(246, y_join - 15, 0, cap, CV, cap_thick(106)), diag(262, y_join - 15, 512, cap, cap_thin(82)),
                *k.slab(0, cap_thick(106), cap), *k.slab(512, 512 + cap_thin(82), cap),
                *([foot(d, 246, 246 + CV)] if S else [])])
    z_w = 120 if not S else CV * 1.1
    f.add("Z", [rect(22, cap - CH, 508, cap), rect(0, 0, 520, CH), diag(0, 28 if not S else CH, 508 - z_w, cap - 28 if not S else cap - CH, z_w),
                *k.beak(22, cap, 130, flip_x=True), *k.beak(520, 0, 150, flip_y=True)])

    # ---- Lowercase ----------------------------------------------------------------------------
    ax = 330
    if d.shape.get("a") == "single":
        f.add("a", [*k.lstem(368, xh, top_serif=False, foot_serif=False), bowl_left(368),
                    *([foot(d, 368, 368 + V, left=False)] if S else [])])
    else:
        f.add("a", [stroke(d, [(ax, 0, 90), (ax, xh - 165 * Y, 90), (178, T, 180), (10, xh * 0.71, 250, 0.8) if closed else (22, xh * 0.79, 216, 0.74)]),
                    stroke(d, [(ax + 10, xh * 0.56, 186, 0.6), (146, xh * 0.5, 188, 0.95), (0, xh * 0.24, 270), (118, B, 0),
                               (ax + 10, xh * 0.17, 62, d.join)]),
                    *k.ball(58, xh * 0.78, 48),
                    *([poly((ax + V / 2 - 1, 0), (ax + V / 2 + 58, 0), (ax + V / 2 + 58, 14), (ax + V / 2 - 1, 42))] if S else [])])
    f.add("b", [*k.lstem(0, asc, foot_serif=False), bowl_right(412)])
    f.add("c", [stroke(d, [(372, xh * 0.71, 112, 0.84) if closed else (362, xh * 0.81, 140, 0.76), (206, T, 180), (0, cy, 270), (212, B, 0),
                           (378, xh * 0.27, 68, 0.84) if closed else (372, xh * 0.17, 38, 0.74)]),
                *k.ball(326, xh * 0.8, 46)])
    f.add("d", [*k.lstem(368, asc, foot_serif=False), bowl_left(368),
                *([foot(d, 368, 368 + V, left=False)] if S else [])])
    yb = xh * 0.5
    f.add("e", [stroke(d, [(392, yb, 90, 0.85), (204, T, 180), (0, cy, 270), (216, B, 0),
                           (406, xh * 0.25, 62, 0.8) if closed else (402, xh * 0.17, 38, 0.74)]),
                rect(V * 0.4, yb - H * 0.44, 392 + V * 0.42, yb + H * 0.44)])
    fc, ftop = 44 + V / 2, asc + d.os - H / 2
    f.add("f", [stroke(d, [(fc, 0, 90), (fc, asc - 170, 90), (fc + 122, ftop, 0), (fc + 212, ftop - 34, 345, 0.82)]),
                rect(0, xh - H, fc + 150, xh), *k.ball(fc + 190, ftop - 46, 46), *k.feet(fc - V / 2)])
    gcx, grx, gby = 170, 142, xh * 0.33
    gcy = (T + gby) / 2
    if d.shape.get("g") == "single":
        f.add("g", [stroke(d, [(368 + V / 2, xh, 270), (368 + V / 2, 20 * Y, 270), (240, low, 180), (46, low + 58, 150, 0.84)]),
                    bowl_left(368), *([head(d, 368, 368 + V, xh).transform(-1, 0, 0, 1, 2 * 368 + V, 0)] if S else [])])
    else:
        f.add("g", [stroke(d, [(gcx, gby, 0), (gcx + grx, gcy, 90), (gcx, T, 180), (gcx - grx, gcy, 270)], closed=True, v=V * 0.9),
                    stroke(d, [(gcx - grx * 0.62, gby + 12, 232, 0.7), (gcx - grx * 0.84, gby - 58, 285, 0.72), (gcx + 30, gby - 112, 356),
                               (gcx + grx * 1.18, (gby - 112 + low) / 2, 270), (gcx - 6, low, 180),
                               (gcx - grx * 1.22, (gby - 112 + low) / 2 - 6, 90, 0.9), (gcx - grx * 0.3, gby - 108, 16, 0.5)], v=V * 0.95),
                    stroke(d, [(gcx + grx * 0.6, T - 44, 20, 0.6), (gcx + grx * 1.42, xh + 2, 8, 0.82 if not S else 1.5)], v=V * 0.8),
                    *k.ball(gcx + grx * 1.46, xh - 12, 30)])
    nr = V / 2 + 318
    f.add("h", [*k.lstem(0, asc), arch(0, nr, nr * 0.6), *k.feet(nr - V / 2)])
    dot_r = V * 0.6
    dot_y = xh + 165 if not S else xh + 178
    f.add("i", [*k.lstem(0, xh), round_dot(V / 2 - (6 if S else 0), dot_y, dot_r)])
    jc = V / 2
    f.add("j", [stroke(d, [(jc, xh - 6, 270), (jc, 15, 270), (jc - 92, low, 180), (jc - 182, low + 28, 155, 0.8)]),
                round_dot(jc, dot_y, dot_r), *k.ball(jc - 150, low + 12, 40),
                *([head(d, 0, V, xh)] if S else [])])
    if S:
        arm_l = lc_thin(98)
        karm = poly((84, 170 * Y), (300 + arm_l, xh), (300, xh), (84, 207 * Y))
        kleg = poly((338, 0), (338 + lc_thick(102), 0), (198, 312 * Y), (150, 251 * Y))
    else:
        arm_l = 98
        karm = poly((84, 66), (398, xh), (300, xh), (84, 207))
        kleg = poly((338, 0), (440, 0), (227, 272), (130, 265))
    f.add("k", [*k.lstem(0, asc), karm, kleg, *k.slab(300, 300 + arm_l, xh, 34), *k.slab(338, 338 + lc_thick(102), 0, 34)])
    lc = V / 2
    if S or d.shape.get("l") == "plain":
        f.add("l", k.lstem(0, asc))
    else:
        f.add("l", [stroke(d, [(lc, asc, 270), (lc, 105, 270), (lc + 74, B, 0), (lc + 136, 24, 22, 0.72)])])
    mw = 280
    r1 = V / 2 + mw
    r2 = r1 + mw
    f.add("m", [*k.lstem(0, xh), arch(0, r1, r1 * 0.6), arch(r1 - V / 2, r2, r1 + mw * 0.58), *k.feet(r1 - V / 2, r2 - V / 2)])
    f.add("n", [*k.lstem(0, xh), arch(0, nr, nr * 0.6), *k.feet(nr - V / 2)])
    f.add("o", [stroke(d, [(200, B, 0), (400, cy, 90), (200, T, 180), (0, cy, 270)], closed=True)])
    f.add("p", [*k.lstem(0, xh, desc), bowl_right(412)])
    f.add("q", [*k.lstem(368, xh, desc, top_serif=False), bowl_left(368)])
    f.add("r", [*k.lstem(0, xh), stroke(d, [(V - 14, xh - 118 * Y, 64, d.join), (V + 118, T, 8), (V + 198, T - 24, 340, 0.82)]),
                *k.ball(V + 178, T - 28, 42)])
    mid = cy
    f.add("s", [stroke(d, [(332, xh * 0.73, 112, 0.84) if closed else (322, xh * 0.8, 148, 0.75), (178, T, 180), (40, xh * 0.73, 270),
                           (170, mid + 4, 335), (312, xh * 0.25, 270), (150, B, 180),
                           (-8, xh * 0.26, 112, 0.84) if closed else (-2, xh * 0.17, 152, 0.75)], v=V * 0.96),
                *k.spur(336, xh * 0.72, xh + 4, 40), *k.spur(-16, xh * 0.3, -4, 40, left=True)])
    tc = 46 + V / 2
    t_top = xh + 120 if not S else xh + 95
    t_start = t_top if not S else xh - 4
    f.add("t", [stroke(d, [(tc, t_start, 270), (tc, 150 * Y, 270), (tc + 112, B, 0), (tc + 214, xh * 0.1, 28, 0.75)]),
                rect(0, xh - H, tc + 150, xh),
                *([poly((46, xh - 2), (46 + V, xh - 2), (46 + V, t_top), (44, xh))] if S else [])])
    f.add("u", [*k.lstem(nr - V / 2, xh, foot_serif=False),
                stroke(d, [(V / 2, xh, 270), (V / 2, 190 * Y, 270), (nr * 0.42, B, 0), (nr - V / 2 + 14, 118 * Y, 66, d.join)]),
                *([foot(d, nr - V / 2, nr + V / 2, left=False), head(d, 0, V, xh)] if S else [])])
    f.add("v", [diag(182, 0, 0, xh, lc_thick(92), lc_thick(94)), diag(200, 0, 360, xh, lc_thin(72), lc_thin(72)),
                *k.slab(0, lc_thick(94), xh, 36), *k.slab(360, 360 + lc_thin(72), xh, 36)])
    f.add("w", [diag(136, 0, 0, xh, lc_thick(90), lc_thick(92)), diag(150, 0, 282, xh, lc_thin(72)),
                diag(424, 0, 288, xh, lc_thick(90), lc_thick(92)), diag(438, 0, 570, xh, lc_thin(72)),
                *k.slab(0, lc_thick(92), xh, 34), *k.slab(288, 288 + lc_thick(92), xh, 24), *k.slab(570, 570 + lc_thin(72), xh, 34)])
    f.add("x", [diag(322, 0, 2, xh, lc_thick(98)), diag(0, 0, 322, xh, lc_thin(78)),
                *k.slab(2, 2 + lc_thick(98), xh, 30), *k.slab(322, 322 + lc_thin(78), xh, 30),
                *k.slab(0, lc_thin(78), 0, 30), *k.slab(322, 322 + lc_thick(98), 0, 30)])
    f.add("y", [diag(182, 0, 0, xh, lc_thick(92), lc_thick(94)), diag(137, desc, 360, xh, lc_thin(72)),
                *k.slab(0, lc_thick(94), xh, 36), *k.slab(360, 360 + lc_thin(72), xh, 36),
                *k.ball(112, desc + 34, 40)])
    z_t = 104 if not S else V * 1.06
    f.add("z", [rect(14, xh - H, 372, xh), rect(0, 0, 382, H), diag(0, 24 if not S else H, 372 - z_t, xh - 24 if not S else xh - H, z_t),
                *k.beak(14, xh, 110, 54, flip_x=True), *k.beak(382, 0, 120, 54, flip_y=True)])

    # ---- Figures: tabular, so columns of numbers line up ------------------------------------------
    ADV = 540
    FT = fig + d.os - H / 2
    FY = fig / 690

    def fy(v):
        return fig * v

    vf = V + 2

    def fs(nodes, **kw):
        kw.setdefault("v", vf)
        return stroke(d, nodes, **kw)

    fmid = (FT + B) / 2
    f.add("zero", [fs([(205, B, 0), (410, fmid, 90), (205, FT, 180), (0, fmid, 270)], closed=True)], advance=ADV)
    f.add("one", [rect(0, 0, vf, fig), poly((0, fig), (vf, fig), (vf, fig - 96), (-132, fig - 196), (-132, fig - 116)),
                  *([foot(d, 0, vf)] if S else [])], advance=ADV)
    f.add("two", [fs([(18, fy(0.73), 66, 0.82), (195, FT, 0), (368, fy(0.72), 270), (38, 42, 228)]), rect(0, 0, 410, H),
                  *k.ball(52, fy(0.74), 46), *k.beak(410, 0, 120, 54, flip_y=True)], advance=ADV)
    f.add("three", [fs([(18, fy(0.84), 36, 0.8), (185, FT, 0), (352, fy(0.75), 270), (165, fy(0.53), 180, 0.86)]),
                    fs([(165, fy(0.53), 0, 0.86), (382, fy(0.27), 270), (185, B, 180), (2, fy(0.15), 150, 0.8)]),
                    *k.ball(48, fy(0.82), 44), *k.ball(34, fy(0.16), 44)], advance=ADV)
    f.add("four", [rect(312, 0, 312 + vf, fig), diag(0, 175 * FY, 300, fig, 104 if not S else 44), rect(0, 175 * FY, 468, 175 * FY + H),
                   *([foot(d, 312, 312 + vf)] if S else [])], advance=ADV)
    f.add("five", [rect(60, fig - H, 392, fig), poly((60, fig), (60 + vf, fig), (60 + vf - 16, 372 * FY), (42, 338 * FY)) if not S
                   else poly((60, fig), (60 + 40, fig), (60 + 30, 362 * FY), (44, 338 * FY)),
                   fs([(90, 362 * FY, 34, 0.8), (205, 440 * FY, 0), (392, 228 * FY, 270), (190, B, 180), (2, fy(0.15), 150, 0.8)]),
                   *k.ball(34, fy(0.16), 44)], advance=ADV)
    b6t = 450 * FY
    six_cy = (b6t + B) / 2

    def six():
        return [fs([(205, B, 0), (368, six_cy, 90), (205, b6t, 180), (42, six_cy, 270)], closed=True),
                fs([(322, fy(0.97), 145, 0.8), (42, six_cy, 270)]), *k.ball(306, fy(0.92), 42)]

    f.add("six", six(), advance=ADV)
    f.add("seven", [rect(0, fig - H, 420, fig), diag(92, 0, 322, fig - 20, 104, 98), *k.beak(0, fig, 130, 54, flip_x=True)], advance=ADV)
    mid8 = fy(0.53)
    f.add("eight", [fs([(205, mid8, 0), (350, (mid8 + FT) / 2, 90), (205, FT, 180), (60, (mid8 + FT) / 2, 270)], closed=True, v=V * 0.94),
                    fs([(205, B, 0), (378, (mid8 + B) / 2, 90), (205, mid8, 180), (32, (mid8 + B) / 2, 270)], closed=True)], advance=ADV)
    f.add("nine", [p.transform(-1, 0, 0, -1, 410, fig) for p in six()], advance=ADV)

    # ---- Punctuation ----------------------------------------------------------------------------
    r = V * 0.64
    pw = H if not S else V * 0.55  # symbols keep an even, sturdier stroke on high-contrast faces

    def dot(x, y):
        return round_dot(x, y, r)

    def tail(x, y):
        return stroke(d, [(x + 18, y + r * 0.6, 262, 1.0), (x - 30, y - 128, 240, 0.42)], v=V * 1.02)

    f.add("period", [dot(0, r)], (60, 60))
    f.add("comma", [dot(0, r), tail(0, r)], (56, 58))
    f.add("colon", [dot(0, r), dot(0, xh - r)], (60, 60))
    f.add("semicolon", [dot(0, r), tail(0, r), dot(0, xh - r)], (58, 60))
    f.add("exclam", [poly((-48, cap), (48, cap), (31, 215), (-31, 215)), dot(0, r)], (70, 70))
    f.add("question", [stroke(d, [(24, cap * 0.76, 62, 0.8), (195, CT, 0), (365, cap * 0.72, 270), (205, cap * 0.4, 244), (190, 225, 270)]),
                       dot(190, r), *k.ball(60, cap * 0.76, 44)], ("T", "O"))

    def qmark(x):
        return poly((x - 42, cap + 20), (x + 42, cap + 20), (x + 26, cap - 205), (x - 26, cap - 205))

    f.add("quotesingle", [qmark(0)], (66, 66))
    f.add("quotedbl", [qmark(0), qmark(128)], (66, 66))
    f.add("grave", [poly((0, cap + 6), (100, cap + 6), (170, cap - 130), (100, cap - 130))], (60, 60))
    ptop, pbot = asc + 18, desc + 22
    pmid = (ptop + pbot) / 2

    def paren():
        return stroke(d, [(178, ptop, 236, 0.6), (V / 2, pmid, 270), (178, pbot, 304, 0.6)], v=V * 0.96, h=V * 0.96 if not S else H * 1.6)

    f.add("parenleft", [paren()], (50, 24))
    f.add("parenright", [paren().transform(-1, 0, 0, 1, 0, 0)], (24, 50))

    def bracket():
        return [rect(0, pbot, V * 0.92, ptop), rect(0, ptop - H, 210, ptop), rect(0, pbot, 210, pbot + H)]

    f.add("bracketleft", bracket(), (68, 26))
    f.add("bracketright", [p.transform(-1, 0, 0, 1, 0, 0) for p in bracket()], (26, 68))

    def brace_half():
        tp = ptop - H / 2
        return stroke(d, [(230, tp, 180, 0.8), (128, tp - 92, 270), (128, pmid + 92, 270), (30, pmid, 180, 0.72)], v=V * 0.92, h=H)

    def brace():
        return [brace_half(), brace_half().transform(1, 0, 0, -1, 0, 2 * pmid)]

    f.add("braceleft", brace(), (28, 24))
    f.add("braceright", [p.transform(-1, 0, 0, 1, 0, 0) for p in brace()], (24, 28))
    slash_w = 84 if not S else V * 0.62
    f.add("slash", [diag(0, desc + 60, 340, asc + 12, slash_w)], ("D", "D"))
    f.add("backslash", [diag(340, desc + 60, 0, asc + 12, slash_w)], ("D", "D"))
    f.add("bar", [rect(0, desc + 10, V * 0.9 if not S else V * 0.6, asc + 30)], (84, 84))
    f.add("hyphen", [rect(0, 218 * Y, 270, 218 * Y + pw)], (46, 46))
    f.add("underscore", [rect(0, -130, 520, -130 + pw * 0.92)], (0, 0))
    math_y = 300 * Y
    f.add("plus", [rect(0, math_y - pw / 2, 450, math_y + pw / 2), rect(225 - pw / 2, math_y - 225, 225 + pw / 2, math_y + 225)], advance=ADV)
    f.add("equal", [rect(0, math_y + 62, 450, math_y + 62 + pw), rect(0, math_y - 62 - pw, 450, math_y - 62)], advance=ADV)

    def chevron():
        rise = 85 if not S else 62
        return [poly((430, math_y + 215), (430, math_y + 215 - rise), (98, math_y), (0, math_y)),
                poly((430, math_y - 215), (430, math_y - 215 + rise), (98, math_y), (0, math_y))]

    f.add("less", chevron(), advance=ADV)
    f.add("greater", [p.transform(-1, 0, 0, 1, 0, 0) for p in chevron()], advance=ADV)
    f.add("asciicircum", [diag(0, cap * 0.42, 180, cap, 92, 86), diag(354, cap * 0.42, 190, cap, 92, 86)], advance=ADV)
    f.add("asciitilde", [stroke(d, [(0, 262 * Y, 58, 0.92), (118, 348 * Y, 0), (258, 272 * Y, 335), (398, 252 * Y, 0), (516, 338 * Y, 58, 0.92)],
                                v=V * 0.9, h=(H if not S else pw) * 0.92)], advance=ADV)

    def spoke(a):
        ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
        return poly((-34, 0), (34, 0), (26, 182), (-26, 182)).transform(ca, sa, -sa, ca, 0, cap - 172)

    f.add("asterisk", [spoke(a) for a in (0, 72, 144, 216, 288)], (42, 42))
    hash_t = 76 if not S else V * 0.62
    f.add("numbersign", [diag(82, 0, 212, fig, hash_t), diag(258, 0, 388, fig, hash_t),
                         rect(0, 205 * FY, 470, 205 * FY + pw), rect(24, 425 * FY, 494, 425 * FY + pw)], advance=ADV)
    f.add("dollar", [stroke(d, [(378, fig * 0.8, 148, 0.8), (208, FT - 8, 180), (44, fig * 0.73, 270), (205, fig * 0.5 + 4, 335), (368, fig * 0.26, 270),
                                (188, B + 8, 180), (6, fig * 0.17, 152, 0.8)], v=V),
                     rect(205 - 32, fig - 30, 205 + 32, fig + 86), rect(205 - 32, -86, 205 + 32, 30)], advance=ADV)

    def small_o(cx, cyy):
        return stroke(d, [(cx, cyy - 150, 0), (cx + 110, cyy, 90), (cx, cyy + 150, 180), (cx - 110, cyy, 270)], closed=True, v=V * 0.76, h=H * 0.72)

    f.add("percent", [small_o(135, fig - 165), small_o(625, 165), diag(150, 0, 535, fig, 80 if not S else V * 0.6)], ("R", "R"))
    f.add("ampersand", [stroke(d, [(602, 0, 135, 1.0), (258, 420 * C, 124), (150, 560 * C, 90), (262, CT, 0), (368, 560 * C, 270), (235, 385 * C, 205),
                                   (52, 190 * C, 270), (258, CB, 0), (478, 150 * C, 45), (548, 345 * C, 80, 0.86)], v=V * 1.02, h=H)], ("R", "T"))
    atv, ath = V * 0.78, H * 0.76
    f.add("at", [stroke(d, [(350, 138, 0), (480, 290, 90), (350, 442, 180), (220, 290, 270)], closed=True, v=atv, h=ath),
                 stroke(d, [(506, 462, 270), (506, 180, 270), (602, 112, 0), (766, 290, 90), (432, CT - 20, 180), (58, 290, 270),
                            (432, -102, 0), (678, -50, 28, 0.86)], v=atv, h=ath)], ("R", "R"))

    return f
