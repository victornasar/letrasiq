"""Built-in parametric skeleton templates for the MVP charset."""

from __future__ import annotations

from letrasiq.glyph import GlyphSource, MVP_GLYPHS, Stroke
from letrasiq.spec import FontSpec


def _S(*points: tuple[float, float], closed: bool = False) -> Stroke:
    return Stroke(kind="stroke", points=[list(p) for p in points], closed=closed)


def _C(*points: tuple[float, float], closed: bool = False) -> Stroke:
    return Stroke(kind="curve", points=[list(p) for p in points], closed=closed)


def _metrics(spec: FontSpec) -> dict[str, float]:
    # Design on a unit grid then scale; aperture opens counters
    w = 420 * (0.7 + spec.width * 0.6)  # typical capital width
    return {
        "cap": float(spec.cap_height),
        "x": float(spec.x_height),
        "base": float(spec.baseline),
        "desc": float(spec.descender),
        "asc": float(spec.ascender),
        "w": w,
        "ap": float(spec.aperture),
    }


def _caps(m: dict[str, float]) -> dict[str, GlyphSource]:
    cap, base, w, ap = m["cap"], m["base"], m["w"], m["ap"]
    mid = cap * 0.5
    cx = w * 0.5
    # aperture opens bowls: larger ap → wider gaps / more open forms
    open_gap = 40 + ap * 80

    glyphs: dict[str, GlyphSource] = {}

    def g(name: str, *strokes: Stroke) -> None:
        glyphs[name] = GlyphSource(name=name, type="parametric", skeleton=list(strokes))

    g("A", _S((0, base), (cx, cap)), _S((w, base), (cx, cap)), _S((w * 0.22, mid), (w * 0.78, mid)))
    g("B", _S((0, base), (0, cap)), _S((0, cap), (w * 0.55, cap), (w * 0.75, cap * 0.78), (w * 0.55, mid), (0, mid)),
      _S((0, mid), (w * 0.6, mid), (w * 0.85, mid * 0.5), (w * 0.6, base), (0, base)))
    g("C", _S((w * 0.85, cap * 0.78), (w * 0.55, cap), (w * 0.2, cap), (0, mid), (w * 0.2, base), (w * 0.55, base), (w * 0.85, base + open_gap * 0.3)))
    g("D", _S((0, base), (0, cap)), _S((0, cap), (w * 0.45, cap), (w, mid), (w * 0.45, base), (0, base)))
    g("E", _S((0, base), (0, cap)), _S((0, cap), (w * 0.85, cap)), _S((0, mid), (w * 0.7, mid)), _S((0, base), (w * 0.85, base)))
    g("F", _S((0, base), (0, cap)), _S((0, cap), (w * 0.85, cap)), _S((0, mid), (w * 0.7, mid)))
    g("G", _S((w * 0.85, cap * 0.78), (w * 0.55, cap), (w * 0.2, cap), (0, mid), (w * 0.2, base), (w * 0.55, base), (w, base), (w, mid * 0.9)),
      _S((cx, mid * 0.9), (w, mid * 0.9)))
    g("H", _S((0, base), (0, cap)), _S((w, base), (w, cap)), _S((0, mid), (w, mid)))
    g("I", _S((cx, base), (cx, cap)))
    g("J", _S((w * 0.75, cap), (w * 0.75, base + 80), (cx, base), (w * 0.2, base + 60)))
    g("K", _S((0, base), (0, cap)), _S((w, cap), (0, mid * 1.05)), _S((0, mid * 0.95), (w, base)))
    g("L", _S((0, base), (0, cap)), _S((0, base), (w * 0.8, base)))
    g("M", _S((0, base), (0, cap)), _S((0, cap), (cx, mid * 0.7)), _S((w, cap), (cx, mid * 0.7)), _S((w, base), (w, cap)))
    g("N", _S((0, base), (0, cap)), _S((0, cap), (w, base)), _S((w, base), (w, cap)))
    g("O", _S((cx, base), (w * 0.15, base), (0, mid), (w * 0.15, cap), (cx, cap), (w * 0.85, cap), (w, mid), (w * 0.85, base), (cx, base), closed=True))
    g("P", _S((0, base), (0, cap)), _S((0, cap), (w * 0.6, cap), (w, mid * 1.35), (w * 0.6, mid), (0, mid)))
    g("Q", _S((cx, base), (w * 0.15, base), (0, mid), (w * 0.15, cap), (cx, cap), (w * 0.85, cap), (w, mid), (w * 0.85, base), (cx, base), closed=True),
      _S((cx * 1.1, mid * 0.55), (w * 0.95, base - 30)))
    g("R", _S((0, base), (0, cap)), _S((0, cap), (w * 0.6, cap), (w, mid * 1.35), (w * 0.6, mid), (0, mid)),
      _S((w * 0.45, mid), (w, base)))
    g("S", _S((w * 0.85, cap * 0.82), (w * 0.5, cap), (w * 0.15, cap), (0, cap * 0.78), (w * 0.15, mid * 1.15), (w * 0.5, mid),
             (w * 0.85, mid * 0.85), (w, base + 80), (w * 0.85, base), (w * 0.5, base), (w * 0.15, base + 40)))
    g("T", _S((cx, base), (cx, cap)), _S((0, cap), (w, cap)))
    g("U", _S((0, cap), (0, base + 100), (w * 0.25, base), (cx, base), (w * 0.75, base), (w, base + 100), (w, cap)))
    g("V", _S((0, cap), (cx, base)), _S((w, cap), (cx, base)))
    g("W", _S((0, cap), (w * 0.22, base)), _S((cx, cap * 0.55), (w * 0.22, base)), _S((cx, cap * 0.55), (w * 0.78, base)), _S((w, cap), (w * 0.78, base)))
    g("X", _S((0, cap), (w, base)), _S((w, cap), (0, base)))
    g("Y", _S((0, cap), (cx, mid)), _S((w, cap), (cx, mid)), _S((cx, mid), (cx, base)))
    g("Z", _S((0, cap), (w, cap)), _S((w, cap), (0, base)), _S((0, base), (w, base)))
    return glyphs


