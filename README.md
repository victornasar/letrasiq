# LetrasIQ

A local font engine operated through **Claude Code**. You describe the characteristics you want; Claude turns them into a design sheet and real Bézier outlines, then builds OTF, TTF and WOFF2 files. No web app, no API keys, no accounts.

## Setup

```bash
python3.12 -m venv .venv   # any Python 3.11+
source .venv/bin/activate
pip install -e ".[dev]"
letrasiq version
```

Optional:

- `potrace` for sketches: `brew install potrace`, then `letrasiq trace`
- [FontForge](https://fontforge.org/) or any UFO editor, then `letrasiq import-ufo`

Point Claude Code at this repo; `CLAUDE.md` is the operator guide.

## How a font is made

```
brief → design.json (measurable choices) → draw.py (outlines) → letrasiq build → letrasiq check → tester.html
```

- **`letrasiq/drawing.py`** turns spines and a nib model into cubic outlines, so stroke thickness follows direction and related letters share parts.
- **`letrasiq/quality.py`** flags missed extremes, kinks, tiny segments, inconsistent stems and wrong overshoot.
- **`letrasiq/data/craft.md`** maps brief wording to design values.

## Layout

```
letrasiq/           Python package + CLI
fonts/<name>/
  spec.json         identity and metrics
  design.json       design sheet: brief, values, spacing, reasons
  draw.py           calls the engine's construction, plus any font-only glyphs
  glyphs/*.json     generated outlines, plus locked hand edits and traces
  locked.txt        glyphs draw.py must leave alone
  references/       sketches
  CHANGELOG.md
  OFL.txt
  build/            compiled fonts and UFO (gitignored), previews/
```

## CLI

| Command | Purpose |
|---------|---------|
| `letrasiq new <name> [--spec spec.json]` | Create a font folder that builds completely from its design sheet |
| `letrasiq build <name>` | Draw, kern and compile, then generate previews and the tester |
| `letrasiq release <name>` | Build, then assemble the release package, specimen and review packet in `build/release/` |
| `letrasiq check <name>` | Validate coverage, outlines and consistency |
| `letrasiq preview <name>` | Re-render the specimen PNG |
| `letrasiq compare <name> --ref HEAD` | Before/after PNG against a git ref |
| `letrasiq fork <name> <new-name>` | Copy sources for a variant |
| `letrasiq trace <name> <glyph> <image>` | Potrace a sketch into a locked glyph |
| `letrasiq import-ufo <name> <path.ufo>` | Import editor glyphs as locked outlines |

`build` writes four previews to `build/previews/`: `tester.html` (type your own text, compare with a system font), `report.html` (each production stage as passed, failed or needing a person), `review.png` (shapes and text at several sizes) and `detail.png` (outlines with their points).

`fonts/` holds three reference fonts built from sheets: a sans, a serif and a monospace.

## License

Fonts ship under the SIL Open Font License (`OFL.txt` in each font). The toolkit is MIT.
