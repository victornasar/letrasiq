import json
from pathlib import Path

from typer.testing import CliRunner
from fontTools.ttLib import TTFont

from letrasiq.cli import app
from letrasiq.glyph import MVP_GLYPHS

runner = CliRunner()


def test_new_build_preview_e2e(tmp_path: Path):
    fonts = tmp_path / "fonts"
    fonts.mkdir()
    spec = {
        "name": "letra-sans",
        "version": "0.1.0",
        "weight": 0.45,
        "contrast": 0.15,
        "width": 0.55,
        "slant": 0,
        "serif_style": "none",
        "terminal_style": "flat",
        "corner_roundness": 0.2,
        "aperture": 0.55,
        "mood": "neutral",
    }
    spec_path = tmp_path / "spec.json"
    spec_path.write_text(json.dumps(spec), encoding="utf-8")

    r = runner.invoke(app, ["new", "letra-sans", "--spec", str(spec_path), "--fonts", str(fonts)])
    assert r.exit_code == 0, r.output
    font = fonts / "letra-sans"
    assert (font / "spec.json").exists()
    assert (font / "OFL.txt").exists()
    assert (font / "glyphs" / "A_.json").exists()
    assert (font / "glyphs" / "a.json").exists()
    for name in ("zero", "period", "space"):
        assert (font / "glyphs" / f"{name}.json").exists()

    r = runner.invoke(app, ["build", "letra-sans", "--fonts", str(fonts)])
    assert r.exit_code == 0, r.output

    ttf = next((font / "build").glob("*.ttf"))
    otf = next((font / "build").glob("*.otf"))
    assert ttf.exists() and otf.exists()
    preview = font / "build" / "previews" / "specimen.png"
    assert preview.exists() and preview.stat().st_size > 1000

    ft = TTFont(ttf)
    glyph_order = ft.getGlyphOrder()
    for name in MVP_GLYPHS:
        assert name in glyph_order
    # cmap has basic ASCII
    cmap = ft.getBestCmap()
    assert ord("A") in cmap and ord("a") in cmap and ord("0") in cmap

    r = runner.invoke(app, ["preview", "letra-sans", "--fonts", str(fonts)])
    assert r.exit_code == 0, r.output
