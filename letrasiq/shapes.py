"""Shape-class tables for automatic sidebearings."""

from __future__ import annotations

from enum import Enum

import pathops

from letrasiq.expand import path_bounds


class ShapeClass(str, Enum):
    ROUND = "round"
    STRAIGHT = "straight"
    DIAGONAL = "diagonal"
    OPEN = "open"
    NARROW = "narrow"
    WIDE = "wide"


# Sidebearing factors relative to stroke_base (left, right)
SHAPE_SIDEBEARINGS: dict[ShapeClass, tuple[float, float]] = {
    ShapeClass.ROUND: (0.55, 0.55),
    ShapeClass.STRAIGHT: (0.85, 0.85),
    ShapeClass.DIAGONAL: (0.35, 0.35),
    ShapeClass.OPEN: (0.45, 0.7),
    ShapeClass.NARROW: (1.1, 1.1),
    ShapeClass.WIDE: (0.5, 0.5),
}

# Manual hints for common letters (override auto classify)
GLYPH_CLASS_HINTS: dict[str, ShapeClass] = {
    "O": ShapeClass.ROUND,
    "o": ShapeClass.ROUND,
    "C": ShapeClass.OPEN,
    "c": ShapeClass.OPEN,
    "G": ShapeClass.OPEN,
    "Q": ShapeClass.ROUND,
    "D": ShapeClass.ROUND,
    "H": ShapeClass.STRAIGHT,
    "I": ShapeClass.NARROW,
    "i": ShapeClass.NARROW,
    "l": ShapeClass.NARROW,
    "1": ShapeClass.NARROW,
    "one": ShapeClass.NARROW,
    "M": ShapeClass.WIDE,
    "W": ShapeClass.WIDE,
    "m": ShapeClass.WIDE,
    "w": ShapeClass.WIDE,
    "A": ShapeClass.DIAGONAL,
    "V": ShapeClass.DIAGONAL,
    "W": ShapeClass.WIDE,
    "v": ShapeClass.DIAGONAL,
    "w": ShapeClass.WIDE,
    "X": ShapeClass.DIAGONAL,
    "x": ShapeClass.DIAGONAL,
    "Y": ShapeClass.DIAGONAL,
    "y": ShapeClass.DIAGONAL,
    "T": ShapeClass.STRAIGHT,
    "E": ShapeClass.STRAIGHT,
    "F": ShapeClass.STRAIGHT,
    "L": ShapeClass.OPEN,
    "space": ShapeClass.NARROW,
    "period": ShapeClass.NARROW,
    "comma": ShapeClass.NARROW,
    "exclam": ShapeClass.NARROW,
    "colon": ShapeClass.NARROW,
    "semicolon": ShapeClass.NARROW,
    "quotesingle": ShapeClass.NARROW,
    "hyphen": ShapeClass.OPEN,
}


def classify_path(name: str, path: pathops.Path) -> ShapeClass:
    if name in GLYPH_CLASS_HINTS:
        return GLYPH_CLASS_HINTS[name]
    bounds = path_bounds(path)
    if bounds is None:
        return ShapeClass.NARROW
    x0, y0, x1, y1 = bounds
    w = max(1.0, x1 - x0)
    h = max(1.0, y1 - y0)
    aspect = w / h
    if aspect < 0.35:
        return ShapeClass.NARROW
    if aspect > 1.15:
        return ShapeClass.WIDE
    return ShapeClass.STRAIGHT
