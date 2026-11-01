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

Serif construction: bracketed for warmth and reading, unbracketed slab for sturdiness, hairline for elegance at large sizes. Monospace: one advance (about 600); widen `i l r j f t` with serifs or tails, and compress `m w M W`.

## Sheet values

- `stem`, `cap_stem`: vertical strokes. Capitals are about 8-10% heavier, so they look equal next to lowercase.
- `thin`, `cap_thin`: horizontal strokes. Their ratio to the stem is the contrast. Even "monoline" faces need thin below stem, because horizontals look heavier than verticals of the same width.
- `stress_deg`: axis tilt. Negative tilts like a right-handed broad nib.
- `overshoot`: how far rounds pass the flat lines (10-15). Without it, `o` looks smaller than `x`.
- `figure_height`: a little below cap height, so figures don't shout in text.
- `join`: thickness scale where arches meet stems (0.4-0.6). Thinning keeps `n m r` counters open.
- `kern_gap`: the outline gap kerning aims for. Set it between round-round and stem-stem spacing.
- `spacing`: sidebearing values. Straight sides get the most, rounds about 55% of that, diagonals and open shapes the least. Check by setting `nnnonnn` and `HHHOHHH` until the color is even.

## Drawing rules

1. Keep values in the sheet. Build related letters from the same helpers: `n h m u`, `b d p q`, `O C G Q`.
2. Put spine nodes at extremes, with directions of 0, 90, 180 or 270 wherever the stroke turns there.
3. Thin strokes where they enter a stem. Let curves pass over a stem edge, not stop on it.
4. Where a diagonal meets a stem or another stroke, end it on the other stroke's edge. A flat end left outside shows as a notch.
5. Make rounds slightly wider than the straight letters they sit beside, and place the top of an arch right of the counter's centre.
6. Check these spots first in every font: `a e g s`, `K k`, `y`, `5`, `&`, `@`. They failed first in Letra Humanist.

## Review order

1. Run `letrasiq build` and `letrasiq check`. Read each warning and either fix it or say why it doesn't apply.
2. Open `build/previews/detail.png` for construction: boxy bowls, notches, clusters of points.
3. Open `build/previews/review.png` for shape and spacing in real text.
4. Hand over `build/previews/tester.html`, which is where the person makes the final call.
