"""Starts from the engine's full construction; replace glyphs below only where this font should differ."""

from letrasiq.drawing import Design, Drawing
from letrasiq.latin import draw_latin


def draw(d: Design) -> Drawing:
    f = draw_latin(d)
    # f.add("g", [...])  # a glyph drawn differently for this font
    return f
