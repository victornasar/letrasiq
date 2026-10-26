"""Render specimen PNG previews."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from fontTools.ttLib import TTFont

from letrasiq.glyph import MVP_GLYPHS, glyph_char
from letrasiq.spec import FontSpec

PANGRAM = "The quick brown fox jumps over the lazy dog."
SAMPLE_WORDS = ["LetrasIQ", "hamburgefonstiv", "Typography", "1234567890", "AEIOU aeiou"]


def _load_pillow_font(font_path: Path, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(font_path), size=size)


def _pick_font_file(build_dir: Path, family: str, style: str = "Regular") -> Path:
    stem = f"{family.replace(' ', '')}-{style}"
    for ext in ("ttf", "otf"):
        p = build_dir / f"{stem}.{ext}"
        if p.exists():
            return p
    # fallback: any ttf/otf
    for ext in ("ttf", "otf"):
        found = list(build_dir.glob(f"*.{ext}"))
        if found:
            return found[0]
    raise FileNotFoundError(f"No compiled font in {build_dir}")


def render_specimen(
    font_dir: Path,
    spec: FontSpec | None = None,
    out_path: Path | None = None,
) -> Path:
    spec = spec or FontSpec.load(font_dir / "spec.json")
    build_dir = font_dir / "build"
    font_path = _pick_font_file(build_dir, spec.family_name(), spec.style_name)
    out_dir = build_dir / "previews"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_path or (out_dir / "specimen.png")

    W, H = 1400, 1800
    img = Image.new("RGB", (W, H), (250, 248, 244))
    draw = ImageDraw.Draw(img)

    title_font = _load_pillow_font(font_path, 64)
    body = _load_pillow_font(font_path, 42)
    small = _load_pillow_font(font_path, 28)
    grid = _load_pillow_font(font_path, 36)

    y = 40
    draw.text((48, y), spec.family_name(), fill=(20, 20, 20), font=title_font)
    y += 90
    draw.text((48, y), f"{spec.style_name} · v{spec.version} · {spec.mood}", fill=(90, 90, 90), font=small)
    y += 50

    caps = "".join(c for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    lower = "".join(c for c in "abcdefghijklmnopqrstuvwxyz")
    digits = "0123456789"
    punct = ".,!?:;'\"()- "

    for label, text, fnt in (
        ("Caps", caps, body),
        ("Lower", lower, body),
        ("Digits", digits, body),
        ("Punct", punct, body),
    ):
        draw.text((48, y), label, fill=(140, 140, 140), font=small)
        y += 36
        draw.text((48, y), text, fill=(15, 15, 15), font=fnt)
        y += 70

    draw.text((48, y), "Pangram", fill=(140, 140, 140), font=small)
    y += 36
    draw.text((48, y), PANGRAM, fill=(15, 15, 15), font=body)
    y += 80

    draw.text((48, y), "Samples", fill=(140, 140, 140), font=small)
    y += 36
    for word in SAMPLE_WORDS:
        draw.text((48, y), word, fill=(15, 15, 15), font=body)
        y += 56

    y += 20
    draw.text((48, y), "Glyph grid", fill=(140, 140, 140), font=small)
    y += 40
    # grid of MVP printable glyphs
    chars = []
    for name in MVP_GLYPHS:
        ch = glyph_char(name)
        if ch and ch != " ":
            chars.append(ch)
    cols = 12
    cell_w, cell_h = 100, 90
    x0 = 48
    for i, ch in enumerate(chars):
        col = i % cols
        row = i // cols
        x = x0 + col * cell_w
        yy = y + row * cell_h
        draw.rectangle([x, yy, x + cell_w - 8, yy + cell_h - 8], outline=(220, 220, 220))
        draw.text((x + 16, yy + 20), ch, fill=(20, 20, 20), font=grid)

    img.save(out_path, "PNG")
    return out_path


def render_compare_sheet(
    before_png: Path,
    after_png: Path,
    out_path: Path,
    label_before: str = "before",
    label_after: str = "after",
) -> Path:
    a = Image.open(before_png).convert("RGB")
    b = Image.open(after_png).convert("RGB")
    # scale to same height
    h = max(a.height, b.height)
    def _fit(im: Image.Image) -> Image.Image:
        scale = h / im.height
        return im.resize((int(im.width * scale), h), Image.Resampling.LANCZOS)

    a, b = _fit(a), _fit(b)
    gap = 24
    header = 48
    out = Image.new("RGB", (a.width + b.width + gap * 3, h + header + gap), (255, 255, 255))
    draw = ImageDraw.Draw(out)
    draw.text((gap, 12), label_before, fill=(0, 0, 0))
    draw.text((gap * 2 + a.width, 12), label_after, fill=(0, 0, 0))
    out.paste(a, (gap, header))
    out.paste(b, (gap * 2 + a.width, header))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out.save(out_path, "PNG")
    return out_path
