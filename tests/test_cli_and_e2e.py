import json
from pathlib import Path

from fontTools.ttLib import TTFont
from typer.testing import CliRunner

from letrasiq.cli import app

runner = CliRunner()


def test_new_build_preview_e2e(tmp_path: Path):
    fonts = tmp_path / "fonts"
    fonts.mkdir()
    spec_path = tmp_path / "spec.json"
    spec_path.write_text(json.dumps({"x_height": 510, "classification": "sans-serif", "subtype": "humanistic"}), encoding="utf-8")

    r = runner.invoke(app, ["new", "demo", "--spec", str(spec_path), "--fonts", str(fonts)])
    assert r.exit_code == 0, r.output
    font = fonts / "demo"
    for name in ("spec.json", "design.json", "draw.py", "OFL.txt"):
        assert (font / name).exists()

    r = runner.invoke(app, ["build", "demo", "--fonts", str(fonts)])
    assert r.exit_code == 0, r.output
    assert (font / "glyphs" / "H_.json").exists()
    assert (font / "glyphs" / "n.json").exists()
    assert (font / "build" / "previews" / "tester.html").exists()
    assert (font / "build" / "previews" / "specimen.png").stat().st_size > 1000

    cmap = TTFont(next((font / "build").glob("*.ttf"))).getBestCmap()
    assert all(code in cmap for code in range(32, 127))

    # A new font is complete from its design sheet, with no drawing needed first.
    r = runner.invoke(app, ["check", "demo", "--fonts", str(fonts)])
    assert r.exit_code == 0, r.output

    r = runner.invoke(app, ["preview", "demo", "--fonts", str(fonts)])
    assert r.exit_code == 0, r.output


def test_old_parametric_glyph_is_rejected(tmp_path: Path):
    from letrasiq.glyph import GlyphSource
    import pytest

    with pytest.raises(ValueError, match="parametric"):
        GlyphSource.from_dict("A", {"type": "parametric", "skeleton": []})
