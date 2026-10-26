"""Tests for trace and import-ufo."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from unittest.mock import patch

import pytest
import ufoLib2
from typer.testing import CliRunner

from letrasiq.cli import app
from letrasiq.glyph import GlyphSource, load_locked
from letrasiq.import_ufo import import_ufo
from letrasiq.pipeline import build_font, create_font
from letrasiq.spec import FontSpec
from letrasiq.trace import (
    TraceError,
    extract_svg_path_data,
    normalize_path_to_metrics,
    require_potrace,
    trace_glyph,
)

runner = CliRunner()
HAS_POTRACE = shutil.which("potrace") is not None


def _font(tmp: Path, name: str = "demo") -> Path:
    fonts = tmp / "fonts"
    fonts.mkdir(exist_ok=True)
    create_font(name, FontSpec(name=name), root=fonts)
    return fonts


def test_extract_svg_path_data():
    svg = """<?xml version="1.0"?>
    <svg><path d="M 0 0 L 10 0 L 10 10 Z"/><path d='M 20 20 L 30 20 Z'/></svg>"""
    d = extract_svg_path_data(svg)
    assert "M 0 0" in d and "M 20 20" in d


def test_normalize_path_to_metrics():
    spec = FontSpec(name="t", cap_height=700)
    d, adv = normalize_path_to_metrics("M 0 0 L 100 0 L 100 200 L 0 200 Z", spec)
    assert "M" in d and "Z" in d
    assert adv > 0


def test_import_ufo_locks_glyphs(tmp_path: Path):
    fonts = _font(tmp_path)
    # Build a tiny UFO with a custom "Q" square
    ufo_dir = tmp_path / "Edited.ufo"
    ufo = ufoLib2.Font()
    ufo.info.familyName = "Edited"
    ufo.info.unitsPerEm = 1000
    g = ufo.newGlyph("Q")
    g.width = 600
    g.unicodes = [ord("Q")]
    pen = g.getPen()
    pen.moveTo((50, 50))
    pen.lineTo((550, 50))
    pen.lineTo((550, 650))
    pen.lineTo((50, 650))
    pen.closePath()
    # also import a lowercase a
    a = ufo.newGlyph("a")
    a.width = 500
    pen = a.getPen()
    pen.moveTo((40, 0))
    pen.lineTo((460, 0))
    pen.lineTo((460, 500))
    pen.lineTo((40, 500))
    pen.closePath()
    ufo.save(ufo_dir)

    imported = import_ufo("demo", ufo_dir, root=fonts, glyphs=["Q", "a"])
    assert set(imported) == {"Q", "a"}
    locked = load_locked(fonts / "demo" / "locked.txt")
    assert "Q" in locked and "a" in locked

    q = GlyphSource.load(fonts / "demo" / "glyphs" / "Q_.json")
    assert q.type == "custom"
    assert q.path and "M" in q.path
    assert q.width == 600

    a_src = GlyphSource.load(fonts / "demo" / "glyphs" / "a.json")
    assert a_src.type == "custom"

    r = runner.invoke(
        app,
        ["import-ufo", "demo", str(ufo_dir), "--fonts", str(fonts), "--glyphs", "Q"],
    )
    assert r.exit_code == 0, r.output

    # Build still works with custom Q
    outs = build_font("demo", root=fonts, skip_preview=True)
    assert outs["ttf"].exists()


def test_trace_requires_potrace_message(tmp_path: Path):
    fonts = _font(tmp_path)
    img = tmp_path / "sketch.png"
    # black square on white
    from PIL import Image, ImageDraw

    im = Image.new("RGB", (200, 200), "white")
    draw = ImageDraw.Draw(im)
    draw.ellipse((40, 40, 160, 160), fill="black")
    im.save(img)

    with patch("letrasiq.trace.shutil.which", return_value=None):
        with pytest.raises(TraceError, match="potrace"):
            require_potrace()
        r = runner.invoke(
            app, ["trace", "demo", "o", str(img), "--fonts", str(fonts)]
        )
        assert r.exit_code == 1
        assert "potrace" in r.output.lower()


def test_trace_with_mocked_potrace(tmp_path: Path):
    fonts = _font(tmp_path)
    img = tmp_path / "sketch.png"
    from PIL import Image, ImageDraw

    im = Image.new("RGB", (200, 200), "white")
    ImageDraw.Draw(im).rectangle((30, 20, 170, 180), fill="black")
    im.save(img)

    fake_svg = """<?xml version='1.0'?>
    <svg xmlns='http://www.w3.org/2000/svg'>
      <path d='M 10 10 L 190 10 L 190 190 L 10 190 Z'/>
    </svg>"""

    def fake_run_potrace(pbm_path, svg_path, potrace_bin=None):
        svg_path.write_text(fake_svg, encoding="utf-8")
        return fake_svg

    with patch("letrasiq.trace.require_potrace", return_value="/usr/bin/potrace"):
        with patch("letrasiq.trace.run_potrace", side_effect=fake_run_potrace):
            dest = trace_glyph("demo", "I", img, root=fonts)
    assert dest.exists()
    src = GlyphSource.load(dest)
    assert src.type == "custom"
    assert src.path and "M" in src.path
    assert "I" in load_locked(fonts / "demo" / "locked.txt")
    assert (fonts / "demo" / "references" / "I.png").exists()


@pytest.mark.skipif(not HAS_POTRACE, reason="system potrace not installed")
def test_trace_live_potrace(tmp_path: Path):
    fonts = _font(tmp_path)
    img = tmp_path / "blob.png"
    from PIL import Image, ImageDraw

    im = Image.new("RGB", (300, 300), "white")
    ImageDraw.Draw(im).ellipse((50, 40, 250, 260), fill="black")
    im.save(img)
    dest = trace_glyph("demo", "O", img, root=fonts)
    src = GlyphSource.load(dest)
    assert src.type == "custom"
    assert src.width and src.width > 100
