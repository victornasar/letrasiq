"""LetrasIQ command-line interface."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer

from letrasiq import __version__
from letrasiq.check import check_font, format_check_result
from letrasiq.compare import CompareError, compare_font
from letrasiq.pipeline import build_font, create_font, font_dir, fonts_root, fork_font
from letrasiq.preview import render_specimen
from letrasiq.spec import FontSpec

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


@app.command("version")
def cmd_version() -> None:
    typer.echo(__version__)


@app.command("trace", hidden=True)
def cmd_trace_stub() -> None:
    typer.echo("trace: available in Stage 3")
    raise typer.Exit(1)


@app.command("import-ufo", hidden=True)
def cmd_import_stub() -> None:
    typer.echo("import-ufo: available in Stage 3")
    raise typer.Exit(1)


if __name__ == "__main__":
    app()
