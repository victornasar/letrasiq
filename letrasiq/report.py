"""Professional production report: what passed, what failed, and what needs a person."""

from __future__ import annotations

import hashlib
import html
import json
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path

import ufoLib2
from fontTools.ttLib import TTFont

from letrasiq.check import check_font
from letrasiq.drawing import Design, load_design
from letrasiq.spec import FontSpec

PASSED, FAILED, PERSON = "passed", "failed", "needs a person"
CONTROL_GLYPHS = "HOnoaevps"
TEXT_FEATURES = {"kern", "mark", "mkmk", "ccmp", "liga", "tnum", "pnum", "case"}
MONO_FEATURES = {"mark", "mkmk", "ccmp", "case"}
LATER = "Weights, italics, widths, variable fonts, small caps, oldstyle figures, fractions and stylistic sets."


@dataclass
class Stage:
    name: str
    status: str
    detail: str


@dataclass
class Report:
    font: str
    version: str
    fingerprint: str
    reviewed: bool
    groups: dict[str, list[Stage]] = field(default_factory=dict)

    def count(self, status: str) -> int:
        return sum(stage.status == status for stages in self.groups.values() for stage in stages)

    @property
    def summary(self) -> str:
        state = "reviewed" if self.reviewed else "not reviewed"
        return (
            f"report {self.font}: {self.count(PASSED)} passed, {self.count(FAILED)} failed, "
            f"{self.count(PERSON)} need a person; {state}"
        )


def latin_core() -> set[int]:
    text = resources.files("letrasiq").joinpath("data/latin_core.txt").read_text(encoding="utf-8")
    return {int(line.split()[0], 16) for line in text.splitlines() if line.strip() and not line.startswith("#")}


def fingerprint(font_dir: Path) -> str:
    """Hash of everything that defines the font, so a sign-off can't outlive a change."""
    digest = hashlib.sha256()
    paths = [font_dir / "spec.json", font_dir / "design.json", *sorted((font_dir / "glyphs").glob("*.json"))]
    for path in paths:
        if path.exists():
            digest.update(path.name.encode())
            digest.update(path.read_bytes())
    return digest.hexdigest()


def sign_off(font_dir: Path, version: str, current: str) -> Stage:
    """Only a committed review.json matching this exact font counts as an independent review."""
    path = font_dir / "review.json"
    name = "Independent design review"
    if not path.exists():
        return Stage(name, PERSON, "No type designer has reviewed this font.")
    try:
        review = json.loads(path.read_text(encoding="utf-8"))
        who, date, reviewed_version, outcome = review["reviewer"], review["date"], review["version"], review["outcome"]
    except (ValueError, KeyError) as e:
        return Stage(name, FAILED, f"review.json is incomplete: {e}")
    if reviewed_version != version or review.get("fingerprint") != current:
        return Stage(name, PERSON, f"{who} reviewed an earlier state ({reviewed_version}), and the font has changed since.")
    if outcome != "approved":
        return Stage(name, PERSON, f"{who} reviewed this version on {date} and asked for changes: {outcome}.")
    return Stage(name, PASSED, f"Approved by {who} on {date}.")


def font_bakery(profile: str, font: Path) -> Stage:
    name = f"Font Bakery {profile} checks ({font.suffix[1:].upper()})"
    with tempfile.TemporaryDirectory(prefix="letrasiq-report-") as tmp:
        out = Path(tmp) / "report.json"
        try:
            subprocess.run(
                [sys.executable, "-m", "fontbakery", f"check-{profile}", str(font), "-q", "--json", str(out)],
                capture_output=True,
                timeout=300,
            )
            data = json.loads(out.read_text(encoding="utf-8"))
        except (OSError, ValueError, subprocess.TimeoutExpired) as e:
            return Stage(name, FAILED, f"Couldn't run: {e}")
    failed: list[str] = []
    for section in data["sections"]:
        for check in section["checks"]:
            if check["result"] in ("FAIL", "ERROR", "FATAL"):
                key = str(check["key"][1]).replace("<FontBakeryCheck:", "").rstrip(">")
                # Font Bakery 1.1.0's monospace check crashes on CFF; the TTF still runs it.
                if not (key == "opentype/monospace" and font.suffix == ".otf"):
                    failed.append(key)
    result = data["result"]
    counts = f"{result.get('PASS', 0)} passed, {len(failed)} failed, {result.get('SKIP', 0)} skipped"
    if failed:
        return Stage(name, FAILED, f"{counts}: {', '.join(sorted(failed))}")
    return Stage(name, PASSED, counts)


def _features(font: TTFont) -> set[str]:
    found: set[str] = set()
    for table in ("GSUB", "GPOS"):
        if table in font:
            found |= {record.FeatureTag for record in font[table].table.FeatureList.FeatureRecord}
    return found


def _otf_is_hinted(font: TTFont) -> bool:
    top = font["CFF "].cff.topDictIndex[0]
    charstring = top.CharStrings["n"] if "n" in top.CharStrings else None
    if charstring is None:
        return False
    charstring.decompile()
    return any(op in charstring.program for op in ("hstem", "vstem", "hstemhm", "vstemhm", "hintmask"))


