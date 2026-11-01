"""Font creation and build orchestration."""

from __future__ import annotations

import shutil
from importlib import resources
from pathlib import Path

import pathops

from letrasiq.compile import build_ufo, compile_otf_ttf, ensure_ofl, set_name_table_license
from letrasiq.drawing import load_design, regenerate_drawn
from letrasiq.glyph import GlyphSource, glyph_name_from_path, load_locked
from letrasiq.kerning import build_kerning
from letrasiq.outline import cleanup_path, path_bounds, svg_path_to_pathops
from letrasiq.preview import render_detail, render_detail_core, render_review, render_specimen
from letrasiq.spec import FontSpec
from letrasiq.tester import render_tester


def fonts_root(start: Path | None = None) -> Path:
    """Locate the repo fonts/ directory walking up from start or cwd."""
    cur = (start or Path.cwd()).resolve()
    for p in [cur, *cur.parents]:
        candidate = p / "fonts"
        if candidate.is_dir() or (p / "pyproject.toml").exists():
            fonts = p / "fonts"
            fonts.mkdir(exist_ok=True)
            return fonts
    fonts = Path.cwd() / "fonts"
    fonts.mkdir(exist_ok=True)
    return fonts


def font_dir(name: str, root: Path | None = None) -> Path:
    return (root or fonts_root()) / name


def create_font(name: str, spec: FontSpec, root: Path | None = None) -> Path:
    errors = spec.validate()
    if errors:
        raise ValueError("Invalid spec: " + "; ".join(errors))
    spec.name = name
    d = font_dir(name, root)
    if d.exists():
        raise FileExistsError(f"Font already exists: {d}")
    (d / "glyphs").mkdir(parents=True)
    (d / "references").mkdir(parents=True)
    (d / "build" / "previews").mkdir(parents=True)
    (d / "locked.txt").write_text("", encoding="utf-8")
    (d / "CHANGELOG.md").write_text(
        f"# {spec.family_name()} Changelog\n\n- Created from spec (v{spec.version})\n",
        encoding="utf-8",
    )
    ensure_ofl(d)
    spec.save(d / "spec.json")
    data = resources.files("letrasiq").joinpath("data")
    (d / "design.json").write_text(data.joinpath("design_template.json").read_text(encoding="utf-8"), encoding="utf-8")
    (d / "draw.py").write_text(data.joinpath("draw_template.py.txt").read_text(encoding="utf-8"), encoding="utf-8")
    return d


def load_glyph_sources(d: Path) -> dict[str, GlyphSource]:
    sources: dict[str, GlyphSource] = {}
    gdir = d / "glyphs"
    for path in sorted(gdir.glob("*.json")):
        name = glyph_name_from_path(path)
        src = GlyphSource.load(path)
        src.name = name
        sources[name] = src
    return sources


def build_font(
    name: str,
    root: Path | None = None,
    skip_preview: bool = False,
) -> dict[str, Path]:
    d = font_dir(name, root)
    if not d.exists():
        raise FileNotFoundError(f"Font not found: {d}")
    spec = FontSpec.load(d / "spec.json")
    if (d / "draw.py").exists():
        regenerate_drawn(d, spec, load_locked(d / "locked.txt"))
    sources = load_glyph_sources(d)
    if not sources:
        raise ValueError(f"{name} has no glyphs: add draw.py, trace, or import a UFO")

    placed: dict[str, tuple[pathops.Path, int]] = {"space": (pathops.Path(), spec.space_advance())}
    for gname, src in sources.items():
        if gname == "space":
            placed[gname] = (pathops.Path(), src.width or spec.space_advance())
        elif src.type == "drawn":
            # Already spaced and tidied by draw.py.
            placed[gname] = (svg_path_to_pathops(src.path or ""), src.width or 0)
        else:
            path = cleanup_path(svg_path_to_pathops(src.path or ""))
            bounds = path_bounds(path)
            # Without an explicit width, mirror the left sidebearing on the right.
            inferred = int(round(bounds[2] + max(bounds[0], 0))) if bounds else spec.space_advance()
            placed[gname] = (path, src.width or inferred)

    design = load_design(d, spec)
    # Kerning would break a monospace font's single advance.
    kern = {} if design.advance else build_kerning(placed, target_gap=design.kern_gap, damping=0.75, clamp=(-90.0, 0.0))
    ufo = build_ufo(
        spec, placed, kerning=kern, fixed_advance=design.advance,
        anchors={name: src.anchors for name, src in sources.items() if src.anchors},
    )

    build_dir = d / "build"
    build_dir.mkdir(parents=True, exist_ok=True)
    # Clear old binaries but keep previews
    for pattern in ("*.otf", "*.ttf", "*.woff2"):
        for p in build_dir.glob(pattern):
            p.unlink()

    outputs = compile_otf_ttf(ufo, build_dir, spec.family_name(), spec.style_name)
    for key in ("otf", "ttf", "woff2"):
        if key in outputs and outputs[key].exists():
            set_name_table_license(outputs[key], spec.family_name())

    if not skip_preview:
        outputs["preview"] = render_specimen(d, spec)
        outputs["review"] = render_review(d, spec)
        outputs["detail"] = render_detail(d, spec)
        outputs["detail_core"] = render_detail_core(d, spec)
        outputs["tester"] = render_tester(d, spec)
        # Imported here because the report uses check, which uses this module.
        from letrasiq.report import render_report

        outputs["report"] = render_report(d, spec)

    return outputs


def fork_font(name: str, new_name: str, root: Path | None = None) -> Path:
    """Copy a font folder as the start of a variant (no build/ binaries)."""
    fonts = root or fonts_root()
    src = font_dir(name, fonts)
    dest = font_dir(new_name, fonts)
    if not src.exists():
        raise FileNotFoundError(f"Font not found: {src}")
    if dest.exists():
        raise FileExistsError(f"Font already exists: {dest}")

    # Copy source tree minus build artifacts
    shutil.copytree(
        src,
        dest,
        ignore=shutil.ignore_patterns(
            "build",
            "*.otf",
            "*.ttf",
            "*.woff2",
            "*.ufo",
            "__pycache__",
        ),
    )
    (dest / "build" / "previews").mkdir(parents=True, exist_ok=True)

    spec = FontSpec.load(dest / "spec.json")
    spec.name = new_name
    spec.save(dest / "spec.json")

    # Fresh changelog note; keep OFL/locked/glyphs as copied
    changelog = dest / "CHANGELOG.md"
    family = spec.family_name()
    line = f"- Forked from `{name}` as `{new_name}`\n"
    if changelog.exists():
        text = changelog.read_text(encoding="utf-8")
        # Retitle
        lines = text.splitlines()
        if lines and lines[0].startswith("#"):
            lines[0] = f"# {family} Changelog"
            text = "\n".join(lines) + ("\n" if not text.endswith("\n") else "")
        changelog.write_text(text + ("" if text.endswith("\n") else "\n") + line, encoding="utf-8")
    else:
        changelog.write_text(f"# {family} Changelog\n\n{line}", encoding="utf-8")

    ensure_ofl(dest)
    return dest
