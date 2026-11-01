"""Font classification taxonomy: reference traits and construction notes for briefs."""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from importlib import resources
from typing import Any

import yaml


@dataclass
class SubtypeInfo:
    classification: str
    subtype: str
    summary: str
    traits: list[str] = field(default_factory=list)
    inspired_by_traits: list[str] = field(default_factory=list)
    construction: list[str] = field(default_factory=list)
    parent_summary: str = ""


@lru_cache(maxsize=1)
def load_taxonomy() -> dict[str, Any]:
    text = resources.files("letrasiq").joinpath("data/classifications.yaml").read_text(
        encoding="utf-8"
    )
    data = yaml.safe_load(text)
    if not isinstance(data, dict):
        raise ValueError("classifications.yaml must be a mapping")
    return data


def list_classifications() -> list[str]:
    return sorted(load_taxonomy().keys())


def list_subtypes(classification: str) -> list[str]:
    node = load_taxonomy().get(classification)
    if not isinstance(node, dict):
        return []
    subtypes = node.get("subtypes") or {}
    return sorted(subtypes.keys())


def resolve(classification: str, subtype: str) -> SubtypeInfo | None:
    """Return subtype info or None if unknown."""
    tax = load_taxonomy()
    parent = tax.get(classification)
    if not isinstance(parent, dict):
        return None
    subtypes = parent.get("subtypes") or {}
    entry = subtypes.get(subtype)
    if not isinstance(entry, dict):
        return None
    return SubtypeInfo(
        classification=classification,
        subtype=subtype,
        summary=str(entry.get("summary") or ""),
        traits=list(entry.get("traits") or []),
        inspired_by_traits=list(entry.get("inspired_by_traits") or []),
        construction=list(entry.get("construction") or []),
        parent_summary=str(parent.get("summary") or ""),
    )


def classification_warnings(
    classification: str | None, subtype: str | None
) -> list[str]:
    """Soft warnings for unknown classifications (never hard errors)."""
    warnings: list[str] = []
    if not classification and not subtype:
        return warnings
    if classification and classification not in load_taxonomy():
        warnings.append(f"unknown classification: {classification!r}")
        return warnings
    if classification and subtype:
        info = resolve(classification, subtype)
        if info is None:
            known = ", ".join(list_subtypes(classification)) or "(none)"
            warnings.append(
                f"unknown subtype {subtype!r} for {classification!r} (known: {known})"
            )
    elif subtype and not classification:
        warnings.append("subtype set without classification")
    return warnings


def all_subtypes() -> list[tuple[str, str]]:
    """Return (classification, subtype) pairs for every entry."""
    pairs: list[tuple[str, str]] = []
    for classification, node in load_taxonomy().items():
        if not isinstance(node, dict):
            continue
        for subtype in (node.get("subtypes") or {}):
            pairs.append((classification, subtype))
    return pairs
