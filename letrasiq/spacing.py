"""Automatic sidebearings from shape class."""

from __future__ import annotations

import pathops

from letrasiq.expand import path_bounds
from letrasiq.shapes import SHAPE_SIDEBEARINGS, ShapeClass, classify_path
from letrasiq.spec import FontSpec


def sidebearings(
    name: str, path: pathops.Path, spec: FontSpec, shape: ShapeClass | None = None
) -> tuple[int, int]:
    shape = shape or classify_path(name, path)
    left_f, right_f = SHAPE_SIDEBEARINGS[shape]
    unit = spec.stroke_base()
    # width knob also nudges overall tracking
    track = 0.7 + spec.width * 0.6
    left = int(round(unit * left_f * track))
    right = int(round(unit * right_f * track))
    return max(0, left), max(0, right)


def advance_width(
    name: str,
    path: pathops.Path,
    spec: FontSpec,
    explicit_width: int | None = None,
    left: int | None = None,
    right: int | None = None,
) -> tuple[int, int, int]:
    """Return (advance, left, right)."""
    if name == "space":
        adv = spec.space_advance()
        return adv, 0, 0
    if explicit_width is not None and path_bounds(path) is None:
        return explicit_width, 0, 0

    bounds = path_bounds(path)
    if bounds is None:
        adv = spec.space_advance()
        return adv, 0, 0

    x0, _, x1, _ = bounds
    bw = x1 - x0
    if left is None or right is None:
        sb_l, sb_r = sidebearings(name, path, spec)
        left = sb_l if left is None else left
        right = sb_r if right is None else right

    if explicit_width is not None:
        # honor explicit advance; distribute residual into sidebearings if needed
        return explicit_width, left, right

    adv = int(round(bw + left + right))
    return max(adv, left + right + 1), left, right


def shift_path(path: pathops.Path, dx: float, dy: float = 0.0) -> pathops.Path:
    return path.transform(1, 0, 0, 1, dx, dy)
