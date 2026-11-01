"""Distance-based kerning for a fixed pair list."""

from __future__ import annotations

from functools import lru_cache
from importlib import resources
from pathlib import Path

import pathops

from letrasiq.outline import path_bounds, to_cubic_path
from letrasiq.glyph import DIGIT_NAMES


def _resolve_name(token: str) -> str:
    if token in DIGIT_NAMES:
        return DIGIT_NAMES[token]
    # legacy aliases in pair list
    aliases = {
        "quoteright": "quotesingle",
        "quoteleft": "quotesingle",
    }
    return aliases.get(token, token)


@lru_cache(maxsize=1)
def load_kern_pairs() -> list[tuple[str, str]]:
    text = resources.files("letrasiq").joinpath("data/kern_pairs.txt").read_text(
        encoding="utf-8"
    )
    pairs: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for line in text.splitlines():
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) != 2:
            continue
        left, right = _resolve_name(parts[0]), _resolve_name(parts[1])
        key = (left, right)
        if key not in seen:
            seen.add(key)
            pairs.append(key)
    return pairs


def _contours(path: pathops.Path) -> list[list[tuple[float, float]]]:
    """Each closed contour as a polyline that follows its curves."""
    contours: list[list[tuple[float, float]]] = []
    cur: list[tuple[float, float]] = []
    for verb, pts in to_cubic_path(path).segments:
        if verb == "moveTo":
            cur = [pts[0]]
        elif verb == "lineTo":
            cur.append(pts[0])
        elif verb == "curveTo":
            p0, (c1, c2, p) = cur[-1], pts
            for i in range(1, 13):
                t, u = i / 12, 1 - i / 12
                cur.append((
                    u**3 * p0[0] + 3 * u * u * t * c1[0] + 3 * u * t * t * c2[0] + t**3 * p[0],
                    u**3 * p0[1] + 3 * u * u * t * c1[1] + 3 * u * t * t * c2[1] + t**3 * p[1],
                ))
        elif verb == "closePath":
            contours.append(cur)
    return contours


def _edge(path: pathops.Path, y_min: float, y_max: float, pick, steps: int = 24) -> list[float | None]:
    """Outermost x where the outline crosses each height; None where it has no ink."""
    contours = _contours(path)
    edges: list[float | None] = []
    for i in range(steps):
        y = y_min + (y_max - y_min) * (i + 0.5) / steps
        xs = [
            a[0] + (y - a[1]) / (b[1] - a[1]) * (b[0] - a[0])
            for c in contours
            for a, b in zip(c, c[1:] + c[:1])
            if (a[1] <= y) != (b[1] <= y)
        ]
        edges.append(pick(xs) if xs else None)
    return edges


def _sample_right_edge(path: pathops.Path, y_min: float, y_max: float, steps: int = 24) -> list[float | None]:
    return _edge(path, y_min, y_max, max, steps)


def _sample_left_edge(path: pathops.Path, y_min: float, y_max: float, steps: int = 24) -> list[float | None]:
    return _edge(path, y_min, y_max, min, steps)


def kern_value(
    left_path: pathops.Path,
    left_advance: int,
    right_path: pathops.Path,
    target_gap: float = 40.0,
    clamp: tuple[float, float] = (-120.0, 0.0),
    damping: float = 1.0,
) -> int:
    """Negative kern so contour distance approaches target_gap."""
    lb = path_bounds(left_path)
    rb = path_bounds(right_path)
    if lb is None or rb is None:
        return 0
    y_min = max(lb[1], rb[1])
    y_max = min(lb[3], rb[3])
    if y_max <= y_min:
        return 0
    right_edge = _sample_right_edge(left_path, y_min, y_max)
    left_edge = _sample_left_edge(right_path, y_min, y_max)
    # Distance when glyphs are placed at advance: left_edge + advance - right_edge
    gaps = [
        (left_advance + le) - re
        for re, le in zip(right_edge, left_edge, strict=False)
        if re is not None and le is not None
    ]
    if not gaps:
        return 0
    # New gap = min_gap + k, so k = target - min_gap reaches the target gap.
    k = (target_gap - min(gaps)) * damping
    k = max(clamp[0], min(clamp[1], k))
    return int(round(k))


def build_kerning(
    placed: dict[str, tuple[pathops.Path, int]],
    target_gap: float = 40.0,
    damping: float = 1.0,
    clamp: tuple[float, float] = (-120.0, 0.0),
) -> dict[tuple[str, str], int]:
    kern: dict[tuple[str, str], int] = {}
    figures = set(DIGIT_NAMES.values())
    for left, right in load_kern_pairs():
        if left not in placed or right not in placed:
            continue
        # Figures share one width so columns line up; kerning would break that.
        if left in figures and right in figures:
            continue
        lp, la = placed[left]
        rp, _ = placed[right]
        val = kern_value(lp, la, rp, target_gap=target_gap, clamp=clamp, damping=damping)
        if val:
            kern[(left, right)] = val
    return kern
