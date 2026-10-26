"""Per-glyph source loading and validation."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

GlyphType = Literal["parametric", "custom"]

# MVP charset — Adobe Glyph List-ish names
MVP_GLYPHS: tuple[str, ...] = (
    "space",
    *list("ABCDEFGHIJKLMNOPQRSTUVWXYZ"),
    *list("abcdefghijklmnopqrstuvwxyz"),
    "zero",
    "one",
    "two",
    "three",
    "four",
    "five",
    "six",
    "seven",
    "eight",
    "nine",
    "period",
    "comma",
    "exclam",
    "question",
    "colon",
    "semicolon",
    "quotesingle",
    "quotedbl",
    "parenleft",
    "parenright",
    "hyphen",
)

DIGIT_NAMES = {
    "0": "zero",
    "1": "one",
    "2": "two",
    "3": "three",
    "4": "four",
    "5": "five",
    "6": "six",
    "7": "seven",
    "8": "eight",
    "9": "nine",
}

PUNCT_CHARS = {
    "period": ".",
    "comma": ",",
    "exclam": "!",
    "question": "?",
    "colon": ":",
    "semicolon": ";",
    "quotesingle": "'",
    "quotedbl": '"',
    "parenleft": "(",
    "parenright": ")",
    "hyphen": "-",
    "space": " ",
}


@dataclass
class Stroke:
    kind: Literal["stroke", "curve"]
    points: list[list[float]]
    closed: bool = False


@dataclass
class GlyphSource:
    name: str
    type: GlyphType
    skeleton: list[Stroke] = field(default_factory=list)
    overrides: dict[str, Any] = field(default_factory=dict)
    path: str | None = None
    width: int | None = None

    def to_dict(self) -> dict[str, Any]:
        if self.type == "custom":
            data: dict[str, Any] = {"type": "custom", "path": self.path or ""}
            if self.width is not None:
                data["width"] = self.width
            return data
        return {
            "type": "parametric",
            "skeleton": [
                {"kind": s.kind, "points": s.points, "closed": s.closed}
                for s in self.skeleton
            ],
            "overrides": self.overrides,
            **({"width": self.width} if self.width is not None else {}),
        }

    def save(self, path: Path) -> None:
        path.write_text(json.dumps(self.to_dict(), indent=2) + "\n", encoding="utf-8")

    @classmethod
    def from_dict(cls, name: str, data: dict[str, Any]) -> GlyphSource:
        gtype = data.get("type", "parametric")
        if gtype == "custom":
            return cls(
                name=name,
                type="custom",
                path=data.get("path", ""),
                width=data.get("width"),
            )
        skeleton = [
            Stroke(
                kind=s.get("kind", "stroke"),
                points=[list(map(float, p)) for p in s.get("points", [])],
                closed=bool(s.get("closed", False)),
            )
            for s in data.get("skeleton", [])
        ]
        return cls(
            name=name,
            type="parametric",
            skeleton=skeleton,
            overrides=dict(data.get("overrides") or {}),
            width=data.get("width"),
        )

    @classmethod
    def load(cls, path: Path) -> GlyphSource:
        name = glyph_name_from_path(path)
        return cls.from_dict(name, json.loads(path.read_text(encoding="utf-8")))


def glyph_char(name: str) -> str | None:
    if len(name) == 1:
        return name
    if name in PUNCT_CHARS:
        return PUNCT_CHARS[name]
    for digit, gname in DIGIT_NAMES.items():
        if gname == name:
            return digit
    return None


def glyph_unicode(name: str) -> int | None:
    ch = glyph_char(name)
    if ch is None:
        return None
    return ord(ch)


def load_locked(path: Path) -> set[str]:
    if not path.exists():
        return set()
    names: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            names.add(line)
    return names


def save_locked(path: Path, names: set[str]) -> None:
    path.write_text(
        "".join(f"{n}\n" for n in sorted(names)) or "",
        encoding="utf-8",
    )


_SAFE_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_.]*$")


def assert_safe_glyph_name(name: str) -> None:
    if not _SAFE_NAME.match(name) and name not in MVP_GLYPHS:
        # allow single-letter and known MVP names; reject path tricks
        if not (len(name) == 1 and name.isalpha()):
            raise ValueError(f"unsafe glyph name: {name!r}")


def glyph_filename(name: str) -> str:
    """Case-insensitive-safe filename for a glyph (UFO-style underscore).

    On APFS/HFS default volumes, ``A.json`` and ``a.json`` collide. Uppercase
    single-letter glyphs are stored as ``A_.json``.
    """
    if len(name) == 1 and name.isupper():
        return f"{name}_.json"
    return f"{name}.json"


def glyph_name_from_path(path: Path) -> str:
    stem = path.stem
    if len(stem) == 2 and stem[0].isupper() and stem[1] == "_":
        return stem[0]
    return stem
