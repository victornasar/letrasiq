"""Contour cleanup: direction, overlaps, rounding."""

from __future__ import annotations

import pathops

from letrasiq.expand import round_path_coords, union_paths


def cleanup_path(path: pathops.Path) -> pathops.Path:
    """Remove overlaps, simplify, convert to cubics, round to integers."""
    if not path:
        return path
    try:
        cleaned = pathops.simplify(union_paths([path]), clockwise=False)
    except Exception:
        try:
            cleaned = union_paths([path])
        except Exception:
            cleaned = path
    return round_path_coords(cleaned, ndigits=0)


def reverse_if_needed(path: pathops.Path) -> pathops.Path:
    try:
        return pathops.simplify(path, clockwise=False)
    except Exception:
        return path
