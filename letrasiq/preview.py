"""Render specimen PNG previews."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from fontTools.ttLib import TTFont

from letrasiq.outline import svg_path_to_pathops, to_cubic_path
from letrasiq.glyph import ASCII_GLYPHS, GlyphSource, glyph_char, glyph_filename
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

    W, H = 1400, 2100
    img = Image.new("RGB", (W, H), (250, 248, 244))
    draw = ImageDraw.Draw(img)

    title_font = _load_pillow_font(font_path, 64)
    body = _load_pillow_font(font_path, 42)
    small = _load_pillow_font(font_path, 28)
    grid = _load_pillow_font(font_path, 36)

    y = 40
    draw.text((48, y), spec.family_name(), fill=(20, 20, 20), font=title_font)
    y += 90
    draw.text((48, y), f"{spec.style_name} - v{spec.version}", fill=(90, 90, 90), font=small)
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
    # grid of printable glyphs
    chars = []
    for name in ASCII_GLYPHS:
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


READING = (
    "The quick brown fox jumps over the lazy dog while a mild breeze carries the smell of "
    "rain across the valley. Good type stays out of the way: words hold together, spacing "
    "feels even, and the eye moves along each line without stopping. Sphinx of black quartz, "
    "judge my vow. (Figures: 0123456789, $48.50 & 72% - really?)"
)
REVIEW_LINES = [
    ("Hamburgefonstiv", 150),
    ("nnnonnnonnoonn", 72),
    ("HHHOHHHOHHOOHH", 72),
    ("nanbncndnengnhnknmnpnrnsntnunvnwnxnynz", 44),
    ("HAHBHCHDHEHFHGHKHLHMHNHPHQHRHSHTHUHVHWHXHYHZ", 40),
    ("n.n,n:n;n!n?n'n\"n-n–n—n(n)n[n]n{n}n/n&n", 44),
    ("H.H,H:H;H!H?H'H\"H-H(H)H[H]H{H}H/H&H", 44),
    ("H0H1H2H3H4H5H6H7H8H9H n0n1n2n3n4n5n6n7n8n9n", 40),
    ("ncndnendnéngñoöþnßn nænœnøn «n» ‹n› “n” ‘n’ „n“", 44),
    ("ABCDEFGHIJKLM", 110),
    ("NOPQRSTUVWXYZ", 110),
    ("abcdefghijklm", 110),
    ("nopqrstuvwxyz", 110),
    ("0123456789", 110),
    ("!\"#$%&'()*+,-./:;<=>?", 80),
    ("@[\\]^_`{|}~", 80),
    ("minimum illicit Tower AVATAR Typography Wave", 62),
    ("To Ta Te Tu Ty Tö Tä Té Ty. Yo Yá Ya. Vo Vä Va, We Wo Wä Fa Fo Fä Pa Pä P. LT LV LY", 44),
    ("AV VA AW WA AT TA AY YA KO LO RO RT RV ry. ky. r, r. f. y, v. w. \"A A\" 'A' (A) T. T, P, F.", 40),
    ("ÀÉÎÕÜ Çàéîõü ñçšžł ÅÆØ åæø Œœ ß Þþ Ðð Ħħ", 70),
    ("Ångström Çelik Żółć žluťoučký Őrült Ñandú Ģirts", 58),
    ("“Quotes” ‘single’ «guillemets» „low“ – en — em … € £ ¥ ¢ © ® ™ § ¶ ° × ÷ − • ¡Sí! ¿Qué?", 44),
]


def render_review(font_dir: Path, spec: FontSpec | None = None) -> Path:
    """Large letters plus real text at several sizes, for judging shape and spacing."""
    spec = spec or FontSpec.load(font_dir / "spec.json")
    build_dir = font_dir / "build"
    font_path = _pick_font_file(build_dir, spec.family_name(), spec.style_name)
    W = 1500
    img = Image.new("RGB", (W, 3600), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    y = 24
    for text, size in REVIEW_LINES:
        draw.text((40, y), text, font=_load_pillow_font(font_path, size), fill=(15, 15, 15))
        y += int(size * 1.3)
    for size in (28, 20, 16, 13):
        font = _load_pillow_font(font_path, size)
        line, lines = "", []
        for word in READING.split():
            test = (line + " " + word).strip()
            if font.getlength(test) > 900:
                lines.append(line)
                line = word
            else:
                line = test
        lines.append(line)
        for ln in lines:
            draw.text((40, y), ln, font=font, fill=(15, 15, 15))
            y += int(size * 1.45)
        y += 18
    out = build_dir / "previews" / "review.png"
    img.crop((0, 0, W, y + 10)).save(out, "PNG")
    return out


def _core_names() -> list[str]:
    from letrasiq.latin_core import core_codes, glyph_name

    ascii_names = set(ASCII_GLYPHS)
    return [glyph_name(code) for code in core_codes() if glyph_name(code) not in ascii_names and code != 0x00A0]


def render_detail(font_dir: Path, spec: FontSpec | None = None) -> Path:
    """Every ASCII glyph's outline with its on-curve points, for inspecting construction."""
    names = [n for n in ASCII_GLYPHS if n != "space"]
    return _outline_sheet(font_dir, spec, names, "detail.png", 0.2, 10, 190, 225)


