"""Trace a sketch image into a custom glyph via system potrace."""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageOps

from letrasiq.expand import path_bounds, svg_path_to_pathops, to_cubic_path
from letrasiq.glyph import GlyphSource, glyph_filename, load_locked, save_locked
from letrasiq.pipeline import font_dir
from letrasiq.spec import FontSpec


class TraceError(RuntimeError):
    pass


def require_potrace() -> str:
    path = shutil.which("potrace")
    if not path:
        raise TraceError(
            "potrace not found on PATH. Install with `brew install potrace` "
            "(or your system package manager), then retry."
        )
    return path


def image_to_pbm(image_path: Path, pbm_path: Path, threshold: int = 128) -> None:
    """Convert any raster image to a binary PBM for potrace."""
    img = Image.open(image_path)
    img = ImageOps.exif_transpose(img)
    gray = img.convert("L")
    # Invert if background is mostly dark (sketch on black)
    hist = gray.histogram()
    dark = sum(hist[:128])
    light = sum(hist[128:])
    if dark > light:
        gray = ImageOps.invert(gray)
    bw = gray.point(lambda p: 0 if p < threshold else 255, mode="1")
    # potrace likes black foreground on white; PIL mode "1" with 0=black
    bw.save(pbm_path)


_PATH_D_RE = re.compile(
    r"<path\b[^>]*\bd\s*=\s*[\"']([^\"']+)[\"']",
    re.IGNORECASE | re.DOTALL,
)


def extract_svg_path_data(svg_text: str) -> str:
    """Concatenate all path `d` attributes from potrace SVG output."""
    parts = _PATH_D_RE.findall(svg_text)
    if not parts:
        raise TraceError("potrace produced SVG with no <path d=...> elements")
    return " ".join(p.strip() for p in parts)


def run_potrace(pbm_path: Path, svg_path: Path, potrace_bin: str | None = None) -> str:
    binary = potrace_bin or require_potrace()
    try:
        subprocess.run(
            [
                binary,
                "-s",  # SVG
                "-o",
                str(svg_path),
                str(pbm_path),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as e:
        raise TraceError(
            "potrace not found on PATH. Install with `brew install potrace`."
        ) from e
    except subprocess.CalledProcessError as e:
        raise TraceError(f"potrace failed: {e.stderr or e.stdout or e}") from e
    return svg_path.read_text(encoding="utf-8")


def pathops_to_svg_d(path) -> str:
    """Serialize a pathops Path to an SVG path `d` string (cubics/lines)."""
    cubic = to_cubic_path(path)
    parts: list[str] = []
    for verb, pts in cubic.segments:
        if verb == "moveTo":
            x, y = pts[0]
            parts.append(f"M {x:.3f} {y:.3f}")
        elif verb == "lineTo":
            x, y = pts[0]
            parts.append(f"L {x:.3f} {y:.3f}")
        elif verb == "curveTo":
            (x1, y1), (x2, y2), (x3, y3) = pts[0], pts[1], pts[2]
            parts.append(f"C {x1:.3f} {y1:.3f} {x2:.3f} {y2:.3f} {x3:.3f} {y3:.3f}")
        elif verb == "closePath":
            parts.append("Z")
    return " ".join(parts)


def normalize_path_to_metrics(
    svg_d: str,
    spec: FontSpec,
    *,
    target_height: float | None = None,
) -> tuple[str, int]:
    """
    Flip SVG Y (potrace Y-down → font Y-up), scale to fit target height
    (default: cap_height), sit on baseline, return (svg_d, advance).
    """
    path = svg_path_to_pathops(svg_d)
    if not path:
        raise TraceError("traced path is empty after parse")

    # SVG is Y-down; font is Y-up — flip around Y
    bounds = path_bounds(path)
    if bounds is None:
        raise TraceError("traced path has no bounds")
    x0, y0, x1, y1 = bounds
    # Flip: y' = -y
    path = path.transform(1, 0, 0, -1, 0, 0)
    bounds = path_bounds(path)
    assert bounds is not None
    x0, y0, x1, y1 = bounds

    h = max(1.0, y1 - y0)
    w = max(1.0, x1 - x0)
    target_h = target_height if target_height is not None else float(spec.cap_height)
    scale = target_h / h
    # Scale then move xmin→sidebearing, ymin→baseline
    path = path.transform(scale, 0, 0, scale, 0, 0)
    bounds = path_bounds(path)
    assert bounds is not None
    x0, y0, x1, y1 = bounds
    left_sb = int(round(spec.stroke_base() * 0.7))
    path = path.transform(1, 0, 0, 1, left_sb - x0, -y0)
    bounds = path_bounds(path)
    assert bounds is not None
    x0, y0, x1, y1 = bounds
    right_sb = left_sb
    advance = int(round((x1 - x0) + left_sb + right_sb))
    d = pathops_to_svg_d(path)
    if not d.strip():
        raise TraceError("normalized path serialized empty")
    return d, max(advance, left_sb + right_sb + 1)


def trace_glyph(
    name: str,
    glyph: str,
    image: Path,
    root: Path | None = None,
    *,
    lock: bool = True,
    threshold: int = 128,
) -> Path:
    """
    Trace `image` into fonts/<name>/glyphs/<glyph>.json as a custom glyph.
    Optionally append glyph to locked.txt.
    """
    d = font_dir(name, root)
    if not d.exists():
        raise TraceError(f"font not found: {d}")
    image = Path(image)
    if not image.exists():
        raise TraceError(f"image not found: {image}")

    spec = FontSpec.load(d / "spec.json")
    potrace_bin = require_potrace()

    # Copy reference into references/
    ref_dir = d / "references"
    ref_dir.mkdir(parents=True, exist_ok=True)
    ref_dest = ref_dir / f"{glyph}{image.suffix.lower() or '.png'}"
    if image.resolve() != ref_dest.resolve():
        shutil.copy2(image, ref_dest)

    with tempfile.TemporaryDirectory(prefix="letrasiq-trace-") as tmp:
        tmp_path = Path(tmp)
        pbm = tmp_path / "input.pbm"
        svg = tmp_path / "out.svg"
        image_to_pbm(image, pbm, threshold=threshold)
        svg_text = run_potrace(pbm, svg, potrace_bin=potrace_bin)
        raw_d = extract_svg_path_data(svg_text)
        # Descenders / x-height letters: use x_height for lowercase single letters
        target_h = float(spec.x_height) if len(glyph) == 1 and glyph.islower() else float(spec.cap_height)
        if glyph in ("g", "j", "p", "q", "y"):
            # Leave room for descender: scale to x_height, will sit on baseline
            # (true descender placement can be refined later)
            target_h = float(spec.x_height)
        norm_d, advance = normalize_path_to_metrics(raw_d, spec, target_height=target_h)

    out = GlyphSource(name=glyph, type="custom", path=norm_d, width=advance)
    dest = d / "glyphs" / glyph_filename(glyph)
    out.save(dest)

    if lock:
        locked = load_locked(d / "locked.txt")
        locked.add(glyph)
        save_locked(d / "locked.txt", locked)

    return dest
