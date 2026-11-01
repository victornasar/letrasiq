"""Font metrics and identity. Drawing values live in the design sheet (design.json)."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


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
    mood: str = "neutral"
    notes: str = ""
    classification: str | None = None
    subtype: str | None = None
    extras: dict[str, Any] = field(default_factory=dict)

    def family_name(self) -> str:
        return self.name.replace("-", " ").replace("_", " ").title()

    def space_advance(self) -> int:
        return int(round(0.25 * self.upm))

    def side_bearing(self) -> int:
        """Default sidebearing for outlines placed without a design value."""
        return int(round(0.1 * self.cap_height))

    def validate(self) -> list[str]:
        errors: list[str] = []
        if self.descender >= self.baseline:
            errors.append("descender must be below baseline")
        if self.ascender <= self.cap_height:
            errors.append("ascender should be >= cap_height")
        if self.x_height >= self.cap_height:
            errors.append("x_height should be below cap_height")
        return errors

    def classification_warnings(self) -> list[str]:
        from letrasiq.classification import classification_warnings

        return classification_warnings(self.classification, self.subtype)

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