def render_detail_core(font_dir: Path, spec: FontSpec | None = None) -> Path:
    """The same view of the glyphs beyond ASCII: accents, ligatures, currency and punctuation."""
    return _outline_sheet(font_dir, spec, _core_names(), "detail-core.png", 0.13, 16, 120, 160)


def _outline_sheet(font_dir: Path, spec: FontSpec | None, names: list[str], filename: str, scale: float, cols: int, cw: int, ch: int) -> Path:
    spec = spec or FontSpec.load(font_dir / "spec.json")
    rows = (len(names) + cols - 1) // cols
    img = Image.new("RGB", (cols * cw, rows * ch), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    for i, name in enumerate(names):
        ox, oy = (i % cols) * cw + 24, (i // cols) * ch + int(ch * 0.73)
        draw.line([(ox - 4, oy), (ox + cw - 18, oy)], fill=(190, 205, 225))
        xh = oy - spec.x_height * scale
        draw.line([(ox - 4, xh), (ox + cw - 18, xh)], fill=(190, 205, 225))
        source = font_dir / "glyphs" / glyph_filename(name)
        if not source.exists():
            continue
        path = to_cubic_path(svg_path_to_pathops(GlyphSource.load(source).path or ""))
        last = start = None
        for verb, pts in path.segments:
            if verb == "moveTo":
                last = start = pts[0]
            elif verb == "lineTo":
                draw.line([(ox + last[0] * scale, oy - last[1] * scale), (ox + pts[0][0] * scale, oy - pts[0][1] * scale)], fill=(20, 20, 20))
                last = pts[0]
            elif verb == "curveTo":
                line = []
                for k in range(17):
                    t, u = k / 16, 1 - k / 16
                    x = u**3 * last[0] + 3 * u * u * t * pts[0][0] + 3 * u * t * t * pts[1][0] + t**3 * pts[2][0]
                    y = u**3 * last[1] + 3 * u * u * t * pts[0][1] + 3 * u * t * t * pts[1][1] + t**3 * pts[2][1]
                    line.append((ox + x * scale, oy - y * scale))
                draw.line(line, fill=(20, 20, 20))
                last = pts[2]
            elif verb == "closePath" and last != start:
                draw.line([(ox + last[0] * scale, oy - last[1] * scale), (ox + start[0] * scale, oy - start[1] * scale)], fill=(20, 20, 20))
            if verb in ("moveTo", "lineTo", "curveTo"):
                p = pts[-1]
                draw.rectangle([ox + p[0] * scale - 1, oy - p[1] * scale - 1, ox + p[0] * scale + 1, oy - p[1] * scale + 1], fill=(214, 60, 40))
    out = font_dir / "build" / "previews" / filename
    img.save(out, "PNG")
    return out


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
