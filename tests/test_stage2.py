"""Tests for check, fork, and compare."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from typer.testing import CliRunner

from letrasiq.cli import app
from letrasiq.check import check_font
from letrasiq.pipeline import build_font, create_font, fork_font
from letrasiq.spec import FontSpec

runner = CliRunner()


def _make_font(tmp: Path, name: str = "demo") -> Path:
    fonts = tmp / "fonts"
    fonts.mkdir(exist_ok=True)
    spec = FontSpec(name=name, weight=0.45, contrast=0.15, width=0.55)
    create_font(name, spec, root=fonts)
    build_font(name, root=fonts, skip_preview=False)
    return fonts


def test_check_ok(tmp_path: Path):
    fonts = _make_font(tmp_path)
    result = check_font("demo", root=fonts)
    assert result.ok, result.errors
    r = runner.invoke(app, ["check", "demo", "--fonts", str(fonts)])
    assert r.exit_code == 0, r.output
    assert "OK" in r.output


def test_check_missing_glyph(tmp_path: Path):
    fonts = _make_font(tmp_path)
    # Remove a glyph file
    (fonts / "demo" / "glyphs" / "Q_.json").unlink()
    # Also need to avoid rebuild filling it — check reads disk only
    result = check_font("demo", root=fonts)
    # Compiled font still has Q; source missing is an error
    assert not result.ok
    assert any("missing glyphs" in e for e in result.errors)


def test_fork_copies_and_renames(tmp_path: Path):
    fonts = _make_font(tmp_path)
    dest = fork_font("demo", "demo-bold", root=fonts)
    assert dest.exists()
    spec = FontSpec.load(dest / "spec.json")
    assert spec.name == "demo-bold"
    assert (dest / "glyphs" / "A_.json").exists()
    assert (dest / "glyphs" / "a.json").exists()
    assert not any(dest.glob("build/*.ttf"))
    assert "Forked from" in (dest / "CHANGELOG.md").read_text(encoding="utf-8")

    r = runner.invoke(app, ["fork", "demo", "demo-condensed", "--fonts", str(fonts)])
    assert r.exit_code == 0, r.output
    assert (fonts / "demo-condensed" / "spec.json").exists()


def test_compare_against_git_ref(tmp_path: Path):
    # Build a tiny git repo containing fonts/
    repo = tmp_path / "repo"
    repo.mkdir()
    fonts = repo / "fonts"
    fonts.mkdir()
    spec = FontSpec(name="demo", weight=0.4, contrast=0.1, width=0.5)
    create_font("demo", spec, root=fonts)
    build_font("demo", root=fonts)

    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    # Don't commit binaries — commit sources + preview
    subprocess.run(["git", "add", "fonts/demo/spec.json", "fonts/demo/glyphs",
                    "fonts/demo/locked.txt", "fonts/demo/OFL.txt",
                    "fonts/demo/CHANGELOG.md"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "add", "-f", "fonts/demo/build/previews/specimen.png"],
                   cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "initial demo"], cwd=repo, check=True, capture_output=True)

    # Mutate weight in working tree and rebuild
    s = FontSpec.load(fonts / "demo" / "spec.json")
    s.weight = 0.7
    s.save(fonts / "demo" / "spec.json")
    build_font("demo", root=fonts)

    r = runner.invoke(app, ["compare", "demo", "--ref", "HEAD", "--fonts", str(fonts)])
    assert r.exit_code == 0, r.output
    compare_png = fonts / "demo" / "build" / "previews" / "compare.png"
    assert compare_png.exists()
    assert compare_png.stat().st_size > 1000
