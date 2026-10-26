"""Font classification taxonomy: load, resolve, merge into specs."""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from importlib import resources
from typing import TYPE_CHECKING, Any

import yaml

if TYPE_CHECKING:
    from letrasiq.spec import FontSpec

# Spec knob keys the taxonomy is allowed to set
DEFAULT_KNOBS = (
    "weight",
    "contrast",
    "width",
    "slant",
    "serif_style",
    "terminal_style",
    "corner_roundness",
    "aperture",
)


@dataclass
class SubtypeInfo:
    classification: str
    subtype: str
    summary: str
    traits: list[str] = field(default_factory=list)
    inspired_by_traits: list[str] = field(default_factory=list)
    defaults: dict[str, Any] = field(default_factory=dict)
    construction: list[str] = field(default_factory=list)
    engine_support: str = "full"  # full | partial | stub
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
    defaults = {
        k: v for k, v in (entry.get("defaults") or {}).items() if k in DEFAULT_KNOBS
    }
    return SubtypeInfo(
        classification=classification,
        subtype=subtype,
        summary=str(entry.get("summary") or ""),
        traits=list(entry.get("traits") or []),
        inspired_by_traits=list(entry.get("inspired_by_traits") or []),
        defaults=defaults,
        construction=list(entry.get("construction") or []),
        engine_support=str(entry.get("engine_support") or "full"),
        parent_summary=str(parent.get("summary") or ""),
    )


def classification_warnings(
    classification: str | None, subtype: str | None
) -> list[str]:
    """Soft warnings for unknown or stub classifications (never hard errors)."""
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
        elif info.engine_support == "stub":
            warnings.append(
                f"{classification}/{subtype} is a stub — parametric results will be rough; "
                "prefer custom glyphs, trace, or import-ufo"
            )
        elif info.engine_support == "partial":
            warnings.append(
                f"{classification}/{subtype} has partial engine support — "
                "expect manual glyph work"
            )
    elif subtype and not classification:
        warnings.append("subtype set without classification")
    return warnings


def apply_classification_defaults(
    data: dict[str, Any],
    *,
    only_missing: bool = True,
) -> dict[str, Any]:
    """
    Merge taxonomy defaults into a raw spec dict (e.g. from JSON before from_dict).
    When only_missing=True, keys already present in `data` win.
    """
    out = dict(data)
    classification = out.get("classification")
    subtype = out.get("subtype")
    if not classification or not subtype:
        return out
    info = resolve(str(classification), str(subtype))
    if info is None:
        return out
    for key, val in info.defaults.items():
        if only_missing and key in out:
            continue
        out[key] = val
    if not out.get("notes") and info.summary:
        out["notes"] = info.summary
    return out


def fill_spec_from_taxonomy(spec: FontSpec, *, overwrite: bool = False) -> FontSpec:
    """
    Fill FontSpec knobs from taxonomy.
    When overwrite=False, only replace fields that still equal the dataclass default
    (heuristic for 'not explicitly set' when constructing FontSpec in code).
    """
    if not spec.classification or not spec.subtype:
        return spec
    info = resolve(spec.classification, spec.subtype)
    if info is None:
        return spec

    # Baseline defaults from an empty-named spec
    from letrasiq.spec import FontSpec as FS

    blank = FS(name="_")
    for key, val in info.defaults.items():
        current = getattr(spec, key)
        if overwrite or current == getattr(blank, key):
            setattr(spec, key, val)
    if not spec.notes and info.summary:
        spec.notes = info.summary
    return spec


def all_subtypes() -> list[tuple[str, str]]:
    """Return (classification, subtype) pairs for every entry."""
    pairs: list[tuple[str, str]] = []
    for classification, node in load_taxonomy().items():
        if not isinstance(node, dict):
            continue
        for subtype in (node.get("subtypes") or {}):
            pairs.append((classification, subtype))
    return pairs
