"""Monospace construction: fit the Latin set to one advance without distorting stems."""

from __future__ import annotations

from dataclasses import replace

import pathops

from letrasiq.drawing import Design, Drawing, Placed, oval, rect, stroke, tidy, union
from letrasiq.latin import draw_base
from letrasiq.latin_core import add_latin_core, glyph_name

# How much of a glyph's squeeze its stems share. Mild squeezes keep full weight, while
# m and w go somewhat lighter so their counters stay open.
WEIGHT_GIVE = 0.35


def _centered(path: pathops.Path, advance: int) -> Placed:
    x0, _, x1, _ = path.bounds
    return Placed(tidy(path.transform(1, 0, 0, 1, (advance - (x1 - x0)) / 2 - x0, 0)), advance)


def _fit(d: Design, base: Drawing, advance: int, margin: float) -> dict[str, Placed]:
    """Compress wide glyphs horizontally, redrawing them first so stems stay the right weight."""
    limit = advance - 2 * margin
    out: dict[str, Placed] = {}
    redrawn: dict[float, Drawing] = {}
    for name, placed in base.glyphs.items():
        if name == "space":
            out[name] = Placed(pathops.Path(), advance)
            continue
        x0, _, x1, _ = placed.path.bounds
        width = x1 - x0
        if width <= limit:
            out[name] = _centered(placed.path, advance)
            continue
        scale = round(limit / width, 2)
        # Drawing stems wider by the inverse of the squeeze cancels it out.
        if scale not in redrawn:
            k = (1 - (1 - scale) * WEIGHT_GIVE) / scale
            redrawn[scale] = draw_base(replace(d, V=d.V * k, CV=d.CV * k))
        path = redrawn[scale].glyphs[name].path
        x0, _, x1, _ = path.bounds
        out[name] = _centered(path.transform(limit / (x1 - x0), 0, 0, 1, 0, 0), advance)
    return out


def _slab_letters(d: Design, f: Drawing, advance: int) -> None:
    """Narrow letters get slabs and a hook, so each one fills its cell and reads distinctly."""
    V, H, xh, asc, cap = d.V, d.H, d.xh, d.asc, d.cap
    x = (advance - V) / 2
    left, right = 90, advance - 90
    dot = oval(advance / 2, xh + 165, V * 0.62, V * 0.62)

    def place(name: str, parts: list[pathops.Path]) -> None:
        f.glyphs[name] = _centered(union(*parts), advance)

    place("i", [rect(x, 0, x + V, xh), rect(left + 25, xh - H, x + V, xh), rect(left, 0, right, H), dot])
    place("dotlessi", [rect(x, 0, x + V, xh), rect(left + 25, xh - H, x + V, xh), rect(left, 0, right, H)])
    place("l", [rect(x, 0, x + V, asc), rect(left + 25, asc - H, x + V, asc), rect(left, 0, right, H)])
    jc = x + V / 2 + 50
    low = d.desc + d.os + H / 2
    place("j", [stroke(d, [(jc, xh - 4, 270), (jc, 20, 270), (jc - 120, low, 180), (jc - 262, low + 34, 158, 0.82)]),
                rect(left + 45, xh - H, jc + V / 2, xh), oval(jc, xh + 165, V * 0.62, V * 0.62)])
    # r, f and t would leave a hole in the cell, so their arms and bars reach further.
    T, B = d.T, d.B
    rx = 120
    place("r", [rect(rx, 0, rx + V, xh), rect(left - 10, xh - H, rx + V, xh), rect(left - 10, 0, right - 90, H),
                stroke(d, [(rx + V - 14, xh - 118, 64, d.join), (rx + V + 150, T, 6), (right + 8, T - 42, 335, 0.82)])])
    fc = x + V / 2 - 15
    ftop = asc + d.os - H / 2
    place("f", [stroke(d, [(fc, 0, 90), (fc, asc - 170, 90), (fc + 128, ftop, 0), (fc + 230, ftop - 34, 345, 0.82)]),
                rect(left - 5, xh - H, right - 25, xh), rect(left + 15, 0, right - 45, H)])
    tc = x + V / 2 - 25
    place("t", [stroke(d, [(tc, xh + 125, 270), (tc, 160, 270), (tc + 122, B, 0), (tc + 245, xh * 0.1, 28, 0.76)]),
                rect(left - 5, xh - H, right - 25, xh)])
    place(glyph_name(0x0237), [stroke(d, [(jc, xh - 4, 270), (jc, 20, 270), (jc - 120, low, 180), (jc - 262, low + 34, 158, 0.82)]),
                               rect(left + 45, xh - H, jc + V / 2, xh)])
    cx = (advance - d.CV) / 2
    place("I", [rect(cx, 0, cx + d.CV, cap), rect(left + 10, cap - d.CH, right - 10, cap), rect(left + 10, 0, right - 10, d.CH)])


def _clear_figures(d: Design, f: Drawing, advance: int) -> None:
    """A dotted zero can't be mistaken for O, and a based one can't be mistaken for l."""
    H, fig = d.H, d.fig
    centre = advance / 2
    zero = f.glyphs["zero"].path
    f.glyphs["zero"] = _centered(union(zero, oval(centre, fig / 2, d.V * 0.56, d.V * 0.72)), advance)
    one = f.glyphs["one"].path
    f.glyphs["one"] = _centered(union(one, rect(centre - 165, 0, centre + 195, H)), advance)


def draw_mono(d: Design) -> Drawing:
    advance = d.advance or 600
    margin = 44.0
    f = Drawing(d)
    f.glyphs = _fit(d, draw_base(d), advance, margin)
    _slab_letters(d, f, advance)
    _clear_figures(d, f, advance)
    add_latin_core(f, d)
    return f