def _lower(m: dict[str, float]) -> dict[str, GlyphSource]:
    x, base, asc, desc, w, ap = m["x"], m["base"], m["asc"], m["desc"], m["w"] * 0.82, m["ap"]
    cx = w * 0.5
    glyphs: dict[str, GlyphSource] = {}

    def g(name: str, *strokes: Stroke) -> None:
        glyphs[name] = GlyphSource(name=name, type="parametric", skeleton=list(strokes))

    g("a", _S((w * 0.85, x * 0.55), (w * 0.6, x), (w * 0.25, x), (0, x * 0.55), (w * 0.25, base), (w * 0.6, base), (w * 0.85, x * 0.4)),
      _S((w * 0.85, x), (w * 0.85, base)))
    g("b", _S((0, asc), (0, base)), _S((0, x * 0.55), (w * 0.35, x), (w * 0.75, x), (w, x * 0.55), (w * 0.75, base), (w * 0.35, base), (0, x * 0.45)))
    g("c", _S((w * 0.85, x * 0.75), (w * 0.55, x), (w * 0.25, x), (0, x * 0.5), (w * 0.25, base), (w * 0.55, base), (w * 0.85, base + 40)))
    g("d", _S((w, asc), (w, base)), _S((w, x * 0.55), (w * 0.65, x), (w * 0.25, x), (0, x * 0.55), (w * 0.25, base), (w * 0.65, base), (w, x * 0.45)))
    g("e", _S((0, x * 0.55), (w, x * 0.55)), _S((w * 0.9, x * 0.55), (w * 0.7, x), (w * 0.3, x), (0, x * 0.55), (w * 0.25, base), (w * 0.6, base), (w * 0.9, base + 35)))
    g("f", _S((w * 0.7, asc), (w * 0.45, asc), (w * 0.3, asc - 40), (w * 0.3, base)), _S((0, x), (w * 0.7, x)))
    g("g", _S((w, x), (w, desc + 80)), _S((w, x * 0.55), (w * 0.65, x), (w * 0.25, x), (0, x * 0.55), (w * 0.25, base * 0 + x * 0.05), (w * 0.65, 0), (w, x * 0.4)),
      _S((w, desc + 80), (cx, desc), (w * 0.15, desc + 40)))
    g("h", _S((0, asc), (0, base)), _S((0, x * 0.55), (w * 0.35, x), (w * 0.75, x), (w, x * 0.55), (w, base)))
    g("i", _S((cx, x), (cx, base)), _S((cx, asc - 20), (cx, asc - 20)))  # dot as tiny stroke; expand makes blob
    g("j", _S((cx, x), (cx, desc + 60), (cx - 40, desc)), _S((cx, asc - 20), (cx, asc - 20)))
    g("k", _S((0, asc), (0, base)), _S((w, x), (0, x * 0.55)), _S((0, x * 0.55), (w, base)))
    g("l", _S((cx, asc), (cx, base)))
    g("m", _S((0, x), (0, base)), _S((0, x * 0.6), (w * 0.2, x), (w * 0.35, x), (w * 0.45, x * 0.55), (w * 0.45, base)),
      _S((w * 0.45, x * 0.55), (w * 0.6, x), (w * 0.8, x), (w, x * 0.55), (w, base)))
    g("n", _S((0, x), (0, base)), _S((0, x * 0.55), (w * 0.35, x), (w * 0.75, x), (w, x * 0.55), (w, base)))
    g("o", _S((cx, base), (w * 0.2, base), (0, x * 0.5), (w * 0.2, x), (cx, x), (w * 0.8, x), (w, x * 0.5), (w * 0.8, base), (cx, base), closed=True))
    g("p", _S((0, x), (0, desc)), _S((0, x * 0.55), (w * 0.35, x), (w * 0.75, x), (w, x * 0.55), (w * 0.75, base), (w * 0.35, base), (0, x * 0.45)))
    g("q", _S((w, x), (w, desc)), _S((w, x * 0.55), (w * 0.65, x), (w * 0.25, x), (0, x * 0.55), (w * 0.25, base), (w * 0.65, base), (w, x * 0.45)))
    g("r", _S((0, x), (0, base)), _S((0, x * 0.55), (w * 0.4, x), (w * 0.75, x)))
    g("s", _S((w * 0.85, x * 0.8), (w * 0.5, x), (w * 0.2, x), (0, x * 0.75), (w * 0.25, x * 0.55), (w * 0.5, x * 0.5),
             (w * 0.8, x * 0.4), (w, base + 50), (w * 0.7, base), (w * 0.3, base), (w * 0.1, base + 30)))
    g("t", _S((w * 0.35, asc - 40), (w * 0.35, base + 40), (w * 0.55, base), (w * 0.8, base + 20)), _S((0, x), (w * 0.75, x)))
    g("u", _S((0, x), (0, base + 60), (w * 0.3, base), (cx, base), (w * 0.7, base), (w, base + 60), (w, x)))
    g("v", _S((0, x), (cx, base)), _S((w, x), (cx, base)))
    g("w", _S((0, x), (w * 0.22, base)), _S((cx, x * 0.55), (w * 0.22, base)), _S((cx, x * 0.55), (w * 0.78, base)), _S((w, x), (w * 0.78, base)))
    g("x", _S((0, x), (w, base)), _S((w, x), (0, base)))
    g("y", _S((0, x), (cx, base)), _S((w, x), (cx, base)), _S((cx, base), (cx - 20, desc)))
    g("z", _S((0, x), (w, x)), _S((w, x), (0, base)), _S((0, base), (w, base)))
    return glyphs


