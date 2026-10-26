"""LetrasIQ command-line interface."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer

from letrasiq import __version__
from letrasiq.check import check_font, format_check_result
from letrasiq.compare import CompareError, compare_font
from letrasiq.import_ufo import ImportError_, import_ufo
from letrasiq.pipeline import build_font, create_font, font_dir, fonts_root, fork_font
from letrasiq.preview import render_specimen
from letrasiq.spec import FontSpec
from letrasiq.trace import TraceError, trace_glyph

app = typer.Typer(
    name="letrasiq",
    help="Local font-design toolkit operated through Claude Code.",
    no_args_is_help=True,
)


@app.callback()
def main() -> None:
    """LetrasIQ — parametric local fonts."""


@app.command("new")
def cmd_new(
    name: str = typer.Argument(..., help="Font folder name, e.g. letra-sans"),
    spec: Path = typer.Option(..., "--spec", help="Path to spec.json"),
    fonts: Optional[Path] = typer.Option(None, "--fonts", help="Fonts root directory"),
) -> None:
    """Create a font folder from a style spec."""
    data = json.loads(Path(spec).read_text(encoding="utf-8"))
    if "name" not in data:
        data["name"] = name
    font_spec = FontSpec.from_dict(data)
    d = create_font(name, font_spec, root=fonts or fonts_root())
    typer.echo(f"Created {d}")


@app.command("build")
def cmd_build(
    name: str = typer.Argument(..., help="Font name"),
    glyphs: Optional[str] = typer.Option(
        None, "--glyphs", help="Comma-separated glyph names to prioritize"
    ),
    fonts: Optional[Path] = typer.Option(None, "--fonts", help="Fonts root directory"),
    no_preview: bool = typer.Option(False, "--no-preview"),
) -> None:
    """Run the full pipeline and output fonts."""
    only = [g.strip() for g in glyphs.split(",")] if glyphs else None
    outputs = build_font(
        name,
        root=fonts or fonts_root(),
        only_glyphs=only,
        skip_preview=no_preview,
    )
    for key, path in outputs.items():
        typer.echo(f"{key}: {path}")


@app.command("preview")
def cmd_preview(
    name: str = typer.Argument(..., help="Font name"),
    fonts: Optional[Path] = typer.Option(None, "--fonts", help="Fonts root directory"),
) -> None:
    """Render a specimen PNG."""
    d = font_dir(name, fonts or fonts_root())
    build_dir = d / "build"
    if not any(build_dir.glob("*.ttf")) and not any(build_dir.glob("*.otf")):
        typer.echo("No compiled font found; running build first…")
        build_font(name, root=fonts or fonts_root(), skip_preview=True)
    path = render_specimen(d)
    typer.echo(str(path))


@app.command("check")
def cmd_check(
    name: str = typer.Argument(..., help="Font name"),
    fonts: Optional[Path] = typer.Option(None, "--fonts", help="Fonts root directory"),
) -> None:
    """Validate glyph coverage, contours, metrics, and spacing."""
    result = check_font(name, root=fonts or fonts_root())
    typer.echo(format_check_result(result))
    if not result.ok:
        raise typer.Exit(1)


@app.command("compare")
def cmd_compare(
    name: str = typer.Argument(..., help="Font name"),
    ref: str = typer.Option(..., "--ref", help="Git ref for the before state"),
    fonts: Optional[Path] = typer.Option(None, "--fonts", help="Fonts root directory"),
) -> None:
    """Render a before/after specimen against a git ref."""
    try:
        path = compare_font(name, ref, root=fonts or fonts_root())
    except CompareError as e:
        typer.echo(f"compare failed: {e}", err=True)
        raise typer.Exit(1) from e
    typer.echo(str(path))


@app.command("fork")
def cmd_fork(
    name: str = typer.Argument(..., help="Source font name"),
    new_name: str = typer.Argument(..., help="New font folder name"),
    fonts: Optional[Path] = typer.Option(None, "--fonts", help="Fonts root directory"),
) -> None:
    """Copy a font as the start of a variant."""
    try:
        d = fork_font(name, new_name, root=fonts or fonts_root())
    except (FileNotFoundError, FileExistsError) as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(1) from e
    typer.echo(f"Forked {name} → {d}")


@app.command("trace")
def cmd_trace(
    name: str = typer.Argument(..., help="Font name"),
    glyph: str = typer.Argument(..., help="Glyph name, e.g. g or ampersand"),
    image: Path = typer.Argument(..., help="Sketch image path"),
    fonts: Optional[Path] = typer.Option(None, "--fonts", help="Fonts root directory"),
    no_lock: bool = typer.Option(False, "--no-lock", help="Do not add glyph to locked.txt"),
    threshold: int = typer.Option(128, "--threshold", help="Binarization threshold 0-255"),
) -> None:
    """Vectorize a sketch with potrace into a custom glyph."""
    try:
        dest = trace_glyph(
            name,
            glyph,
            image,
            root=fonts or fonts_root(),
            lock=not no_lock,
            threshold=threshold,
        )
    except TraceError as e:
        typer.echo(f"trace failed: {e}", err=True)
        raise typer.Exit(1) from e
    typer.echo(str(dest))


@app.command("import-ufo")
def cmd_import_ufo(
    name: str = typer.Argument(..., help="Font name"),
    ufo: Path = typer.Argument(..., help="Path to a .ufo directory"),
    fonts: Optional[Path] = typer.Option(None, "--fonts", help="Fonts root directory"),
    glyphs: Optional[str] = typer.Option(
        None, "--glyphs", help="Comma-separated glyph names (default: all)"
    ),
) -> None:
    """Import glyphs from FontForge/other UFO editors; lock them."""
    only = [g.strip() for g in glyphs.split(",")] if glyphs else None
    try:
        imported = import_ufo(
            name, ufo, root=fonts or fonts_root(), glyphs=only
        )
    except ImportError_ as e:
        typer.echo(f"import-ufo failed: {e}", err=True)
        raise typer.Exit(1) from e
    typer.echo(f"imported {len(imported)} glyph(s): {', '.join(imported[:20])}"
               + ("…" if len(imported) > 20 else ""))


@app.command("version")
def cmd_version() -> None:
    typer.echo(__version__)


if __name__ == "__main__":
    app()
