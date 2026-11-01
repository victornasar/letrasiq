"""Tests for the font classification taxonomy."""

from __future__ import annotations

import json
from pathlib import Path

from letrasiq.classification import (
    all_subtypes,
    classification_warnings,
    list_classifications,
    load_taxonomy,
    resolve,
)
from letrasiq.check import check_font
from letrasiq.pipeline import create_font
from letrasiq.spec import FontSpec


EXPECTED = {
    "sans-serif": {
        "neo-grotesque",
        "grotesque",
        "geometric",
        "humanistic",
        "gothic",
    },
    "serif": {"old-style", "transitional", "modern", "slab"},
    "monospace": {"sans-mono", "slab-mono"},
    "display": {"compressed", "ultra-bold", "decorative"},
    "script": {"formal", "casual"},
    "blackletter": {"textura", "fraktur"},
}


def test_taxonomy_loads_all_subtypes():
    tax = load_taxonomy()
    assert set(tax.keys()) == set(EXPECTED.keys())
    for classification, subtypes in EXPECTED.items():
        assert set(tax[classification]["subtypes"].keys()) == subtypes
        for subtype in subtypes:
            info = resolve(classification, subtype)
            assert info is not None
            assert info.summary
            assert info.construction
            # No commercial brand names in taxonomy text
            blob = json.dumps(tax[classification]["subtypes"][subtype]).lower()
            for banned in ("helvetica", "futura", "garamond", "bodoni", "times new"):
                assert banned not in blob


def test_all_subtypes_helper():
    pairs = all_subtypes()
    assert len(pairs) == sum(len(s) for s in EXPECTED.values())
    assert ("sans-serif", "neo-grotesque") in pairs


def test_resolve_unknown():
    assert resolve("sans-serif", "nope") is None
    assert resolve("emoji", "happy") is None
    warns = classification_warnings("sans-serif", "nope")
    assert any("unknown subtype" in w for w in warns)
    assert classification_warnings("script", "formal") == []


def test_check_warns_on_unknown_subtype(tmp_path: Path):
    fonts = tmp_path / "fonts"
    fonts.mkdir()
    spec = FontSpec(
        name="demo",
        classification="sans-serif",
        subtype="not-a-real-subtype",
    )
    create_font("demo", spec, root=fonts)
    # Force bad subtype into saved spec (create_font may not clear it)
    p = fonts / "demo" / "spec.json"
    data = json.loads(p.read_text())
    data["subtype"] = "not-a-real-subtype"
    data["classification"] = "sans-serif"
    p.write_text(json.dumps(data), encoding="utf-8")
    result = check_font("demo", root=fonts)
    assert any("unknown subtype" in w for w in result.warnings)


def test_list_classifications():
    assert "sans-serif" in list_classifications()
