# LetrasIQ

Local font-design toolkit operated through **Claude Code**. You describe fonts in conversation; Claude edits sources and runs the CLI. No web app, no API keys, no accounts.

## Setup

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
letrasiq version
```

Optional:

- [FontForge](https://fontforge.org/) (or any UFO editor) → `letrasiq import-ufo`
- `potrace` for sketches → `brew install potrace`, then `letrasiq trace`

Point Claude Code at this repo; `CLAUDE.md` is the operator guide.

## Layout

```
letrasiq/           Python package + CLI
fonts/<name>/
  spec.json         global style
  glyphs/*.json     parametric skeletons or custom SVG paths
  locked.txt        do-not-regenerate list
  references/       sketches
  CHANGELOG.md
  OFL.txt
  build/            OTF/TTF/WOFF2, UFO, previews/ (binaries gitignored)
CLAUDE.md           how Claude should operate the toolkit
```

Uppercase glyph *files* use UFO-style names (`A_.json`) so they do not collide with `a.json` on case-insensitive disks. Glyph names inside the font stay `A` / `a`.

## CLI

| Command | Purpose |
|---------|---------|
| `letrasiq new <name> --spec spec.json` | Create font folder + MVP glyphs |
| `letrasiq build <name>` | Expand → space/kern → OTF/TTF/WOFF2 + specimen |
| `letrasiq build <name> --glyphs g,R,a` | Build after local glyph edits |
| `letrasiq preview <name>` | Specimen PNG |
| `letrasiq check <name>` | Validate contours, coverage, metrics, spacing |
| `letrasiq compare <name> --ref HEAD` | Before/after PNG vs a git ref |
| `letrasiq fork <name> <new-name>` | Copy sources for a variant |
| `letrasiq trace <name> <glyph> <image>` | Potrace sketch → locked custom glyph |
| `letrasiq import-ufo <name> <path.ufo>` | Import editor glyphs → locked custom |

Sample face: `fonts/letra-sans/` (neo-grotesque MVP).

Font types/subtypes live in `letrasiq/data/classifications.yaml`. Set `classification` + `subtype` in `spec.json` so `new` can fill default knobs; see `CLAUDE.md`.

## Example session (Claude Code)

**Human:** Make a friendly neo-grotesque called “letra-sans”, medium weight, a bit wide.

**Claude (condensed):**

```bash
# write fonts/_tmp_spec.json then:
letrasiq new letra-sans --spec fonts/_tmp_spec.json
letrasiq build letra-sans
# open fonts/letra-sans/build/previews/specimen.png
# critique → tweak weight/width in spec.json → regenerate unlocked → rebuild
letrasiq check letra-sans
```

On accept:

```bash
# append CHANGELOG.md
git add fonts/letra-sans
git commit -m "font(letra-sans): initial neo-grotesque from brief"
```

**Human:** Make a bold version.

```bash
letrasiq fork letra-sans letra-sans-bold
# edit fonts/letra-sans-bold/spec.json → weight 0.72, style_name Bold
# regenerate unlocked templates, build, check, preview
```

**Human:** The R looks wrong — only fix R.

```bash
# edit fonts/letra-sans/glyphs/R_.json
letrasiq build letra-sans
letrasiq compare letra-sans --ref HEAD
# show compare.png
```

**Human:** I dropped a sketch in references/g-sketch.png — use that for g.

```bash
letrasiq trace letra-sans g fonts/letra-sans/references/g-sketch.png
letrasiq build letra-sans
# g is now custom + locked
```

## Adding a parametric glyph

1. Prefer editing `letrasiq/templates.py` constructors (`_caps`, `_lower`, `_digits`, `_punct`) so `new` and regenerations stay complete.
2. Skeletons are polylines (`kind: "stroke"`) or cubic chains (`kind: "curve"`: on, c1, c2, on, …) in UPM coordinates (Y-up).
3. For a one-off face, write `fonts/<name>/glyphs/<file>.json` directly (`A_.json` for `A`).
4. `letrasiq build <name>` then inspect the specimen; run `letrasiq check <name>`.

Custom outline instead of a skeleton:

```json
{
  "type": "custom",
  "path": "M 0 0 L 100 0 L 100 700 L 0 700 Z",
  "width": 200
}
```

Put the glyph name in `locked.txt` if global regenerations must not replace it.

## Tests & CI

```bash
pytest -q
```

GitHub Actions runs pytest on Python 3.11 and 3.12. Trace tests mock potrace when it is absent; a live potrace test runs when `potrace` is on `PATH`.

## License

- **Toolkit code:** MIT (`LICENSE`)
- **Generated fonts:** SIL Open Font License 1.1 (`OFL.txt` per font; embedded in name tables)
