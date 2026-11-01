"""Generate a self-contained live type tester page for a built font."""

from __future__ import annotations

import base64
import json
from importlib import resources
from pathlib import Path

from fontTools.ttLib import TTFont

from letrasiq.spec import FontSpec

READING = (
    "Good type stays out of the way. Words hold together, spacing feels even, and the eye moves "
    "along each line without stopping. A paragraph set well invites you to keep reading; one set "
    "badly makes you notice the letters instead of the meaning. Judge it here at the size you "
    "would really use, and look at the rhythm of the whole block before any single letter."
)
INTERFACE = (
    "Sign in to your account\nSave changes    Cancel\n3 new messages\n"
    "Last updated 12 minutes ago\nSettings / Billing / Invoices\nTotal: $1,284.50 (18% off)"
)
CODE = (
    'def total(items: list[int]) -> int:\n    # O0 l1I `quotes` "double" {braces} [brackets]\n'
    "    return sum(x * 2 for x in items if x != 0)\n\nconst ok = a <= b && c >= d || !e;"
)
HEADLINE = "Hamburgefonstiv"
FIGURES = "0123456789 $48.50 72% #1 (a+b)=c"

# First sample opens the page, so each genre leads with the use its brief cares about.
SAMPLES_BY_CLASS: dict[str, dict[str, str]] = {
    "sans-serif": {"Interface": INTERFACE, "Headline": HEADLINE, "Figures": FIGURES, "Reading": READING},
    "serif": {"Reading": READING, "Headline": HEADLINE, "Figures": FIGURES},
    "monospace": {"Code": CODE, "Headline": HEADLINE, "Figures": FIGURES, "Reading": READING},
}


def _embed(value: object) -> str:
    return json.dumps(value, ensure_ascii=False).replace("</", "<\\/")


def render_tester(font_dir: Path, spec: FontSpec | None = None) -> Path:
    spec = spec or FontSpec.load(font_dir / "spec.json")
    build_dir = font_dir / "build"
    stem = f"{spec.family_name().replace(' ', '')}-{spec.style_name}"
    woff2 = build_dir / f"{stem}.woff2"
    chars = "".join(chr(c) for c in sorted(TTFont(woff2).getBestCmap()))
    samples = dict(SAMPLES_BY_CLASS.get(spec.classification or "", SAMPLES_BY_CLASS["sans-serif"]))
    samples.setdefault("Reading", READING)
    template = resources.files("letrasiq").joinpath("data/tester.html").read_text(encoding="utf-8")
    page = (
        template.replace("__FAMILY_JSON__", _embed(spec.family_name()))
        .replace("__FAMILY__", spec.family_name())
        .replace("__FONT__", base64.b64encode(woff2.read_bytes()).decode("ascii"))
        .replace("__CHARS__", _embed(chars))
        .replace("__SAMPLES__", _embed(samples))
    )
    out = build_dir / "previews" / "tester.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8")
    return out
