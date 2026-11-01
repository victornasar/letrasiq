"""Latin Core beyond ASCII: reusable marks with computed anchors, and the remaining glyphs."""

from __future__ import annotations

import math
import unicodedata
from importlib import resources
from typing import Callable

import pathops
from fontTools.agl import UV2AGL

from letrasiq.drawing import Design, Drawing, Placed, diag, oval, poly, rect, stroke, tidy, union
from letrasiq.outline import to_cubic_path


def glyph_name(code: int) -> str:
    return UV2AGL.get(code) or f"uni{code:04X}"


def core_codes() -> list[int]:
    text = resources.files("letrasiq").joinpath("data/latin_core.txt").read_text(encoding="utf-8")
    return [int(line.split()[0], 16) for line in text.splitlines() if line.strip() and not line.startswith("#")]


# Letters that take these marks are written with a comma, whatever Unicode's cedilla suggests.
COMMA_BELOW_LETTERS = set("GKLNRgklnr")
SHORT_CARON_LETTERS = set("dltL")
TOP_MARKS = {0x0300, 0x0301, 0x0302, 0x0303, 0x0304, 0x0306, 0x0307, 0x0308, 0x030A, 0x030B, 0x030C}
GAP_LOWER, GAP_UPPER = 62, 42


def _band_center(path: pathops.Path, top: bool, band: float = 0.14) -> float:
    """Centre of the ink nearest a glyph's top or bottom edge, blended with its overall centre."""
    x0, y0, x1, y1 = path.bounds
    limit = y1 - (y1 - y0) * band if top else y0 + (y1 - y0) * band
    xs: list[float] = []
    for verb, pts in to_cubic_path(path).segments:
        if verb in ("moveTo", "lineTo", "curveTo"):
            p = pts[-1]
            if (p[1] >= limit) if top else (p[1] <= limit):
                xs.append(p[0])
    return ((min(xs) + max(xs)) / 2 + (x0 + x1) / 2) / 2 if xs else (x0 + x1) / 2


def _moved(path: pathops.Path, dx: float = 0.0, dy: float = 0.0, sx: float = 1.0, sy: float = 1.0) -> pathops.Path:
    return path.transform(sx, 0, 0, sy, dx, dy)


def _marks(d: Design, dot: Callable[[float, float, float], pathops.Path]) -> dict[str, pathops.Path]:
    """Marks drawn with their attachment point at (0, 0): above it for top marks, below for bottom."""
    w = d.V * 0.82
    t = max(d.H * 0.9, d.V * 0.5)
    r = d.V * 0.56
    light = {"v": d.V * 0.72, "h": t}

    def acute(shift: float = 0.0) -> pathops.Path:
        return poly((-w * 0.55 + shift, 0), (w * 0.2 + shift, 0), (w * 1.05 + shift, 165), (w * 0.1 + shift, 165))

    def chevron(flip: bool) -> pathops.Path:
        arms = union(diag(-135, 0, -46, 150, w * 0.8), diag(135 - w * 0.8, 0, 46 - w * 0.8, 150, w * 0.8))
        return _moved(arms, dy=150, sy=-1) if flip else arms

    marks = {
        "acute": acute(),
        "grave": _moved(acute(), sx=-1),
        "circumflex": chevron(False),
        "caron": chevron(True),
        "tilde": stroke(d, [(-130, 40, 58, 0.9), (-62, 108, 0), (28, 58, 330), (92, 40, 0), (150, 112, 58, 0.9)], **light),
        "macron": rect(-125, 0, 125, t),
        "breve": stroke(d, [(-108, 130, 280, 0.8), (0, t / 2, 0), (108, 130, 80, 0.8)], **light),
        "dotaccent": dot(0, r, r),
        "dieresis": union(dot(-88, r, r), dot(88, r, r)),
        "ring": stroke(d, [(0, 12 + t / 2, 0), (62, 86, 90), (0, 160 - t / 2, 180), (-62, 86, 270)], closed=True, **light),
        "hungarumlaut": union(acute(-58), acute(82)),
        "commaabove": _moved(_comma(d), dy=170, sx=-1, sy=-1),
        "cedilla": stroke(d, [(0, 30, 270, 0.7), (30, -62, 300, 0.8), (54, -112, 270, 0.9), (0, -184, 180, 0.8), (-68, -166, 150, 0.7)], **light),
        "ogonek": stroke(d, [(20, 24, 225, 0.9), (-42, -66, 270), (6, -132, 0, 0.9), (56, -116, 30, 0.7)], **light),
        "commabelow": _moved(_comma(d), dy=-34),
        "caronshort": _moved(_comma(d), dy=0, sx=0.92, sy=0.92),
    }
    return marks


