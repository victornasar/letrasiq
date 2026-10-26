"""Before/after specimen compare against a git ref."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from letrasiq.pipeline import build_font, font_dir, fonts_root
from letrasiq.preview import render_compare_sheet, render_specimen
from letrasiq.spec import FontSpec


class CompareError(RuntimeError):
    pass


def _git_root(start: Path) -> Path:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=start,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        return Path(out)
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        raise CompareError(
            f"compare requires a git repository (not found from {start})"
        ) from e


def _git_show_path(repo: Path, ref: str, rel: str) -> bytes | None:
    try:
        return subprocess.check_output(
            ["git", "show", f"{ref}:{rel}"],
            cwd=repo,
            stderr=subprocess.DEVNULL,
        )
    except subprocess.CalledProcessError:
        return None


def _list_ref_glyph_files(repo: Path, ref: str, font_rel: str) -> list[str]:
    """List glyph JSON paths under font_rel/glyphs at ref via git ls-tree."""
    try:
        out = subprocess.check_output(
            ["git", "ls-tree", "-r", "--name-only", ref, f"{font_rel}/glyphs"],
            cwd=repo,
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except subprocess.CalledProcessError as e:
        raise CompareError(f"git ref not found or no glyphs at {ref}:{font_rel}/glyphs") from e
    return [line.strip() for line in out.splitlines() if line.strip().endswith(".json")]


def materialize_font_at_ref(
    name: str,
    ref: str,
    dest: Path,
    root: Path | None = None,
) -> Path:
    """Extract font source (spec, glyphs, locked, OFL) at ref into dest/<name>."""
    fonts = (root or fonts_root()).resolve()
    current = font_dir(name, fonts)
    if not current.exists():
        raise CompareError(f"font not found: {current}")

    repo = _git_root(current)
    try:
        font_rel = str(current.resolve().relative_to(repo))
    except ValueError as e:
        raise CompareError(f"font folder {current} is not inside git root {repo}") from e

    # Ensure ref exists
    try:
        subprocess.check_output(
            ["git", "rev-parse", "--verify", ref],
            cwd=repo,
            stderr=subprocess.DEVNULL,
        )
    except subprocess.CalledProcessError as e:
        raise CompareError(f"git ref not found: {ref}") from e

    out_font = dest / name
    (out_font / "glyphs").mkdir(parents=True)
    (out_font / "references").mkdir(parents=True)
    (out_font / "build" / "previews").mkdir(parents=True)

    # Required: spec.json
    spec_bytes = _git_show_path(repo, ref, f"{font_rel}/spec.json")
    if spec_bytes is None:
        raise CompareError(f"no spec.json at {ref}:{font_rel}/spec.json")
    (out_font / "spec.json").write_bytes(spec_bytes)

    for optional in ("locked.txt", "OFL.txt", "CHANGELOG.md"):
        data = _git_show_path(repo, ref, f"{font_rel}/{optional}")
        if data is not None:
            (out_font / optional).write_bytes(data)
        elif optional == "locked.txt":
            (out_font / optional).write_text("", encoding="utf-8")

    glyph_paths = _list_ref_glyph_files(repo, ref, font_rel)
    if not glyph_paths:
        raise CompareError(f"no glyph JSON files at {ref}:{font_rel}/glyphs")
    for rel in glyph_paths:
        data = _git_show_path(repo, ref, rel)
        if data is None:
            continue
        (out_font / "glyphs" / Path(rel).name).write_bytes(data)

    return out_font


def compare_font(
    name: str,
    ref: str,
    root: Path | None = None,
    out_path: Path | None = None,
) -> Path:
    """Build current + ref versions and write side-by-side compare.png."""
    fonts = root or fonts_root()
    current = font_dir(name, fonts)
    if not current.exists():
        raise CompareError(f"font not found: {current}")

    # Ensure current has a specimen (build if needed)
    cur_preview = current / "build" / "previews" / "specimen.png"
    if not cur_preview.exists() or not any((current / "build").glob("*.ttf")):
        build_font(name, root=fonts, skip_preview=False)
    else:
        # refresh specimen from current binaries
        render_specimen(current)

    with tempfile.TemporaryDirectory(prefix="letrasiq-compare-") as tmp:
        tmp_path = Path(tmp)
        ref_font = materialize_font_at_ref(name, ref, tmp_path / "ref_fonts", root=fonts)
        # Build ref into its own fonts root layout: tmp/ref_fonts/<name>
        build_font(name, root=tmp_path / "ref_fonts", skip_preview=False)
        ref_preview = ref_font / "build" / "previews" / "specimen.png"
        if not ref_preview.exists():
            raise CompareError("failed to render specimen for git ref")

        out = out_path or (current / "build" / "previews" / "compare.png")
        # Shorten label
        short_ref = ref if len(ref) <= 20 else ref[:17] + "…"
        return render_compare_sheet(
            ref_preview,
            current / "build" / "previews" / "specimen.png",
            out,
            label_before=f"before ({short_ref})",
            label_after="after (working tree)",
        )
