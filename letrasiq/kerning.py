"""Distance-based kerning for a fixed pair list."""

from __future__ import annotations

import unicodedata
from functools import lru_cache
from importlib import resources
from pathlib import Path

import pathops

from letrasiq.outline import path_bounds, to_cubic_path
from letrasiq.glyph import DIGIT_NAMES, glyph_char


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


# Base letters whose sides behave alike. Accented letters join their base letter's class.
FIRST_SIDE_CLASSES = {  # the glyph's right side, when it comes first in a pair
    "A": "A", "B": "B", "C": "CG", "D": "DOQ", "E": "E", "F": "F", "J": "JU", "K": "KX", "L": "L", "P": "P",
    "R": "R", "S": "S", "T": "T", "V": "VW", "Y": "Y", "Z": "Z",
    "a": "a", "b": "bop", "c": "c", "e": "e", "f": "f", "g": "g", "h": "hmn", "k": "kx", "r": "r", "s": "s",
    "t": "t", "v": "vwy", "z": "z",
}
SECOND_SIDE_CLASSES = {  # the glyph's left side, when it comes second in a pair
    "A": "A", "C": "CGOQ", "J": "J", "S": "S", "T": "T", "U": "U", "V": "VW", "X": "X", "Y": "Y", "Z": "Z",
    "a": "a", "c": "cdegoq", "f": "f", "j": "j", "n": "mnpr", "s": "s", "t": "t", "u": "u", "v": "vwy", "x": "x", "z": "z",
}
# Glyphs with no decomposition that still belong with a letter on one side.
FIRST_SIDE_ALIASES = {"AE": "E", "OE": "E", "ae": "e", "oe": "e", "Oslash": "D", "oslash": "b", "Thorn": "P", "thorn": "b", "Dcroat": "D", "Eth": "D", "dcroat": "h", "Lslash": "L"}
SECOND_SIDE_ALIASES = {"AE": "A", "OE": "C", "ae": "a", "oe": "c", "Oslash": "C", "oslash": "c", "eth": "c", "dcroat": "c"}
PUNCTUATION_CLASSES = {
    "period": ["period", "comma", "ellipsis", "quotesinglbase", "quotedblbase"],
    "quote": ["quotesingle", "quotedbl", "quoteright", "quotedblright", "quoteleft", "quotedblleft"],
}
EXCEPTION_MARGIN = 6
MAX_SYMBOL_KERN = -35


def _base_letter(name: str) -> str | None:
    """The plain letter a glyph is built on, for accented letters."""
    char = glyph_char(name)
    if not char or len(char) != 1:
        return None
    if len(name) == 1 and name.isalpha():
        return name
    parts = unicodedata.decomposition(char).split()
    if len(parts) == 2 and not parts[0].startswith("<"):
        base = chr(int(parts[0], 16))
        return base if base.isalpha() else None
    return None


def _classes(names: list[str], table: dict[str, str], aliases: dict[str, str]) -> dict[str, list[str]]:
    by_letter = {letter: key for key, letters in table.items() for letter in letters}
    classes: dict[str, list[str]] = {}
    for name in names:
        letter = aliases.get(name) or _base_letter(name)
        key = by_letter.get(letter or "")
        if key:
            classes.setdefault(key, []).append(name)
    for key, members in PUNCTUATION_CLASSES.items():
        present = [m for m in members if m in names]
        if present:
            classes[key] = present
    return classes


class _Profiles:
    """Each glyph's left and right edges on one shared height grid, so pairs compare quickly."""

    STEP = 20

    def __init__(self, placed: dict[str, tuple[pathops.Path, int]]) -> None:
        self.placed = placed
        low = min((p.bounds[1] for p, _ in placed.values() if p), default=0.0)
        high = max((p.bounds[3] for p, _ in placed.values() if p), default=1000.0)
        self.low, self.steps = low, max(1, int((high - low) / self.STEP))
        self.high = low + self.steps * self.STEP
        self.right: dict[str, list[float | None]] = {}
        self.left: dict[str, list[float | None]] = {}

    def _edges(self, name: str, store: dict, pick) -> list[float | None]:
        if name not in store:
            store[name] = _edge(self.placed[name][0], self.low, self.high, pick, self.steps)
        return store[name]

    def gap(self, first: str, second: str) -> float | None:
        """Closest approach of two glyphs set side by side, wherever they share a height."""
        width = self.placed[first][1]
        gaps = [
            width + b - a
            for a, b in zip(self._edges(first, self.right, max), self._edges(second, self.left, min))
            if a is not None and b is not None
        ]
        return min(gaps) if gaps else None


def build_class_kerning(
    placed: dict[str, tuple[pathops.Path, int]],
    target_gap: float,
    damping: float = 0.75,
    clamp: tuple[float, float] = (-90.0, 0.0),
    minimum_gap: float = 24.0,
) -> tuple[dict[str, list[str]], dict[tuple[str, str], int]]:
    """Kerning groups and rules, with exceptions where an accent would collide.

    A rule comes from the plain letters in each class and takes the gentlest value any of
    them needs. Accented members then keep the rule unless it would crowd them.
    """
    drawn = {n: v for n, v in placed.items() if v[0]}
    names = list(drawn)
    firsts = _classes(names, FIRST_SIDE_CLASSES, FIRST_SIDE_ALIASES)
    seconds = _classes(names, SECOND_SIDE_CLASSES, SECOND_SIDE_ALIASES)
    first_of = {m: k for k, ms in firsts.items() for m in ms}
    second_of = {m: k for k, ms in seconds.items() for m in ms}
    profiles = _Profiles(drawn)

    def plain(members: list[str]) -> list[str]:
        return [m for m in members if len(m) == 1] or members

    def wanted(a: str, b: str) -> int | None:
        gap = profiles.gap(a, b)
        if gap is None:
            return None
        return int(round(max(clamp[0], min(clamp[1], (target_gap - gap) * damping))))

    class_pairs: set[tuple[str, str]] = set()
    single_pairs: set[tuple[str, str]] = set()
    figures = set(DIGIT_NAMES.values())
    for left, right in load_kern_pairs():
        if left not in drawn or right not in drawn or (left in figures and right in figures):
            continue
        if left in first_of and right in second_of:
            class_pairs.add((first_of[left], second_of[right]))
        else:
            single_pairs.add((left, right))

    groups: dict[str, list[str]] = {}
    kerning: dict[tuple[str, str], int] = {}
    for first_key, second_key in sorted(class_pairs):
        values = [v for a in plain(firsts[first_key]) for b in plain(seconds[second_key]) if (v := wanted(a, b)) is not None]
        rule = max(values, default=0)
        if rule >= -4:
            continue
        group1, group2 = f"public.kern1.{first_key}", f"public.kern2.{second_key}"
        groups[group1], groups[group2] = firsts[first_key], seconds[second_key]
        kerning[(group1, group2)] = rule
        for a in firsts[first_key]:
            for b in seconds[second_key]:
                gap = profiles.gap(a, b)
                if gap is not None and gap + rule < minimum_gap:
                    # The rule would crowd this pair, so give back only what it needs.
                    kerning[(a, b)] = int(min(0, minimum_gap + EXCEPTION_MARGIN - gap))
    for left, right in sorted(single_pairs):
        value = wanted(left, right)
        if value is not None and value < -4:
            # Punctuation keeps some air: a fully closed "A?" reads as a mistake.
            limit = 0 if left in names and right in names and len(left) == 1 and len(right) == 1 else MAX_SYMBOL_KERN
            kerning[(left, right)] = max(value, limit) if limit else value
    return groups, kerning