def _comma(d: Design) -> pathops.Path:
    """A comma with its head's top at y=0 and its tail below."""
    r = d.V * 0.5
    return union(oval(0, -r, r, r), stroke(d, [(r * 0.3, -r * 0.5, 262), (-r * 0.75, -r * 2.8, 240, 0.42)], v=d.V * 0.8))


def add_latin_core(f: Drawing, d: Design) -> None:
    """Add every Latin Core glyph that isn't drawn yet."""
    square = d.shape.get("dots", "round") == "square"

    def dot(x: float, y: float, r: float) -> pathops.Path:
        return rect(x - r * 0.84, y - r * 0.84, x + r * 0.84, y + r * 0.84) if square else oval(x, y, r, r)

    marks = _marks(d, dot)
    overrides: dict[str, dict[str, float]] = d.shape.get("anchors", {})
    V, H, xh, cap, fig = d.V, d.H, d.xh, d.cap, d.fig
    limit = (d.advance - 60) if d.advance else None

    def add(name: str, parts: list[pathops.Path], sb: tuple | str | None = (40, 40)) -> None:
        path = union(*parts)
        if d.advance:
            x0, _, x1, _ = path.bounds
            if x1 - x0 > limit:
                path = _moved(path, sx=limit / (x1 - x0))
            f.add(name, [path], advance=d.advance)
        else:
            f.add(name, [path], sb=(30, 30) if sb == "fig" else sb)

    def top_anchor(base: str, path: pathops.Path) -> tuple[float, float]:
        y1 = path.bounds[3]
        gap = GAP_UPPER if base[0].isupper() else GAP_LOWER
        return overrides.get(base, {}).get("top", _band_center(path, True)), y1 + gap

    def bottom_anchor(base: str, path: pathops.Path) -> float:
        return overrides.get(base, {}).get("bottom", _band_center(path, False))

    # ---- Bases that the accents sit on ------------------------------------------------------
    for name, placed in list(f.glyphs.items()):
        if placed.path and (len(name) == 1 and name.isalpha() or name in ("dotlessi", "uni0237", "dotlessj")):
            x, y = top_anchor(name, placed.path)
            placed.anchors = {"top": (round(x), round(y)), "bottom": (round(bottom_anchor(name, placed.path)), 0),
                              "ogonek": (round(placed.path.bounds[2] - V * 0.45), 0)}

    def compose(code: int) -> None:
        base_code, mark_code = (int(p, 16) for p in unicodedata.decomposition(chr(code)).split())
        letter = chr(base_code)
        base_name = letter
        if mark_code in TOP_MARKS and letter in "ij":
            base_name = "dotlessi" if letter == "i" else glyph_name(0x0237)
        base = f.glyphs[base_name]
        path = base.path
        x, y = top_anchor(base_name, path)
        upper = letter.isupper()
        squash = 0.86 if upper else 1.0
        if mark_code == 0x030C and letter in SHORT_CARON_LETTERS:
            # Slovak and Czech: an apostrophe-like caron beside the ascender, not over it.
            x1 = path.bounds[2]
            right = (x1 + V * 0.42) if letter != "t" else (x + V * 1.0)
            top = cap if letter == "L" else (d.asc if letter in "dl" else xh + 90)
            mark = _moved(marks["caronshort"], dx=right, dy=top)
        elif mark_code == 0x0327 and letter in COMMA_BELOW_LETTERS:
            # Latvian: g takes its comma above, the others below.
            mark = _moved(marks["commaabove"], dx=x, dy=path.bounds[3] + 34) if letter == "g" else _moved(marks["commabelow"], dx=bottom_anchor(base_name, path))
        elif mark_code == 0x0327:
            mark = _moved(marks["cedilla"], dx=bottom_anchor(base_name, path))
        elif mark_code == 0x0326:
            mark = _moved(marks["commabelow"], dx=bottom_anchor(base_name, path))
        elif mark_code == 0x0328:
            mark = _moved(marks["ogonek"], dx=path.bounds[2] - V * 0.5)
        else:
            key = {0x0300: "grave", 0x0301: "acute", 0x0302: "circumflex", 0x0303: "tilde", 0x0304: "macron", 0x0306: "breve",
                   0x0307: "dotaccent", 0x0308: "dieresis", 0x030A: "ring", 0x030B: "hungarumlaut", 0x030C: "caron"}[mark_code]
            mark = _moved(marks[key], dx=x, dy=y, sy=squash)
        name = glyph_name(code)
        # Marks that reach past the letter, like the short caron on d, keep their room.
        reach = mark.bounds[2] + V * 0.15
        width = base.width if d.advance else max(base.width, round(reach))
        f.glyphs[name] = Placed(tidy(union(path, mark)), width)

    # ---- Combining marks and spacing accents ------------------------------------------------
    top_height = xh + GAP_LOWER
    combining = {0x0300: "grave", 0x0301: "acute", 0x0302: "circumflex", 0x0303: "tilde", 0x0304: "macron", 0x0306: "breve",
                 0x0307: "dotaccent", 0x0308: "dieresis", 0x030A: "ring", 0x030B: "hungarumlaut", 0x030C: "caron"}
    for code, key in combining.items():
        path = tidy(union(_moved(marks[key], dy=top_height)))
        f.glyphs[glyph_name(code)] = Placed(path, 0, anchors={"_top": (0, round(top_height)), "top": (0, round(path.bounds[3] + 30))})
    for code, key, anchor in ((0x0326, "commabelow", "_bottom"), (0x0327, "cedilla", "_bottom"), (0x0328, "ogonek", "_ogonek")):
        f.glyphs[glyph_name(code)] = Placed(tidy(union(marks[key])), 0, anchors={anchor: (0, 0)})
    for code, key in ((0x00B4, "acute"), (0x02C6, "circumflex"), (0x02C7, "caron"), (0x02D8, "breve"), (0x02D9, "dotaccent"),
                      (0x02DA, "ring"), (0x02DC, "tilde"), (0x02DD, "hungarumlaut"), (0x00A8, "dieresis"), (0x00AF, "macron")):
        add(glyph_name(code), [_moved(marks[key], dy=top_height)], (44, 44))
    add(glyph_name(0x00B8), [marks["cedilla"]], (50, 50))
    add(glyph_name(0x02DB), [marks["ogonek"]], (50, 50))

    # ---- Letters built from others -----------------------------------------------------------
    def part(name: str) -> pathops.Path:
        return f.glyphs[name].path

    def joined(left: str, right: str, overlap: float) -> pathops.Path:
        a, b = part(left), part(right)
        return union(a, _moved(b, dx=a.bounds[2] - b.bounds[0] - overlap))

    # AE shares one stem: a single diagonal runs into the E, with no second diagonal to overlap it.
    ae_e = part("E")
    ae_x = 300.0
    ae_shifted = _moved(ae_e, dx=ae_x - ae_e.bounds[0])
    stem_x = ae_x + (d.serif_len if d.serifs != "none" else 0)
    ae_thin = d.CV * 0.86 if d.serifs == "none" else d.CH * 1.2
    ae_bar = 205 * cap / 710
    ae_at_bar = stem_x * ae_bar / cap
    ae_parts = [ae_shifted, diag(0, 0, stem_x - ae_thin * 0.3, cap, ae_thin),
                rect(ae_at_bar + ae_thin / 2, ae_bar, stem_x + d.CV / 2, ae_bar + d.CH * 0.92)]
    if d.serifs != "none":
        ae_parts.append(rect(-44, 0, ae_thin + 44, d.serif_t))
    add(glyph_name(0x00C6), ae_parts, "optical")
    add(glyph_name(0x00E6), [joined("a", "e", V * 0.95)], "optical")
    add(glyph_name(0x0152), [joined("O", "E", d.CV * 1.0)], "optical")
    add(glyph_name(0x0153), [joined("o", "e", V * 0.95)], "optical")

    d_cap = part("D")
    bar_cap = d.CH * 0.86
    eth = union(d_cap, rect(d_cap.bounds[0] - 48, cap * 0.5 - bar_cap / 2, d_cap.bounds[0] + d.CV + 110, cap * 0.5 + bar_cap / 2))
    add(glyph_name(0x00D0), [eth], "optical")
    add(glyph_name(0x0110), [eth], "optical")
    h_cap = part("H")
    add(glyph_name(0x0126), [h_cap, rect(h_cap.bounds[0] - 40, cap * 0.76 - bar_cap / 2, h_cap.bounds[2] + 40, cap * 0.76 + bar_cap / 2)], "optical")
    d_low, h_low = part("d"), part("h")
    bar_low = max(H * 0.86, V * 0.5)
    stem_right = d_low.bounds[2]
    add(glyph_name(0x0111), [d_low, rect(stem_right - V - 100, d.asc - 130 - bar_low / 2, stem_right + 30, d.asc - 130 + bar_low / 2)], "optical")
    add(glyph_name(0x0127), [h_low, rect(h_low.bounds[0] - 30, d.asc - 130 - bar_low / 2, h_low.bounds[0] + V + 100, d.asc - 130 + bar_low / 2)], "optical")

    def slash(path: pathops.Path, overshoot: float, width: float) -> pathops.Path:
        x0, y0, x1, y1 = path.bounds
        return union(path, diag(x0 + (x1 - x0) * 0.06, y0 - overshoot, x1 - (x1 - x0) * 0.06 - width, y1 + overshoot, width))

    add(glyph_name(0x00D8), [slash(part("O"), 36, max(d.CH, d.CV * 0.55))], "optical")
    add(glyph_name(0x00F8), [slash(part("o"), 30, max(H, V * 0.55))], "optical")

    def l_stroke(name: str, top: float, lean: float, t: float) -> pathops.Path:
        p = part(name)
        x = p.bounds[0] + (d.CV if name == "L" else V) / 2
        if not d.serifs == "none":
            # Serif feet push the outline's left edge past the stem.
            x = p.bounds[0] + d.serif_len + (d.CV if name == "L" else V) / 2
        y = top * 0.5
        return union(p, poly((x - lean, y - 82 - t / 2), (x + lean, y + 82 - t / 2), (x + lean, y + 82 + t / 2), (x - lean, y - 82 + t / 2)))

    add(glyph_name(0x0141), [l_stroke("L", cap, 118, bar_cap)], "optical")
    add(glyph_name(0x0142), [l_stroke("l", d.asc, 100, bar_low)], "optical")

    # ---- Small versions: scaled down, then thickened so strokes stay in proportion -----------
    def small(name: str, scale: float, stem: float = 0.72) -> pathops.Path:
        """A glyph at this scale whose stems measure ``stem`` of the font's stem."""
        path = _moved(part(name), sx=scale, sy=scale)
        grow = V * stem - V * scale
        if grow <= 0:
            return path
        grown = _moved(path)
        grown.stroke(grow, pathops.LineCap.BUTT_CAP, pathops.LineJoin.MITER_JOIN, 2.0)
        grown.convertConicsToQuads()
        return union(path, grown)

    high = fig - xh * 0.6
    add(glyph_name(0x00AA), [_moved(small("a", 0.6), dy=high), rect(0, high - 70, 240, high - 70 + H * 0.8)], (46, 46))
    add(glyph_name(0x00BA), [_moved(small("o", 0.6), dy=high), rect(0, high - 70, 240, high - 70 + H * 0.8)], (46, 46))
    trade_y = cap - cap * 0.42
    t_small = small("T", 0.42, 0.62)
    add(glyph_name(0x2122), [_moved(t_small, dy=trade_y), _moved(small("M", 0.42, 0.62), dx=t_small.bounds[2] + 36, dy=trade_y)], (40, 40))

    def circled(inner: pathops.Path) -> list[pathops.Path]:
        R, cy = 350.0, cap / 2
        ring = stroke(d, [(R, cy - R + 36, 0), (2 * R - 36, cy, 90), (R, cy + R - 36, 180), (36, cy, 270)], closed=True, v=V * 0.72, h=H * 0.72)
        x0, y0, x1, y1 = inner.bounds
        return [ring, _moved(inner, dx=R - (x0 + x1) / 2, dy=cy - (y0 + y1) / 2)]

    add(glyph_name(0x00A9), circled(small("C", 0.56)), (46, 46))
    add(glyph_name(0x00AE), [_moved(p, dx=0, dy=cap * 0.44, sx=0.56, sy=0.56) for p in circled(small("R", 0.56))], (46, 46))
    add(glyph_name(0x00B0), [stroke(d, [(100, cap - 200 + H * 0.3, 0), (190, cap - 100, 90), (100, cap - H * 0.3, 180), (10, cap - 100, 270)], closed=True, v=V * 0.7, h=H * 0.65)], (46, 46))

    # ---- Punctuation -------------------------------------------------------------------------
    pw = H if d.serifs == "none" else V * 0.55
    dash_y = 218 * xh / 520
    add(glyph_name(0x2013), [rect(0, dash_y, 500, dash_y + pw)], (24, 24))
    add(glyph_name(0x2014), [rect(0, dash_y, 900, dash_y + pw)], (24, 24))
    add(glyph_name(0x2212), [rect(0, 300 * xh / 520 - pw / 2, 450, 300 * xh / 520 + pw / 2)], (45, 45))

    q_top = cap + 18
    # Quotes are larger than a comma so they read at text sizes.
    comma_head = _moved(_comma(d), sx=1.32, sy=1.32)
    quote_right = _moved(comma_head, dy=q_top)
    q_left_path = _moved(comma_head, sx=-1, sy=-1)
    quote_left = _moved(q_left_path, dy=q_top - q_left_path.bounds[3])
    pair = V * 1.75
    add(glyph_name(0x2018), [quote_left], (54, 54))
    add(glyph_name(0x2019), [quote_right], (54, 54))
    add(glyph_name(0x201C), [quote_left, _moved(quote_left, dx=pair)], (54, 54))
    add(glyph_name(0x201D), [quote_right, _moved(quote_right, dx=pair)], (54, 54))
    low = _moved(comma_head, dy=comma_head.bounds[3] - comma_head.bounds[1] - V * 0.5)
    add(glyph_name(0x201A), [low], (54, 54))
    add(glyph_name(0x201E), [low, _moved(low, dx=pair)], (54, 54))

    def guillemet(x: float) -> pathops.Path:
        ht, mid, thin = 118.0, 300 * xh / 520 - 34, V * 0.72
        return union(poly((x + 130, mid + ht), (x + 130 + thin, mid + ht), (x + thin, mid), (x, mid)),
                     poly((x + 130, mid - ht), (x + 130 + thin, mid - ht), (x + thin, mid), (x, mid)))

    add(glyph_name(0x2039), [guillemet(0)], (44, 44))
    add(glyph_name(0x203A), [_moved(guillemet(0), sx=-1)], (44, 44))
    add(glyph_name(0x00AB), [guillemet(0), guillemet(150)], (44, 44))
    add(glyph_name(0x00BB), [_moved(guillemet(0), sx=-1), _moved(guillemet(150), sx=-1)], (44, 44))
    r = V * 0.64
    add(glyph_name(0x2026), [dot(0, r, r), dot(290, r, r), dot(580, r, r)], (60, 60))
    add(glyph_name(0x00B7), [dot(0, 300 * xh / 520, r)], (60, 60))
    add(glyph_name(0x2022), [dot(0, 300 * xh / 520, V * 1.15)], (50, 50))
    add(glyph_name(0x00D7), [_moved(rect(-205, -pw / 2, 205, pw / 2).transform(math.cos(math.pi / 4), math.sin(math.pi / 4), -math.sin(math.pi / 4), math.cos(math.pi / 4), 0, 0), dy=300 * xh / 520),
                             _moved(rect(-205, -pw / 2, 205, pw / 2).transform(math.cos(math.pi / 4), -math.sin(math.pi / 4), math.sin(math.pi / 4), math.cos(math.pi / 4), 0, 0), dy=300 * xh / 520)], (70, 70))
    mid = 300 * xh / 520
    add(glyph_name(0x00F7), [rect(-225, mid - pw / 2, 225, mid + pw / 2), dot(0, mid + 172, r * 0.86), dot(0, mid - 172, r * 0.86)], (45, 45))

    def flipped(name: str, drop: float) -> pathops.Path:
        p = part(name)
        return _moved(p, dy=p.bounds[3] - drop, sx=-1, sy=-1)

    add(glyph_name(0x00A1), [flipped("exclam", 210)], (70, 70))
    add(glyph_name(0x00BF), [flipped("question", 210)], (24, 40))

    # ---- Currency and signs ------------------------------------------------------------------
    c_low = part("c")
    cx = (c_low.bounds[0] + c_low.bounds[2]) / 2
    add(glyph_name(0x00A2), [c_low, rect(cx - V * 0.28, c_low.bounds[1] - 80, cx + V * 0.28, c_low.bounds[3] + 80)], "fig")
    bar = max(H, V * 0.62)
    add(glyph_name(0x00A3), [stroke(d, [(370, fig * 0.82, 148, 0.82), (230, fig + d.os - H / 2, 180), (100, fig * 0.72, 270), (100, fig * 0.3, 270), (40, 40, 225, 0.9)]),
                             rect(0, 0, 410, H), rect(10, fig * 0.42 - bar / 2, 320, fig * 0.42 + bar / 2)], "fig")
    y_cap = part("Y")
    yc = (y_cap.bounds[0] + y_cap.bounds[2]) / 2
    add(glyph_name(0x00A5), [y_cap, rect(yc - 210, fig * 0.33, yc + 210, fig * 0.33 + bar * 0.86), rect(yc - 210, fig * 0.17, yc + 210, fig * 0.17 + bar * 0.86)], "fig")
    c_cap = part("C")
    add(glyph_name(0x20AC), [c_cap, rect(c_cap.bounds[0] - 70, cap * 0.56, c_cap.bounds[0] + 340, cap * 0.56 + bar * 0.86),
                             rect(c_cap.bounds[0] - 70, cap * 0.37, c_cap.bounds[0] + 310, cap * 0.37 + bar * 0.86)], "fig")
    s_small = small("s", 0.92, 0.92)
    h_s = s_small.bounds[3] - s_small.bounds[1]
    add(glyph_name(0x00A7), [_moved(s_small, dy=cap - h_s), _moved(s_small, dy=cap - h_s * 1.78, sx=1), ], (46, 46))
    p_stem = V * 0.86
    add(glyph_name(0x00B6), [rect(250, -60, 250 + p_stem, cap), rect(400, -60, 400 + p_stem * 0.8, cap),
                             oval(250, cap - 200, 200, 200), rect(250, cap - H * 0.9, 480, cap)], (40, 62))

    # ---- Accented letters: last, so they use every base above -------------------------------
    for code in core_codes():
        parts = unicodedata.decomposition(chr(code)).split()
        if glyph_name(code) not in f.glyphs and len(parts) == 2 and not parts[0].startswith("<") and chr(int(parts[0], 16)).isalpha():
            compose(code)
