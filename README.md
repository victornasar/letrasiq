# LetrasIQ

Local font-design toolkit operated through Claude Code. No web app, no API keys, no accounts.

## Setup

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Optional:

- [FontForge](https://fontforge.org/) for external glyph edits (`import-ufo`, Stage 3)
- `potrace` for sketch tracing (`brew install potrace`, Stage 3)

## Quick start

```bash
# write a spec, then:
letrasiq new letra-sans --spec path/to/spec.json
letrasiq build letra-sans
letrasiq preview letra-sans
# open fonts/letra-sans/build/previews/specimen.png
```

Sample face: `fonts/letra-sans/` (neo-grotesque MVP). Uppercase glyph files use UFO-style names (`A_.json`) so they do not collide with `a.json` on case-insensitive disks.

## License

MIT for the toolkit. Generated fonts default to the SIL Open Font License (OFL-1.1).