def _digits(m: dict[str, float]) -> dict[str, GlyphSource]:
    cap, base, w = m["cap"], m["base"], m["w"] * 0.9
    cx = w * 0.5
    mid = (cap + base) / 2
    glyphs: dict[str, GlyphSource] = {}

    def g(name: str, *strokes: Stroke) -> None:
        glyphs[name] = GlyphSource(name=name, type="parametric", skeleton=list(strokes))

    g("zero", _S((cx, base), (w * 0.2, base), (0, mid), (w * 0.2, cap), (cx, cap), (w * 0.8, cap), (w, mid), (w * 0.8, base), (cx, base), closed=True))
    g("one", _S((w * 0.25, cap * 0.75), (cx, cap), (cx, base)), _S((w * 0.2, base), (w * 0.8, base)))
    g("two", _S((w * 0.1, cap * 0.75), (w * 0.3, cap), (w * 0.7, cap), (w * 0.9, cap * 0.7), (w * 0.7, mid), (w * 0.2, mid * 0.6), (0, base), (w, base)))
    g("three", _S((w * 0.15, cap * 0.85), (w * 0.4, cap), (w * 0.75, cap), (w, mid * 1.3), (w * 0.55, mid), (w * 0.2, mid)),
      _S((w * 0.55, mid), (w, mid * 0.7), (w * 0.7, base), (w * 0.3, base), (w * 0.1, base + 50)))
    g("four", _S((w * 0.75, base), (w * 0.75, cap)), _S((w * 0.75, cap), (0, mid * 0.9)), _S((0, mid * 0.9), (w, mid * 0.9)))
    g("five", _S((w * 0.85, cap), (w * 0.2, cap), (w * 0.15, mid * 1.15), (w * 0.55, mid * 1.2), (w, mid * 0.85), (w * 0.7, base), (w * 0.25, base), (0, base + 50)))
    g("six", _S((w * 0.8, cap), (w * 0.4, cap), (0, mid), (0, base + 80), (w * 0.3, base), (cx, base), (w * 0.85, mid * 0.55), (w * 0.5, mid), (0, mid * 0.9)))
    g("seven", _S((0, cap), (w, cap)), _S((w, cap), (w * 0.35, base)))
    g("eight", _S((cx, mid), (w * 0.25, mid * 1.15), (w * 0.25, cap), (cx, cap), (w * 0.75, cap), (w * 0.75, mid * 1.15), (cx, mid),
                 (w * 0.25, mid * 0.85), (w * 0.25, base), (cx, base), (w * 0.75, base), (w * 0.75, mid * 0.85), (cx, mid)))
    g("nine", _S((w, mid * 1.1), (w, base)), _S((w, mid), (w * 0.7, cap), (cx, cap), (w * 0.2, cap), (0, mid * 1.2), (w * 0.25, mid * 0.85), (cx, mid * 0.75), (w, mid)))
    return glyphs