def _stage(name: str, ok: bool, good: str, bad: str) -> Stage:
    return Stage(name, PASSED if ok else FAILED, good if ok else bad)


def _not_built(name: str, step: str) -> Stage:
    return Stage(name, FAILED, f"Not built yet. Planned in step {step}.")


def build_report(font_dir: Path, spec: FontSpec | None = None, run_font_bakery: bool = True) -> Report:
    spec = spec or FontSpec.load(font_dir / "spec.json")
    design: Design = load_design(font_dir, spec)
    sheet = json.loads((font_dir / "design.json").read_text(encoding="utf-8"))
    checks = check_font(font_dir.name, root=font_dir.parent)
    build = font_dir / "build"
    previews = build / "previews"
    stem = f"{spec.family_name().replace(' ', '')}-{spec.style_name}"
    ttf_path, otf_path = build / f"{stem}.ttf", build / f"{stem}.otf"
    ttf, otf = TTFont(ttf_path), TTFont(otf_path)
    cmap = set(ttf.getBestCmap())
    glyphs = set(ttf.getGlyphOrder())
    mono = bool(design.advance)
    current = fingerprint(font_dir)

    define = [
        _stage("Brief", bool(design.brief.strip()), "The sheet states the font's purpose.", "The design sheet has no brief."),
        _stage("Reasons for decisions", len(design.why) >= 3, f"{len(design.why)} decisions are explained.", "The sheet needs reasons for its main decisions."),
        _stage(
            "Classification",
            bool(spec.classification and spec.subtype) and not spec.classification_warnings(),
            f"{spec.classification} / {spec.subtype}.",
            "Set a recognised classification and subtype in spec.json.",
        ),
    ]

    outline_warnings = [w for w in checks.warnings if "kink" in w or "tiny" in w or "extreme" in w or "stem" in w or "overshoot" in w or "sit exactly" in w or "touching" in w]
    missing_control = [c for c in CONTROL_GLYPHS if c not in glyphs]
    letterforms = [
        _stage("Control glyphs", not missing_control, f"{CONTROL_GLYPHS} are all drawn.", f"Missing: {' '.join(missing_control)}."),
        _stage("Outline and consistency checks", not outline_warnings and checks.ok, "No problems found.",
               f"{len(checks.errors)} errors, {len(outline_warnings)} warnings. See `letrasiq check`."),
        Stage("Letterform quality", PERSON, "Curve quality and character need a designer's eye."),
    ]

    core = latin_core()
    missing_core = core - cmap
    glyph_set = [
        _stage("Latin Core coverage", not missing_core, f"All {len(core)} characters are covered.",
               f"{len(core) - len(missing_core)} of {len(core)} characters are covered. Planned in step 3."),
        _stage("Reusable marks and anchors", "acutecomb" in glyphs, "Marks and anchors are in place.", "Not built yet. Planned in step 3."),
    ]

    ufo = ufoLib2.Font.open(build / f"{stem}.ufo")
    if mono:
        kerning = [Stage("Kerning", PASSED, "Doesn't apply: every glyph has one width.")]
    else:
        kerning = [
            _stage("Kerning classes", bool(ufo.groups), f"{len(ufo.groups)} classes and {len(ufo.kerning)} rules.",
                   f"{len(ufo.kerning)} individual pairs, and no classes. Planned in step 5."),
            Stage("Kerning reviewed in real text", PERSON, "Automated values still need judging in words and sentences."),
        ]
    spacing = [
        _stage("Letter spacing", design.spacing.get("S", 0) > 0 or mono, "Letters space from measured white space.", "No spacing value in the sheet."),
        _not_built("Spacing for every glyph", "4"),
        *kerning,
    ]

    wanted = MONO_FEATURES if mono else TEXT_FEATURES
    missing_features = wanted - _features(ttf)
    os2 = ttf["OS/2"]
    head = ttf["head"]
    if run_font_bakery:
        bakery = [font_bakery("universal", ttf_path), font_bakery("universal", otf_path), font_bakery("googlefonts", ttf_path)]
    else:
        bakery = [Stage("Font Bakery checks", FAILED, "Skipped in this run.")]
    engineering = [
        *bakery,
        _stage("OpenType features", not missing_features, f"{', '.join(sorted(wanted))}.",
               f"Missing {', '.join(sorted(missing_features))}. Planned in step 6."),
        _stage("Windows metrics cover all glyphs", os2.usWinAscent >= head.yMax and os2.usWinDescent >= -head.yMin,
               "Nothing should clip.", f"Glyphs reach {head.yMax}/{head.yMin}, past the Windows limits."),
        _stage("TTF hinting", "fpgm" in ttf, "Autohinted.", "Not autohinted yet. Planned in step 7."),
        _stage("OTF hinting", _otf_is_hinted(otf), "Autohinted.", "Not autohinted yet. Planned in step 7."),
    ]

    testing = [
        _stage("Live tester", (previews / "tester.html").exists(), "tester.html is generated.", "tester.html is missing."),
        _stage("Proof sheets", (previews / "review.png").exists() and (previews / "detail.png").exists(),
               "review.png and detail.png are generated.", "Proof sheets are missing."),
        Stage("Small sizes in a browser", PERSON, "Autohinted text needs checking at 8-16 px on real screens."),
        Stage("Real applications", PERSON, "Install and test in apps like Word and InDesign."),
    ]

    review = sign_off(font_dir, spec.version, current)
    release = [
        _not_built("Release package", "8"),
        _not_built("Specimen and documentation", "8"),
        _not_built("Review packet", "8"),
        review,
    ]

    return Report(
        font=font_dir.name,
        version=spec.version,
        fingerprint=current,
        reviewed=review.status == PASSED,
        groups={
            "1. Define": define,
            "2. Letterforms": letterforms,
            "3. Glyph set": glyph_set,
            "4. Spacing and kerning": spacing,
            "5. Engineering": engineering,
            "6. Testing": testing,
            "7. Release": release,
        },
    )


PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{family} Report</title>
<style>
:root {{ --bg:#fff; --fg:#1b2026; --muted:#5a6470; --line:#d9dde1; --ok:#1f6b43; --ok-bg:#e4f3ea; --bad:#a3271a; --bad-bg:#fbe6e2; --person:#6a4a00; --person-bg:#fbf0d3; }}
@media (prefers-color-scheme: dark) {{ :root {{ --bg:#16191c; --fg:#e7eaed; --muted:#a0a9b3; --line:#343a41; --ok:#8fd8ae; --ok-bg:#1b3327; --bad:#ffb3a7; --bad-bg:#42221d; --person:#f0cf85; --person-bg:#3b2f12; color-scheme: dark; }} }}
body {{ margin:0; background:var(--bg); color:var(--fg); font:15px/1.45 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif; }}
main {{ max-width:860px; margin:0 auto; padding:28px 16px 56px; }}
h1 {{ font-size:24px; margin:0 0 4px; }} h2 {{ font-size:15px; margin:28px 0 6px; }}
p {{ margin:0 0 8px; color:var(--muted); }} code {{ font:12px ui-monospace,Menlo,Consolas,monospace; overflow-wrap:anywhere; }}
.state {{ font-size:17px; font-weight:600; color:var(--fg); }}
table {{ width:100%; border-collapse:collapse; table-layout:fixed; }} td {{ padding:7px 10px 7px 0; border-top:1px solid var(--line); vertical-align:top; overflow-wrap:anywhere; }}
td:first-child {{ width:32%; }} td:nth-child(2) {{ width:118px; }}
.pill {{ display:inline-block; padding:1px 8px; border-radius:10px; font-size:12px; font-weight:600; white-space:nowrap; }}
.passed {{ color:var(--ok); background:var(--ok-bg); }} .failed {{ color:var(--bad); background:var(--bad-bg); }} .person {{ color:var(--person); background:var(--person-bg); }}
@media (max-width:560px) {{ td {{ display:block; width:auto !important; border:0; padding:2px 0; }} tr {{ display:block; border-top:1px solid var(--line); padding:7px 0; }} }}
</style></head><body><main>
<h1>{family}</h1>
<p>Version {version}</p>
<p class="state">{state}</p>
<p>{counts}</p>
{body}
<h2>Later, outside this plan</h2>
<p>{later}</p>
<h2>Fingerprint for sign-off</h2>
<p>A <code>review.json</code> must carry this value, so a review can't outlive a change to the font.</p>
<p><code>{fingerprint}</code></p>
</main></body></html>
"""


def render_report(font_dir: Path, spec: FontSpec | None = None, run_font_bakery: bool = True) -> Path:
    spec = spec or FontSpec.load(font_dir / "spec.json")
    report = build_report(font_dir, spec, run_font_bakery)
    classes = {PASSED: "passed", FAILED: "failed", PERSON: "person"}
    sections = []
    for group, stages in report.groups.items():
        rows = "".join(
            f'<tr><td>{html.escape(s.name)}</td><td><span class="pill {classes[s.status]}">{s.status}</span></td><td>{html.escape(s.detail)}</td></tr>'
            for s in stages
        )
        sections.append(f"<h2>{html.escape(group)}</h2><table>{rows}</table>")
    state = "Reviewed by a type designer" if report.reviewed else "Not reviewed by a type designer"
    page = PAGE.format(
        family=html.escape(spec.family_name()),
        version=html.escape(spec.version),
        state=state,
        counts=f"{report.count(PASSED)} passed, {report.count(FAILED)} failed, {report.count(PERSON)} need a person",
        body="".join(sections),
        later=LATER,
        fingerprint=report.fingerprint,
    )
    previews = font_dir / "build" / "previews"
    previews.mkdir(parents=True, exist_ok=True)
    out = previews / "report.html"
    out.write_text(page, encoding="utf-8")
    (previews / "report-summary.txt").write_text(report.summary + "\n", encoding="utf-8")
    return out
