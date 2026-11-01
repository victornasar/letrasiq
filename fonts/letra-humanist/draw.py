"""Letra Humanist: warm humanist sans. All values come from design.json and spec.json."""

import math

from letrasiq.drawing import Design, Drawing, diag, oval, poly, rect, stroke


def draw(d: Design) -> Drawing:
    f = Drawing(d)
    V, H, CV, CH = d.V, d.H, d.CV, d.CH
    xh, cap, asc, desc, fig = d.xh, d.cap, d.asc, d.desc, d.fig
    T, B, CT, CB = d.T, d.B, d.CT, d.CB
    cy = (T + B) / 2
    ccy = cap / 2
    low = desc + d.os + H / 2

    def cs(nodes, **kw):
        kw.setdefault("v", CV)
        kw.setdefault("h", CH)
        return stroke(d, nodes, **kw)

    def lstem(x, top, bottom=0.0, cut=14):
        """Lowercase stem whose top rises toward the right, as a pen would leave it."""
        return poly((x, bottom), (x + V, bottom), (x + V, top), (x, top - cut))

    def arch(xl, xr, apex):
        """Shoulder from a stem's right edge into a right stem centred on xr."""
        return stroke(d, [(xl + V - 14, xh - 118, 66, d.join), (apex, T, 0), (xr, xh - 190, 270), (xr, 0, 270)])

    def bowl_right(R, xs=0.0):
        """Bowl closing against a stem on its left (b, p)."""
        apex = xs + (R - xs) * 0.56
        return stroke(d, [(xs + V - 14, xh - 125, 62, d.join), (apex, T, 0), (R, cy, 270), (apex, B, 180),
                          (xs + V - 14, 110, 118, d.join)])

    def bowl_left(xs):
        """Bowl closing against a stem on its right (d, q)."""
        apex = V / 2 + (xs + 14 - V / 2) * 0.54
        return stroke(d, [(xs + 14, xh - 125, 118, d.join), (apex, T, 180), (V / 2, cy, 270), (apex, B, 0),
                          (xs + 14, 110, 62, d.join)])

    # ---- Capitals -----------------------------------------------------------------------------
    W = 660
    wl, wr, apex = CV * 0.86, CV * 1.04, 110
    lx0, rx0 = W / 2 - apex / 2, W / 2 + apex / 2 - wr
    def a_x(y):
        return (lx0 * y / cap + wl / 2, (W - wr) + (rx0 - (W - wr)) * y / cap + wr / 2)
    bar_y = 205
    f.add("A", [diag(0, 0, lx0, cap, wl), diag(W - wr, 0, rx0, cap, wr),
                rect(a_x(bar_y)[0], bar_y, a_x(bar_y)[1], bar_y + CH * 0.92)], ("D", "D"))

    top_b, bot_b, my = cap - CH / 2, CH / 2, cap * 0.53
    f.add("B", [rect(0, 0, CV, cap),
                cs([(CV - 5, top_b, 0), (245, top_b, 0), (385, (top_b + my) / 2, 270), (235, my, 180), (CV - 5, my, 180)]),
                cs([(CV - 5, my, 0), (262, my, 0), (425, (my + bot_b) / 2, 270), (252, bot_b, 180), (CV - 5, bot_b, 180)])],
          ("S", "R"))
    f.add("C", [cs([(562, cap * 0.8, 142, 0.82), (345, CT, 180), (CV / 2, ccy, 270), (345, CB, 0), (574, cap * 0.17, 38, 0.82)])],
          ("R", "O"))
    f.add("D", [rect(0, 0, CV, cap),
                cs([(CV - 5, top_b, 0), (262, top_b, 0), (590, ccy, 270), (262, bot_b, 180), (CV - 5, bot_b, 180)])],
          ("S", "R"))
    f.add("E", [rect(0, 0, CV, cap), rect(0, cap - CH, 432, cap), rect(0, my - CH * 0.46, 385, my + CH * 0.46), rect(0, 0, 446, CH)],
          ("S", "O"))
    f.add("F", [rect(0, 0, CV, cap), rect(0, cap - CH, 420, cap), rect(0, cap * 0.51 - CH * 0.46, 372, cap * 0.51 + CH * 0.46)],
          ("S", "T"))
    f.add("G", [cs([(562, cap * 0.8, 142, 0.82), (345, CT, 180), (CV / 2, ccy, 270), (345, CB, 0), (574, 118, 72, 0.84)]),
                rect(525, 105, 525 + CV, 335), rect(392, 335 - CH * 0.92, 525 + CV, 335)], ("R", "S"))
    f.add("H", [rect(0, 0, CV, cap), rect(502, 0, 502 + CV, cap), rect(CV - 5, my - CH * 0.46, 507, my + CH * 0.46)], ("S", "S"))
    f.add("I", [rect(0, 0, CV, cap)], ("S", "S"))
    f.add("J", [cs([(215, cap, 270), (215, 175, 270), (90, CB, 180), (-22, 92, 145, 0.82)])], ("T", "S"))
    f.add("K", [rect(0, 0, CV, cap), poly((90, 190), (538, cap), (432, cap), (90, 314)), poly((440, 0), (554, 0), (278, 408), (169, 400))], ("S", "D"))
    f.add("L", [rect(0, 0, CV, cap), rect(0, 0, 432, CH)], ("S", "T"))
    f.add("M", [rect(0, 0, CV * 0.9, cap), rect(668, 0, 668 + CV * 0.9, cap),
                diag(328, 0, 0, cap, 102), diag(344, 0, 675, cap, 82)], ("S", "S"))
    f.add("N", [rect(0, 0, CV * 0.88, cap), rect(516, 0, 516 + CV * 0.88, cap), diag(490, 0, 0, cap, 112)], ("S", "S"))
    def big_o(r=302):
        return cs([(CV / 2 + r, CB, 0), (CV / 2 + 2 * r, ccy, 90), (CV / 2 + r, CT, 180), (CV / 2, ccy, 270)], closed=True)
    f.add("O", [big_o()], ("R", "R"))
    pm = cap * 0.42
    f.add("P", [rect(0, 0, CV, cap),
                cs([(CV - 5, top_b, 0), (268, top_b, 0), (440, (top_b + pm) / 2, 270), (258, pm, 180), (CV - 5, pm, 180)])],
          ("S", "O"))
    f.add("Q", [big_o(), poly((372, 170), (468, 170), (690, -82), (586, -82))], ("R", "R"))
    rm = cap * 0.46
    f.add("R", [rect(0, 0, CV, cap),
                cs([(CV - 5, top_b, 0), (258, top_b, 0), (425, (top_b + rm) / 2, 270), (248, rm, 180), (CV - 5, rm, 180)]),
                diag(432, 0, 198, rm + 18, 112)], ("S", "D"))
    f.add("S", [cs([(428, cap * 0.82, 148, 0.8), (236, CT, 180), (52, cap * 0.74, 270), (232, ccy + 6, 335), (418, cap * 0.25, 270),
                    (210, CB, 180), (6, cap * 0.17, 152, 0.8)], v=CV * 0.96)], ("O", "O"))
    f.add("T", [rect(228, 0, 228 + CV, cap), rect(0, cap - CH, 228 * 2 + CV, cap)], ("T", "T"))
    f.add("U", [cs([(CV / 2, cap, 270), (CV / 2, 235, 270), (300, CB, 0), (551, 235, 90), (551, cap, 90)])], ("S", "S"))
    f.add("V", [diag(268, 0, 0, cap, 102, 106), diag(280, 0, 562, cap, 84)], ("D", "D"))
    f.add("W", [diag(195, 0, 0, cap, 100, 104), diag(210, 0, 400, cap, 82), diag(615, 0, 408, cap, 100, 104), diag(628, 0, 835, cap, 82)],
          ("D", "D"))
    f.add("X", [diag(478, 0, 6, cap, 112), diag(0, 0, 472, cap, 92)], ("D", "D"))
    f.add("Y", [rect(246, 0, 246 + CV, 300), diag(246, 285, 0, cap, CV, 106), diag(262, 285, 512, cap, 82)], ("D", "D"))
    f.add("Z", [rect(22, cap - CH, 508, cap), rect(0, 0, 520, CH), diag(0, 28, 388, cap - 28, 120)], ("O", "O"))

    # ---- Lowercase ----------------------------------------------------------------------------
    ax = 330
    f.add("a", [stroke(d, [(ax, 0, 90), (ax, xh - 165, 90), (178, T, 180), (22, xh * 0.79, 216, 0.74)]),
                stroke(d, [(ax + 10, xh * 0.56, 186, 0.6), (146, xh * 0.5, 188, 0.95), (0, xh * 0.24, 270), (118, B, 0),
                           (ax + 10, xh * 0.17, 62, d.join)])], ("O", "S"))
    f.add("b", [lstem(0, asc), bowl_right(412)], ("S", "R"))
    f.add("c", [stroke(d, [(362, xh * 0.81, 140, 0.76), (206, T, 180), (0, cy, 270), (212, B, 0), (372, xh * 0.17, 38, 0.74)])], ("R", "T"))
    f.add("d", [lstem(368, asc), bowl_left(368)], ("R", "S"))
    yb = xh * 0.5
    f.add("e", [stroke(d, [(392, yb, 90, 0.85), (204, T, 180), (0, cy, 270), (216, B, 0), (402, xh * 0.17, 38, 0.74)]),
                rect(V * 0.4, yb - H * 0.44, 392 + V * 0.42, yb + H * 0.44)], ("R", "O"))
    fc, ftop = 44 + V / 2, asc + d.os - H / 2
    f.add("f", [stroke(d, [(fc, 0, 90), (fc, asc - 170, 90), (fc + 122, ftop, 0), (fc + 212, ftop - 34, 345, 0.82)]),
                rect(0, xh - H, fc + 150, xh)], ("T", -14))
    gcx, grx, gby = 170, 142, xh * 0.33
    gcy = (T + gby) / 2
    f.add("g", [stroke(d, [(gcx, gby, 0), (gcx + grx, gcy, 90), (gcx, T, 180), (gcx - grx, gcy, 270)], closed=True, v=V * 0.9),
                stroke(d, [(gcx - grx * 0.62, gby + 12, 232, 0.7), (gcx - grx * 0.84, gby - 58, 285, 0.72), (gcx + 30, gby - 112, 356),
                           (gcx + grx * 1.18, (gby - 112 + low) / 2, 270), (gcx - 6, low, 180),
                           (gcx - grx * 1.22, (gby - 112 + low) / 2 - 6, 90, 0.9), (gcx - grx * 0.3, gby - 108, 16, 0.5)], v=V * 0.95),
                stroke(d, [(gcx + grx * 0.6, T - 44, 20, 0.6), (gcx + grx * 1.42, xh + 2, 8, 0.82)], v=V * 0.8)], ("O", "T"))
    nr = V / 2 + 318
    f.add("h", [lstem(0, asc), arch(0, nr, nr * 0.6)], ("S", "S"))
    dot_r = V * 0.6
    f.add("i", [lstem(0, xh), oval(V / 2, xh + 165, dot_r, dot_r)], ("S", "S"))
    jc = V / 2
    f.add("j", [stroke(d, [(jc, xh - 6, 270), (jc, 15, 270), (jc - 92, low, 180), (jc - 182, low + 28, 155, 0.8)]),
                oval(jc, xh + 165, dot_r, dot_r)], ("T", "S"))
    f.add("k", [lstem(0, asc), poly((84, 66), (398, xh), (300, xh), (84, 207)), poly((338, 0), (440, 0), (227, 272), (130, 265))], ("S", "D"))
    lc = V / 2
    f.add("l", [stroke(d, [(lc, asc, 270), (lc, 105, 270), (lc + 74, B, 0), (lc + 136, 24, 22, 0.72)])], ("S", "T"))
    mw = 280
    r1 = V / 2 + mw
    r2 = r1 + mw
    f.add("m", [lstem(0, xh), arch(0, r1, r1 * 0.6), arch(r1 - V / 2, r2, r1 + mw * 0.58)], ("S", "S"))
    f.add("n", [lstem(0, xh), arch(0, nr, nr * 0.6)], ("S", "S"))
    f.add("o", [stroke(d, [(200, B, 0), (400, cy, 90), (200, T, 180), (0, cy, 270)], closed=True)], ("R", "R"))
    f.add("p", [lstem(0, xh, desc), bowl_right(412)], ("S", "R"))
    f.add("q", [lstem(368, xh, desc), bowl_left(368)], ("R", "S"))
    f.add("r", [lstem(0, xh), stroke(d, [(V - 14, xh - 118, 64, d.join), (V + 118, T, 8), (V + 198, T - 24, 340, 0.82)])], ("S", "T"))
    mid = cy
    f.add("s", [stroke(d, [(322, xh * 0.8, 148, 0.75), (178, T, 180), (40, xh * 0.73, 270), (170, mid + 4, 335), (312, xh * 0.25, 270),
                           (150, B, 180), (-2, xh * 0.17, 152, 0.75)], v=V * 0.96)], ("O", "O"))
    tc = 46 + V / 2
    f.add("t", [stroke(d, [(tc, xh + 120, 270), (tc, 150, 270), (tc + 112, B, 0), (tc + 214, xh * 0.1, 28, 0.75)]),
                rect(0, xh - H, tc + 150, xh)], ("T", "T"))
    f.add("u", [lstem(nr - V / 2, xh),
                stroke(d, [(V / 2, xh, 270), (V / 2, 190, 270), (nr * 0.42, B, 0), (nr - V / 2 + 14, 118, 66, d.join)])], ("S", "S"))
    f.add("v", [diag(182, 0, 0, xh, 92, 94), diag(200, 0, 360, xh, 72, 72)], ("D", "D"))
    f.add("w", [diag(136, 0, 0, xh, 90, 92), diag(150, 0, 282, xh, 72), diag(424, 0, 288, xh, 90, 92), diag(438, 0, 570, xh, 72)], ("D", "D"))
    f.add("x", [diag(322, 0, 2, xh, 98), diag(0, 0, 322, xh, 78)], ("D", "D"))
    f.add("y", [diag(182, 0, 0, xh, 92, 94), diag(137, desc, 360, xh, 72)], ("D", "D"))
    f.add("z", [rect(14, xh - H, 372, xh), rect(0, 0, 382, H), diag(0, 24, 268, xh - 24, 104)], ("O", "O"))

    # ---- Figures: tabular, so columns of numbers line up ------------------------------------------
    ADV = 540
    FT = fig + d.os - H / 2
    def fy(k):
        return fig * k
    vf = V + 2
    def fs(nodes, **kw):
        kw.setdefault("v", vf)
        return stroke(d, nodes, **kw)
    fmid = (FT + B) / 2
    f.add("zero", [fs([(205, B, 0), (410, fmid, 90), (205, FT, 180), (0, fmid, 270)], closed=True)], advance=ADV)
    s1 = 0.0
    f.add("one", [rect(s1, 0, s1 + vf, fig), poly((s1, fig), (s1 + vf, fig), (s1 + vf, fig - 96), (s1 - 132, fig - 196), (s1 - 132, fig - 116))], advance=ADV)
    f.add("two", [fs([(18, fy(0.73), 66, 0.82), (195, FT, 0), (368, fy(0.72), 270), (38, 42, 228)]), rect(0, 0, 410, H)], advance=ADV)
    f.add("three", [fs([(18, fy(0.84), 36, 0.8), (185, FT, 0), (352, fy(0.75), 270), (165, fy(0.53), 180, 0.86)]),
                    fs([(165, fy(0.53), 0, 0.86), (382, fy(0.27), 270), (185, B, 180), (2, fy(0.15), 150, 0.8)])], advance=ADV)
    f.add("four", [rect(312, 0, 312 + vf, fig), diag(0, 175, 300, fig, 104), rect(0, 175, 468, 175 + H)], advance=ADV)
    f.add("five", [rect(60, fig - H, 392, fig), poly((60, fig), (60 + vf, fig), (60 + vf - 16, 372), (42, 338)),
                   fs([(90, 362, 34, 0.8), (205, 440, 0), (392, 228, 270), (190, B, 180), (2, fy(0.15), 150, 0.8)])], advance=ADV)
    b6t = 450
    six_cy = (b6t + B) / 2
    def six():
        return [fs([(205, B, 0), (368, six_cy, 90), (205, b6t, 180), (42, six_cy, 270)], closed=True),
                fs([(322, fy(0.97), 145, 0.8), (42, six_cy, 270)])]
    f.add("six", six(), advance=ADV)
    f.add("seven", [rect(0, fig - H, 420, fig), diag(92, 0, 322, fig - 20, 104, 98)], advance=ADV)
    mid8 = fy(0.53)
    f.add("eight", [fs([(205, mid8, 0), (350, (mid8 + FT) / 2, 90), (205, FT, 180), (60, (mid8 + FT) / 2, 270)], closed=True, v=V * 0.94),
                    fs([(205, B, 0), (378, (mid8 + B) / 2, 90), (205, mid8, 180), (32, (mid8 + B) / 2, 270)], closed=True)], advance=ADV)
    nine = [p.transform(-1, 0, 0, -1, 410, fig) for p in six()]
    f.add("nine", nine, advance=ADV)

    # ---- Punctuation ----------------------------------------------------------------------------
    r = V * 0.64
    def dot(x, y):
        return oval(x, y, r, r)
    def tail(x, y):
        return stroke(d, [(x + 18, y + r * 0.6, 262, 1.0), (x - 30, y - 128, 240, 0.42)], v=V * 1.02)
    f.add("period", [dot(0, r)], (60, 60))
    f.add("comma", [dot(0, r), tail(0, r)], (56, 58))
    f.add("colon", [dot(0, r), dot(0, xh - r)], (60, 60))
    f.add("semicolon", [dot(0, r), tail(0, r), dot(0, xh - r)], (58, 60))
    f.add("exclam", [poly((-48, cap), (48, cap), (31, 215), (-31, 215)), dot(0, r)], (70, 70))
    f.add("question", [stroke(d, [(24, cap * 0.76, 62, 0.8), (195, CT, 0), (365, cap * 0.72, 270), (205, cap * 0.4, 244), (190, 225, 270)]),
                       dot(190, r)], ("T", "O"))
    def qmark(x):
        return poly((x - 42, cap + 20), (x + 42, cap + 20), (x + 26, cap - 205), (x - 26, cap - 205))
    f.add("quotesingle", [qmark(0)], (66, 66))
    f.add("quotedbl", [qmark(0), qmark(128)], (66, 66))
    f.add("grave", [poly((0, cap + 6), (100, cap + 6), (170, cap - 130), (100, cap - 130))], (60, 60))
    ptop, pbot = asc + 18, desc + 22
    pmid = (ptop + pbot) / 2
    def paren():
        return stroke(d, [(178, ptop, 236, 0.6), (V / 2, pmid, 270), (178, pbot, 304, 0.6)], v=V * 0.96, h=V * 0.96)
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
    f.add("slash", [diag(0, desc + 60, 340, asc + 12, 84)], ("D", "D"))
    f.add("backslash", [diag(340, desc + 60, 0, asc + 12, 84)], ("D", "D"))
    f.add("bar", [rect(0, desc + 10, V * 0.9, asc + 30)], (84, 84))
    f.add("hyphen", [rect(0, 218, 270, 218 + H)], (46, 46))
    f.add("underscore", [rect(0, -130, 520, -130 + H * 0.92)], (0, 0))
    math_y = 300
    f.add("plus", [rect(0, math_y - H / 2, 450, math_y + H / 2), rect(225 - H / 2, math_y - 225, 225 + H / 2, math_y + 225)], advance=ADV)
    f.add("equal", [rect(0, math_y + 62, 450, math_y + 62 + H), rect(0, math_y - 62 - H, 450, math_y - 62)], advance=ADV)
    def chevron():
        return [poly((430, math_y + 215), (430, math_y + 130), (98, math_y), (0, math_y)),
                poly((430, math_y - 215), (430, math_y - 130), (98, math_y), (0, math_y))]
    f.add("less", chevron(), advance=ADV)
    f.add("greater", [p.transform(-1, 0, 0, 1, 0, 0) for p in chevron()], advance=ADV)
    f.add("asciicircum", [diag(0, cap * 0.42, 180, cap, 92, 86), diag(354, cap * 0.42, 190, cap, 92, 86)], advance=ADV)
    f.add("asciitilde", [stroke(d, [(0, 262, 58, 0.92), (118, 348, 0), (258, 272, 335), (398, 252, 0), (516, 338, 58, 0.92)], v=V * 0.9, h=H * 0.92)], advance=ADV)
    def spoke(a):
        ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
        return poly((-34, 0), (34, 0), (26, 182), (-26, 182)).transform(ca, sa, -sa, ca, 0, cap - 172)
    f.add("asterisk", [spoke(a) for a in (0, 72, 144, 216, 288)], (42, 42))
    f.add("numbersign", [diag(82, 0, 212, fig, 76), diag(258, 0, 388, fig, 76),
                         rect(0, 205, 470, 205 + H), rect(24, 425, 494, 425 + H)], advance=ADV)
    f.add("dollar", [stroke(d, [(378, fig * 0.8, 148, 0.8), (208, FT - 8, 180), (44, fig * 0.73, 270), (205, fig * 0.5 + 4, 335), (368, fig * 0.26, 270),
                                (188, B + 8, 180), (6, fig * 0.17, 152, 0.8)], v=V),
                     rect(205 - 32, fig - 30, 205 + 32, fig + 86), rect(205 - 32, -86, 205 + 32, 30)], advance=ADV)
    def small_o(cx, cyy):
        return stroke(d, [(cx, cyy - 150, 0), (cx + 110, cyy, 90), (cx, cyy + 150, 180), (cx - 110, cyy, 270)], closed=True, v=V * 0.76, h=H * 0.72)
    f.add("percent", [small_o(135, fig - 165), small_o(625, 165), diag(150, 0, 535, fig, 80)], ("R", "R"))
    f.add("ampersand", [stroke(d, [(602, 0, 135, 1.0), (258, 420, 124), (150, 560, 90), (262, CT, 0), (368, 560, 270), (235, 385, 205),
                                   (52, 190, 270), (258, CB, 0), (478, 150, 45), (548, 345, 80, 0.86)], v=V * 1.02, h=H)], ("R", "T"))
    atv, ath = V * 0.78, H * 0.76
    f.add("at", [stroke(d, [(350, 138, 0), (480, 290, 90), (350, 442, 180), (220, 290, 270)], closed=True, v=atv, h=ath),
                 stroke(d, [(506, 462, 270), (506, 180, 270), (602, 112, 0), (766, 290, 90), (432, CT - 20, 180), (58, 290, 270),
                            (432, -102, 0), (678, -50, 28, 0.86)], v=atv, h=ath)], ("R", "R"))

    return f
