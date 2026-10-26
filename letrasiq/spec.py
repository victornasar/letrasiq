"""Font style specification."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

SERIF_STYLES = ("none", "slab", "bracketed", "hairline")
TERMINAL_STYLES = ("flat", "round", "sheared", "ball")

DEFAULT_METRICS = {
    "upm": 1000,
    "ascender": 800,
    "descender": -200,
    "x_height": 500,
    "cap_height": 700,
    "baseline": 0,
}


@dataclass
class FontSpec:
    name: str
    version: str = "0.1.0"
    style_name: str = "Regular"
    upm: int = 1000
    ascender: int = 800
    descender: int = -200
    x_height: int = 500
    cap_height: int = 700
    baseline: int = 0
    weight: float = 0.45
    contrast: float = 0.15
    width: float = 0.55
    slant: float = 0.0
    serif_style: str = "none"
    terminal_style: str = "flat"
    corner_roundness: float = 0.2
    aperture: float = 0.55
    mood: str = "neutral"
    notes: str = ""
    extras: dict[str, Any] = field(default_factory=dict)

    def family_name(self) -> str:
        return self.name.replace("-", " ").replace("_", " ").title()

    def stroke_base(self) -> float:
        """Base stroke thickness in UPM units."""
        return max(12.0, self.weight * self.upm * 0.16)

    def thickness_for_angle(self, direction_radians: float) -> float:
        """Vertical strokes thicker when contrast > 0."""
        import math

        base = self.stroke_base()
        t_v = base * (1.0 + self.contrast)
        t_h = base * max(0.25, 1.0 - self.contrast)
        # direction 0 = horizontal, pi/2 = vertical
        s = abs(math.sin(direction_radians))
        return t_h + (t_v - t_h) * s

    def space_advance(self) -> int:
        return int(round(0.25 * self.upm * self.width))

    def validate(self) -> list[str]:
        errors: list[str] = []
        if self.serif_style not in SERIF_STYLES:
            errors.append(f"serif_style must be one of {SERIF_STYLES}")
        if self.terminal_style not in TERMINAL_STYLES:
            errors.append(f"terminal_style must be one of {TERMINAL_STYLES}")
        for key in ("weight", "contrast", "width", "corner_roundness", "aperture"):
            val = getattr(self, key)
            if not 0.0 <= float(val) <= 1.0:
                errors.append(f"{key} must be in [0, 1], got {val}")
        if self.descender >= self.baseline:
            errors.append("descender must be below baseline")
        if self.ascender <= self.cap_height:
            errors.append("ascender should be >= cap_height")
        return errors

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        extras = data.pop("extras", {})
        data.update(extras)
        return data

    def save(self, path: Path) -> None:
        path.write_text(json.dumps(self.to_dict(), indent=2) + "\n", encoding="utf-8")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FontSpec:
        known = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        kwargs = {k: v for k, v in data.items() if k in known and k != "extras"}
        extras = {k: v for k, v in data.items() if k not in known}
        return cls(**kwargs, extras=extras)

    @classmethod
    def load(cls, path: Path) -> FontSpec:
        return cls.from_dict(json.loads(path.read_text(encoding="utf-8")))


def title_from_folder(name: str) -> str:
    return name.replace("-", " ").replace("_", " ").title()