def _punct(m: dict[str, float]) -> dict[str, GlyphSource]:
    x, base, cap, w = m["x"], m["base"], m["cap"], m["w"] * 0.35
    cx = w * 0.5
    glyphs: dict[str, GlyphSource] = {}

    def g(name: str, *strokes: Stroke, width: int | None = None) -> None:
        glyphs[name] = GlyphSource(
            name=name, type="parametric", skeleton=list(strokes), width=width
        )

    # Dots need a short stub so stroke expansion yields a real outline
    def _dot(x: float, y: float) -> Stroke:
        return _S((x - 1, y), (x + 1, y))

    g("period", _dot(cx, base + 40))
    g("comma", _S((cx, base + 40), (cx, base + 20), (cx - 15, base - 40)))
    g("exclam", _S((cx, cap), (cx, base + 140)), _dot(cx, base + 40))
    qmid = cap * 0.45
    g("question", _S((w * 0.15, cap * 0.75), (w * 0.35, cap), (w * 0.7, cap), (w, cap * 0.7), (cx, qmid), (cx, base + 140)),
      _dot(cx, base + 40))
    g("colon", _dot(cx, x * 0.7), _dot(cx, base + 40))
    g("semicolon", _dot(cx, x * 0.7), _S((cx, base + 40), (cx, base + 20), (cx - 15, base - 40)))
    g("quotesingle", _S((cx, cap), (cx, cap - 120)))
    g("quotedbl", _S((w * 0.3, cap), (w * 0.3, cap - 120)), _S((w * 0.7, cap), (w * 0.7, cap - 120)))
    g("parenleft", _S((w * 0.8, cap), (w * 0.2, cap * 0.7), (w * 0.2, cap * 0.3), (w * 0.8, base)))
    g("parenright", _S((w * 0.2, cap), (w * 0.8, cap * 0.7), (w * 0.8, cap * 0.3), (w * 0.2, base)))
    g("hyphen", _S((0, x * 0.55), (w * 1.6, x * 0.55)))
    glyphs["space"] = GlyphSource(name="space", type="parametric", skeleton=[])
    return glyphs


def build_mvp_glyphs(spec: FontSpec) -> dict[str, GlyphSource]:
    m = _metrics(spec)
    out: dict[str, GlyphSource] = {}
    out.update(_caps(m))
    out.update(_lower(m))
    out.update(_digits(m))
    out.update(_punct(m))
    # Ensure every MVP name exists
    for name in MVP_GLYPHS:
        if name not in out:
            out[name] = GlyphSource(name=name, type="parametric", skeleton=[])
    return out
