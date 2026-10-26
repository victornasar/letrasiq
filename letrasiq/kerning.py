"""Distance-based kerning for a fixed pair list."""

from __future__ import annotations

from functools import lru_cache
from importlib import resources
from pathlib import Path

import pathops

from letrasiq.expand import path_bounds
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


def _sample_right_edge(path: pathops.Path, y_min: float, y_max: float, steps: int = 24) -> list[float]:
    """For each y sample, find max x of the path (approx via bounds strip)."""
    bounds = path_bounds(path)
    if bounds is None:
        return []
    # Approximate: use overall right edge; refine with vertical strips via point cloud
    pts: list[tuple[float, float]] = []

    class _Pen:
        def moveTo(self, pt):  # noqa: N802
            pts.append(pt)

        def lineTo(self, pt):  # noqa: N802
            pts.append(pt)

        def curveTo(self, *args):  # noqa: N802
            pts.extend(args)

        def qCurveTo(self, *args):  # noqa: N802
            pts.extend(a for a in args if a is not None)

        def closePath(self):  # noqa: N802
            pass

        def endPath(self):  # noqa: N802
            pass

    path.draw(_Pen())
    if not pts:
        return []
    edges: list[float] = []
    for i in range(steps):
        y = y_min + (y_max - y_min) * (i + 0.5) / steps
        band = [p[0] for p in pts if abs(p[1] - y) <= (y_max - y_min) / steps]
        if band:
            edges.append(max(band))
        else:
            edges.append(bounds[2])
    return edges


def _sample_left_edge(path: pathops.Path, y_min: float, y_max: float, steps: int = 24) -> list[float]:
    bounds = path_bounds(path)
    if bounds is None:
        return []
    pts: list[tuple[float, float]] = []

    class _Pen:
        def moveTo(self, pt):  # noqa: N802
            pts.append(pt)

        def lineTo(self, pt):  # noqa: N802
            pts.append(pt)

        def curveTo(self, *args):  # noqa: N802
            pts.extend(args)

        def qCurveTo(self, *args):  # noqa: N802
            pts.extend(a for a in args if a is not None)

        def closePath(self):  # noqa: N802
            pass

        def endPath(self):  # noqa: N802
            pass

    path.draw(_Pen())
    if not pts:
        return []
    edges: list[float] = []
    for i in range(steps):
        y = y_min + (y_max - y_min) * (i + 0.5) / steps
        band = [p[0] for p in pts if abs(p[1] - y) <= (y_max - y_min) / steps]
        if band:
            edges.append(min(band))
        else:
            edges.append(bounds[0])
    return edges


def kern_value(
    left_path: pathops.Path,
    left_advance: int,
    right_path: pathops.Path,
    target_gap: float = 40.0,
    clamp: tuple[float, float] = (-120.0, 0.0),
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
    if not right_edge or not left_edge:
        return 0
    # Distance when glyphs are placed at advance: left_edge + advance - right_edge
    gaps = [
        (left_advance + le) - re for re, le in zip(right_edge, left_edge, strict=False)
    ]
    min_gap = min(gaps)
    # If min_gap > target, kern less negative (or 0); if smaller, pull together
    delta = target_gap - min_gap
    # delta positive means too tight → wait, if min_gap is small, we need more negative kern
    # kern k: new gap = min_gap + k; want min_gap + k ≈ target → k = target - min_gap
    k = target_gap - min_gap
    k = max(clamp[0], min(clamp[1], k))
    return int(round(k))


def build_kerning(
    placed: dict[str, tuple[pathops.Path, int]],
    target_gap: float = 40.0,
) -> dict[tuple[str, str], int]:
    kern: dict[tuple[str, str], int] = {}
    for left, right in load_kern_pairs():
        if left not in placed or right not in placed:
            continue
        lp, la = placed[left]
        rp, _ = placed[right]
        val = kern_value(lp, la, rp, target_gap=target_gap)
        if val:
            kern[(left, right)] = val
    return kern
