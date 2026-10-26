"""Font creation and build orchestration."""

from __future__ import annotations

import shutil
from pathlib import Path

import pathops

from letrasiq.cleanup import cleanup_path
from letrasiq.compile import build_ufo, compile_otf_ttf, ensure_ofl, set_name_table_license
from letrasiq.expand import expand_glyph, path_bounds
from letrasiq.glyph import (
    GlyphSource,
    MVP_GLYPHS,
    glyph_filename,
    glyph_name_from_path,
    load_locked,
)
from letrasiq.kerning import build_kerning
from letrasiq.preview import render_specimen
from letrasiq.spacing import advance_width, shift_path
from letrasiq.spec import FontSpec
from letrasiq.templates import build_mvp_glyphs


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
    from letrasiq.classification import fill_spec_from_taxonomy

    fill_spec_from_taxonomy(spec, overwrite=False)
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
        f"# {spec.family_name()} Changelog\n\n"
        f"- Initial create from spec (v{spec.version})\n",
        encoding="utf-8",
    )
    ensure_ofl(d)
    spec.save(d / "spec.json")
    glyphs = build_mvp_glyphs(spec)
    for gname, glyph in glyphs.items():
        glyph.save(d / "glyphs" / glyph_filename(gname))
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


# Back-compat alias
_load_glyph_sources = load_glyph_sources


def build_font(
    name: str,
    root: Path | None = None,
    only_glyphs: list[str] | None = None,
    skip_preview: bool = False,
) -> dict[str, Path]:
    d = font_dir(name, root)
    if not d.exists():
        raise FileNotFoundError(f"Font not found: {d}")
    spec = FontSpec.load(d / "spec.json")
    locked = load_locked(d / "locked.txt")
    sources = _load_glyph_sources(d)

    # Ensure MVP coverage: fill missing from templates (unless locked missing — still generate)
    templates = build_mvp_glyphs(spec)
    for gname in MVP_GLYPHS:
        if gname not in sources:
            sources[gname] = templates[gname]
            sources[gname].save(d / "glyphs" / glyph_filename(gname))

    # Partial rebuild: still need all glyphs for font compile, but regenerate
    # parametric unlocked ones always from current skeleton+spec.
    placed: dict[str, tuple[pathops.Path, int]] = {}

    target_names = list(sources.keys())
    if only_glyphs:
        # rebuild requested glyphs' outlines; others loaded from previous UFO if present —
        # for MVP simplicity, always rebuild full font but only re-expand requested
        # when only_glyphs set — still expand all for a consistent binary.
        pass

    for gname, src in sources.items():
        if only_glyphs and gname not in only_glyphs and gname != "space":
            # Still expand — full font required. only_glyphs is a filter for
            # which parametric glyphs to refresh from disk (all are on disk).
            pass

        if src.type == "parametric" and gname in locked and gname != "space":
            # Locked parametric: still use the on-disk skeleton (hand-edited),
            # do not replace from templates — already loaded from disk.
            pass

        if gname == "space":
            placed[gname] = (pathops.Path(), spec.space_advance())
            continue

        path = expand_glyph(src, spec)
        path = cleanup_path(path)
        bounds = path_bounds(path)
        adv, left, right = advance_width(gname, path, spec, explicit_width=src.width)
        if bounds is not None:
            # shift so xmin == left sidebearing
            dx = left - bounds[0]
            path = shift_path(path, dx)
        placed[gname] = (path, adv)

    kern = build_kerning(placed, target_gap=spec.stroke_base() * 0.55)
    ufo = build_ufo(spec, placed, kerning=kern)

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

    return outputs


def regenerate_unlocked_from_templates(name: str, root: Path | None = None) -> int:
    """Rewrite parametric unlocked glyphs from built-in templates (after global spec change)."""
    d = font_dir(name, root)
    spec = FontSpec.load(d / "spec.json")
    locked = load_locked(d / "locked.txt")
    templates = build_mvp_glyphs(spec)
    count = 0
    for gname, glyph in templates.items():
        if gname in locked:
            continue
        dest = d / "glyphs" / glyph_filename(gname)
        if dest.exists():
            existing = GlyphSource.load(dest)
            existing.name = gname
            if existing.type == "custom":
                continue
        glyph.save(dest)
        count += 1
    return count


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
