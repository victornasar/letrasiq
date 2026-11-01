"""Release package and independent review packet for a built font."""

from __future__ import annotations

import html
import json
import shutil
from pathlib import Path

from letrasiq.glyph import load_locked
from letrasiq.pipeline import build_font, font_dir, fonts_root
from letrasiq.report import fingerprint, render_report
from letrasiq.spec import FontSpec

SPECIMEN_TEXT = (
    "Good type stays out of the way. Words hold together, spacing feels even, and the eye moves along each line "
    "without stopping. A paragraph set well invites you to keep reading; one set badly makes you notice the letters "
    "instead of the meaning."
)
LANGUAGES = {
    "Français": "Où est la bibliothèque ? Déjà vu, garçon, cœur.",
    "Español": "¿Qué tal, señor? ¡Olé! Niño, corazón.",
    "Deutsch": "Größe, Äpfel, Straße, Übung.",
    "Polski": "Zażółć gęślą jaźń.",
    "Čeština": "Příliš žluťoučký kůň úpěl ďábelské ódy.",
    "Magyar": "Árvíztűrő tükörfúrógép.",
    "Türkçe": "Şişli'de iğne, Çay, Ağaç, İstanbul.",
    "Dansk": "Blåbærgrød på Øresund.",
}
REVIEW_QUESTIONS = [
    "Would you accept this as professional work for its brief? If not, what's the first thing you'd fix?",
    "Do the control letters (H O n o a e g) establish a coherent design? Which feel wrong?",
    "Where does the construction look automated rather than drawn? Check joins, shoulders and curve tension.",
    "Is the color even in paragraphs? Which letters or pairs stand out?",
    "Are spacing and kerning right? Which pairs look too tight or too loose?",
    "Do accents sit well, especially on capitals and on r, t, d, l and letters with ogoneks?",
    "How do small sizes hold up on Windows or Linux, where hinting applies?",
]


