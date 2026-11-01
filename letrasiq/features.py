"""OpenType glyphs and feature code: figure styles, ligatures, case forms, composition.

Kerning and mark positioning are generated from the UFO's kerning and anchors when it compiles.
"""

from __future__ import annotations

from letrasiq.drawing import Design, Drawing, Placed, tidy, union
from letrasiq.glyph import DIGIT_NAMES
from letrasiq.latin_core import TOP_MARKS, glyph_name

FIGURES = list(DIGIT_NAMES.values())
CASE_FORMS = ["parenleft", "parenright", "bracketleft", "bracketright", "braceleft", "braceright", "hyphen", "endash",
              "emdash", "guillemotleft", "guillemotright", "guilsinglleft", "guilsinglright", "exclamdown", "questiondown", "periodcentered"]


def add_feature_glyphs(f: Drawing, d: Design) -> None:
    """Glyphs that only features reach: alternate figures, ligatures and capital-height punctuation."""
    lift = (d.cap - d.xh) / 2
    for name in CASE_FORMS:
        if name in f.glyphs:
            base = f.glyphs[name]
            f.glyphs[f"{name}.case"] = Placed(tidy(union(base.path.transform(1, 0, 0, 1, 0, lift))), base.width)
    if d.advance:
        return

    tabular_default = d.shape.get("figures") == "tabular"
    for name in FIGURES:
        tabular = f.glyphs[name]
        if tabular_default:
            spaced = Drawing(d)
            spaced.add(name, [tabular.path], "optical", top=d.fig)
            f.glyphs[f"{name}.pf"] = spaced.glyphs[name]
        else:
            f.glyphs[f"{name}.tf"] = Placed(tabular.path, tabular.width)
            f.add(name, [tabular.path], "optical", top=d.fig)

    for ligature, second in (("fi", "dotlessi"), ("fl", "l")):
        first_glyph, second_glyph = f.glyphs["f"], f.glyphs[second]
        moved = second_glyph.path.transform(1, 0, 0, 1, first_glyph.width, 0)
        f.glyphs[ligature] = Placed(tidy(union(first_glyph.path, moved)), first_glyph.width + second_glyph.width)


def feature_code(names: set[str], fixed_width: bool, tabular_default: bool = False) -> str:
    """Feature code for the glyphs a font actually has."""
    lines = ["languagesystem DFLT dflt;", "languagesystem latn dflt;", ""]
    top_marks = [glyph_name(code) for code in sorted(TOP_MARKS) if glyph_name(code) in names]
    dotless_j = glyph_name(0x0237)
    if top_marks and "dotlessi" in names:
        lines.append(f"@top_marks = [{' '.join(top_marks)}];")
        lines.append("feature ccmp {")
        lines.append("  sub i' @top_marks by dotlessi;")
        if dotless_j in names:
            lines.append(f"  sub j' @top_marks by {dotless_j};")
        lines.append("} ccmp;\n")

    if not fixed_width:
        if {"fi", "fl"} <= names:
            lines.append("feature liga {\n  sub f i by fi;\n  sub f l by fl;\n} liga;\n")
        suffix = ".pf" if tabular_default else ".tf"
        pairs = [(n, f"{n}{suffix}") for n in FIGURES if f"{n}{suffix}" in names]
        if pairs:
            on, off = ("pnum", "tnum") if tabular_default else ("tnum", "pnum")
            lines.append(f"feature {on} {{")
            lines.extend(f"  sub {a} by {b};" for a, b in pairs)
            lines.append(f"}} {on};\n")
            lines.append(f"feature {off} {{")
            lines.extend(f"  sub {b} by {a};" for a, b in pairs)
            lines.append(f"}} {off};\n")

    forms = [n for n in CASE_FORMS if f"{n}.case" in names]
    if forms:
        lines.append("feature case {")
        lines.extend(f"  sub {n} by {n}.case;" for n in forms)
        lines.append("} case;\n")
    return "\n".join(lines)


def glyph_categories(names: set[str], marks: set[str]) -> dict[str, str]:
    """GDEF categories, so marks attach and ligatures are treated as one unit."""
    categories: dict[str, str] = {name: "mark" for name in marks}
    for name in {"fi", "fl"} & names:
        categories[name] = "ligature"
    for name in names - marks - {"fi", "fl", ".notdef", "space"}:
        categories[name] = "base"
    return categories
