"""Letra Code: sans monospace, using the engine's monospace construction."""

from letrasiq.drawing import Design, Drawing
from letrasiq.mono import draw_mono


def draw(d: Design) -> Drawing:
    return draw_mono(d)