def _specimen(spec: FontSpec, woff2: Path, brief: str) -> str:
    family = html.escape(spec.family_name())
    languages = "".join(f"<p><span class='label'>{html.escape(k)}</span>{html.escape(v)}</p>" for k, v in LANGUAGES.items())
    waterfall = "".join(f"<p style='font-size:{px}px'><span class='label'>{px} px</span>{SPECIMEN_TEXT[:62]}</p>" for px in (10, 12, 14, 16, 20, 24, 32))
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{family} Specimen</title><style>
@font-face {{ font-family: Specimen; src: url("../Web/{woff2.name}") format("woff2"); }}
:root {{ --bg:#fff; --fg:#14171a; --muted:#646c75; --line:#dde1e5; }}
@media (prefers-color-scheme: dark) {{ :root {{ --bg:#14171a; --fg:#eceff2; --muted:#a0a9b3; --line:#343a41; color-scheme: dark; }} }}
body {{ margin:0; background:var(--bg); color:var(--fg); font-family:Specimen,serif; }}
main {{ max-width:980px; margin:0 auto; padding:40px 20px 72px; }}
h1 {{ font-size:clamp(56px,11vw,120px); font-weight:normal; line-height:1; margin:0 0 16px; overflow-wrap:anywhere; }}
h2 {{ font:600 12px -apple-system,BlinkMacSystemFont,sans-serif; letter-spacing:.06em; text-transform:uppercase; color:var(--muted); border-top:1px solid var(--line); padding-top:12px; margin:40px 0 12px; }}
p {{ margin:0 0 10px; overflow-wrap:anywhere; }} .big {{ font-size:clamp(28px,5vw,46px); line-height:1.25; }} .text {{ font-size:18px; line-height:1.5; max-width:62ch; }}
.label {{ display:block; font:11px ui-monospace,Menlo,Consolas,monospace; color:var(--muted); }} .brief {{ font:16px/1.5 -apple-system,BlinkMacSystemFont,sans-serif; color:var(--muted); max-width:62ch; }}
</style></head><body><main>
<h1>{family}</h1><p class="brief">{html.escape(brief)}</p>
<h2>Capitals</h2><p class="big">ABCDEFGHIJKLMNOPQRSTUVWXYZ</p>
<h2>Lowercase</h2><p class="big">abcdefghijklmnopqrstuvwxyz</p>
<h2>Figures and punctuation</h2><p class="big">0123456789 &amp; ! ? € £ ¥ § ¶ © ® ™</p><p class="big" style="font-feature-settings:'tnum'"><span class="label">Tabular figures</span>1,234.50 / 7,111.17</p>
<h2>Words</h2><p class="big">minimum typography Hamburg AVATAR Washington extraordinary office</p>
<h2>Paragraph</h2><p class="text">{SPECIMEN_TEXT}</p>
<h2>Sizes</h2>{waterfall}
<h2>Languages</h2><div class="text">{languages}</div>
</main></body></html>
"""


def _readme(spec: FontSpec, version: str, features: str) -> str:
    return f"""{spec.family_name()} {version}

{spec.mood.capitalize()}. Latin Core character set, one Regular style.

Desktop/  OTF and TTF files to install.
Web/      WOFF2 for websites.
Documentation/  Specimen and license.

OpenType features: {features}.

Known limitations: one style only, Latin only, and not yet reviewed by a type designer.
See CHANGELOG.txt for version history.

License: SIL Open Font License 1.1. See OFL.txt.
"""


def build_release(name: str, root: Path | None = None) -> dict[str, Path]:
    """Build the font, then assemble its release package and review packet from that exact build."""
    fonts = root or fonts_root()
    d = font_dir(name, fonts)
    outputs = build_font(name, root=fonts)
    spec = FontSpec.load(d / "spec.json")
    sheet = json.loads((d / "design.json").read_text(encoding="utf-8"))
    stem = f"{spec.family_name().replace(' ', '')}-{spec.style_name}"
    family_dir = spec.family_name().replace(" ", "")
    release = d / "build" / "release"
    shutil.rmtree(release, ignore_errors=True)
    package = release / family_dir
    for folder in ("Desktop", "Web", "Documentation"):
        (package / folder).mkdir(parents=True)
    shutil.copy2(outputs["otf"], package / "Desktop")
    shutil.copy2(outputs["ttf"], package / "Desktop")
    shutil.copy2(outputs["woff2"], package / "Web")
    shutil.copy2(d / "OFL.txt", package / "Documentation" / "OFL.txt")
    if (d / "CHANGELOG.md").exists():
        shutil.copy2(d / "CHANGELOG.md", package / "Documentation" / "CHANGELOG.txt")
    (package / "Documentation" / "Specimen.html").write_text(_specimen(spec, outputs["woff2"], sheet.get("brief", "")), encoding="utf-8")
    features = "kerning, mark positioning, case forms"
    if not sheet.get("style", {}).get("advance"):
        features += ", ligatures, tabular and proportional figures"
    (package / "Documentation" / "README.txt").write_text(_readme(spec, spec.version, features), encoding="utf-8")

    current = fingerprint(d)
    (release / "manifest.json").write_text(json.dumps({"version": spec.version, "fingerprint": current}, indent=2) + "\n", encoding="utf-8")

    packet = release / f"{family_dir}-review-packet"
    packet.mkdir()
    # The report reads the manifest, so it's rendered before being copied into the packet.
    (packet / "README.md").write_text("", encoding="utf-8")
    render_report(d, spec)
    previews = d / "build" / "previews"
    for filename in ("report.html", "tester.html", "review.png", "detail.png", "detail-core.png", "specimen.png"):
        shutil.copy2(previews / filename, packet / filename)
    shutil.copytree(package, packet / family_dir)
    shutil.copy2(d / "design.json", packet / "design.json")
    notes_path = d / "review-notes.md"
    notes = notes_path.read_text(encoding="utf-8") if notes_path.exists() else "No known weaknesses recorded."
    locked = sorted(load_locked(d / "locked.txt"))
    template = {"reviewer": "", "date": "", "version": spec.version, "fingerprint": current, "outcome": "approved, or the changes you ask for"}
    (packet / "review.template.json").write_text(json.dumps(template, indent=2) + "\n", encoding="utf-8")
    questions = "\n".join(f"{i}. {q}" for i, q in enumerate(REVIEW_QUESTIONS, 1))
    (packet / "README.md").write_text(
        f"""# Review of {spec.family_name()} {spec.version}

Thanks for looking at this. The font was generated by LetrasIQ, an AI-operated font engine, from the brief below. Please judge it as you would any typeface.

## Brief

{sheet.get("brief", "")}

## What to open

- `{family_dir}/Documentation/Specimen.html`: the font in use
- `tester.html`: type your own text and compare with a system font
- `review.png`: letters, spacing proofs, kerning and paragraphs
- `detail.png` and `detail-core.png`: outlines with their points
- `report.html`: automated results, and what still needs a person
- `{family_dir}/Desktop/`: install these to test in your own apps
- `design.json`: the numbers and reasons behind the design

## Questions

{questions}

## Known weaknesses

{notes}
{f"{chr(10)}Hand-edited glyphs: {', '.join(locked)}{chr(10)}" if locked else ""}
## Recording the result

Your written critique is what matters most. To record a sign-off, fill in `review.template.json` with your name, the date and the outcome. The fingerprint ties it to this exact version.
""",
        encoding="utf-8",
    )
    shutil.make_archive(str(packet), "zip", root_dir=release, base_dir=packet.name)
    return {"package": package, "packet": packet, "archive": packet.with_suffix(".zip"), "report": previews / "report.html"}
