"""Letra Humanist: warm humanist sans, using the engine's default construction."""

from letrasiq.drawing import Design, Drawing
from letrasiq.latin import draw_latin


def draw(d: Design) -> Drawing:
    return draw_latin(d)
