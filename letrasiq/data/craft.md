# Craft guide: from a brief to a design sheet

Use this when a font is described in words. Turn every characteristic into numbers in `fonts/<name>/design.json` (and metrics in `spec.json`), record why under `why`, and let the person review the sheet before drawing. Starting values assume 1000 units per em. They are starting points; judge the result in words and paragraphs.

## Translate the brief

| If the brief says | Change | Typical value |
|---|---|---|
| Small sizes, interface, screen | Raise x-height, open apertures, keep contrast low, loosen spacing | x-height 510-540; thin/stem above 0.75 |
| Long reading | Moderate x-height, even rhythm, clear word shapes | x-height 450-490 |
| Display, headline | Tighter spacing, more contrast and finer detail are affordable | spacing 15-25% tighter |
| Warm, friendly, human | Tilted axis, varied letter widths, double-story `a` and `g`, open terminals | stress -8 to -20 |
| Neutral, rational, engineered | Vertical axis, even widths, closed terminals | stress 0; capital widths closer together |
| Geometric | Near-circular bowls, very low contrast, single-story `a` | thin/stem above 0.9 |
| Elegant, refined | Higher contrast, sharper joins, longer ascenders | thin/stem 0.25-0.4 |
| Sturdy, durable, for code | Slightly heavier, low contrast, bigger punctuation | stem 95-110 |
| Light / bold | Scale stem and thin together, then reopen counters and thin the joins | light stem 50-70; bold stem 130-170 |
| Condensed / wide | Change widths and curve shape, not a horizontal stretch, which distorts stems | never scale outlines on one axis |

Serif construction: bracketed for warmth and reading, slab for sturdiness, hairline for elegance at large sizes. For a true slab, set `serif_thickness` close to `thin` and `serif_length` to at least 60, so the serifs read as structure. Monospace: one advance (about 600); widen `i l r j f t` with serifs or tails, and compress `m w M W`.

## Style and shape

These sheet settings choose letter construction, so most briefs need no drawing.

| Setting | Options | Use for |
|---|---|---|
| `style.serifs` | `none`, `bracketed`, `slab` | Slab for sturdy or typewriter faces, bracketed for reading |
| `style.terminals` | `cut`, `ball` | Ball for traditional serif details |
| `style.advance` | a number, usually 600 | Monospace |
| `shape.proportions` | `humanist`, `geometric`, `even` | Varied classical widths, near-circular rounds, or steady neutral widths |
| `shape.widths` | group values, such as `{"wide_caps": 0.9, "o_ratio": 0.8}` | Adjusting a preset; see `WIDTH_GROUPS` in `letrasiq/latin.py` |
| `shape.a`, `shape.g` | `single`, or leave out for double-story | Single for geometric or informal faces |
| `shape.aperture` | `open`, `closed` | Open for warmth and small sizes, closed for neutral or engineered faces |
| `shape.l` | `plain`, or leave out for a tailed `l` | Plain for geometric faces, but check `l I 1` stay clear |
| `shape.dots` | `round`, `square` | Square for neutral or engineered faces |

Stems keep their weight at any width, so change proportions here instead of scaling outlines.

## Sheet values

- `stem`, `cap_stem`: vertical strokes. Capitals are about 8-10% heavier, so they look equal next to lowercase.
- `thin`, `cap_thin`: horizontal strokes. Their ratio to the stem is the contrast. Even "monoline" faces need thin below stem, because horizontals look heavier than verticals of the same width.
- `stress_deg`: axis tilt. Negative tilts like a right-handed broad nib.
- `overshoot`: how far rounds pass the flat lines (10-15). Without it, `o` looks smaller than `x`.
- `figure_height`: a little below cap height, so figures don't shout in text.
- `join`: thickness scale where arches meet stems (0.4-0.6). Thinning keeps `n m r` counters open.
- `kern_gap`: the outline gap kerning aims for. Set it between round-round and stem-stem spacing.
- `spacing.S`: the sidebearing for a straight stem, and the main spacing dial. Letters space optically from it: each side is measured for white space, so rounds and diagonals automatically get less. Pass `sb=` to `add` only for a real exception. Check the proof lines in `review.png`, such as `nnnonnn`, until the color is even.
- `optical_depth`, `optical_factor`: how deep into a side the measurement looks, and how strongly white space reduces the sidebearing. Tune them only if rounds as a group look too tight or too loose.
- Other `spacing` tokens: values for punctuation and symbols, which aren't spaced optically.

## Drawing rules

1. Draw control glyphs first: `H O n o`, plus `a e g` for character. Get their weight, proportions and spacing right in `HHOHH` and `nnonn`, then derive every other letter from them.
2. Keep values in the sheet. Build related letters from the same helpers: `n h m u`, `b d p q`, `O C G Q`.
3. Put spine nodes at extremes, with directions of 0, 90, 180 or 270 wherever the stroke turns there.
4. Thin strokes where they enter a stem. Let curves pass over a stem edge, not stop on it.
5. Where a diagonal meets a stem or another stroke, end it on the other stroke's edge. A flat end left outside shows as a notch.
6. Make rounds slightly wider than the straight letters they sit beside, and place the top of an arch right of the counter's centre.
7. Check these spots first in every font: `a e g s`, `K k`, `y`, `5`, `&`, `@`. They failed first in Letra Humanist.

## Review order

1. Run `letrasiq build` and `letrasiq check`. Read each warning and either fix it or say why it doesn't apply.
2. Open `build/previews/detail.png` for construction: boxy bowls, notches, clusters of points.
3. Open `build/previews/review.png` for shape and spacing in real text.
4. Read `build/previews/report.html`, which includes Font Bakery's results. A failure usually belongs in the engine, so fix it there.
5. Hand over `build/previews/tester.html`, which is where the person makes the final call.
