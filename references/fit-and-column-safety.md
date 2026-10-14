# Fitting translated text into the room that actually exists

Why this file exists: a translated line is sized from `room_around(box)`-style measurements,
which return the free room on **both** sides of the source box. A left-aligned line cannot use
the room to its *left*, so it gets fitted to a width that does not exist and the tail is drawn
off the page — where the PDF viewer clips it silently. The reader sees a sentence that just stops.

Applies to **both** translation directions (the geometry problem is symmetric); the ZH→EN
sibling skill `zh2en-pdf-inplace` carries the raster-repair variants.

## The defect, measured (50-page scanned manual, 2026-09-18)

| page | line drawn to x | page's own content edge | past it |
|---|---|---|---|
| 19 | 596.1 (off the 595 pt page) | 504.9 | +91.2 |
| 21 | 598.0 / 599.8 / 598.8 | 485.2 | +112.8 |
| 25 | 596.5 | 499.5 | +97.1 |
| 27 | 575.0 | 447.3 | +127.7 |
| 30 | 594.9 | 496.6 | +98.2 |
| 31 | 597.7 / 598.6 / 596.6 | 499.1 | +98.5 |
| 32 | 595.5 | 502.5 | +92.5 |
| 34 / 35 / 36 / 37 / 40 / 46 | 594.5–598.0 | 496.4–570.2 | +80 … +105 |
| 11, 12, 20, 22–24, 26 | 509–520 | 498–506 | +3 … +16 |

Pages ending at x > 595 had visible truncation (p19 printed `…repair by a professional is r`).

A second defect on the same pages: a line that stayed on the paper still ran into what sat next
to it, because nothing bounded it by the page's own content or by the target-language text
already drawn — `Calibration Voltage` over `Current Voltage` (43.7 pt overlap), `Channel` over
`Particle Size` (18.6 pt), a label over a numeric input box, and troubleshooting-table cells
re-flowed to the *page* column instead of the *cell*.

## Rules (all of them — do not reinstate a both-sides width)

1. **Usable width = the ink gap.** Measure the interval `lo … hi` between the ink either side of
the source box, bounded by the page's **own** content edges (`ink_l` / `ink_r`, measured from
the scan, + 4 pt).
2. **Alignment decides the start.** A left-aligned line starts at its own left edge; a centred
   label keeps its centring where it fits and slides inside the gap where it does not.
3. **Refuse an impossible word.** A single word wider than the slot is rejected, never accepted
   (the old escape hatch accepted it unconditionally, so `fit_size` returned the *maximum* size
   for every one-word label).
4. **Ink is anything that differs from the band's own ground**, so white labels on a dark button
   count (a `darker than 150` test sees no ink there at all). A column counts only if a real part
   of the line height is covered — a 1–2 px separator rule is not text.
5. **Already-drawn target text is an obstacle too.** Two labels on one row cannot both grow into
   the gap between them.
6. **Size each line on its own** (per-line bounding): a narrow table cell no longer squeezes the
   whole block, and a label no longer prints over the box beside it.
7. **Re-flow to the block's own right edge** — the scanned cell — never to the page column.
8. **Legibility floor (`FS_FLOOR`) = 5.0 pt.** If the gap cannot hold the text, the line may touch
   its neighbour; it never leaves the paper and never becomes unreadable.

## The four assertions — run in code on every rebuilt page

1. **Nothing lost** — every character of the page it replaced is still present (subsequence test
   on the whitespace-free text layer). A rebuilt page may only *gain* what used to be clipped.
2. **Nothing past the column** — the widest body line ends at its own content edge + ≤ 4 pt.
3. **No text-on-text** — no two drawn lines overlap (was 8 collisions across 5 pages).
4. **Nothing unreadable** — no line below the 5 pt floor.

Plus: a render-OCR pass (200–250 dpi) of the rendered page reports **0 CJK**; known line-art
misreads are listed explicitly with page and reason, never silently ignored.

## Batch discipline (this is what makes the fix trustworthy)

- **Fix every page the defect touches, not the one that was reported** (24 pages here, of which
  one was reported). Find them numerically — scan every page for the measured overrun — not by eye.
- **Never rebuild a page that carries hand corrections.** Rebuild it to a temp file and compare
  first; if the current builder does not reproduce the delivered page, leave it and say so. Silent
  rebuilding drops text such a page holds.
- **Record the trade-off you accept.** When a rebuild only swaps one defect for another of the same
  size (a 9 pt overrun for a 9 pt overlap inside a screenshot panel), leave the page and name both
  sides in the write-up.
- **Per-page reports must answer fit questions**: carry the gap, the per-line limits and the size
  actually used (`fs`) per line, so the next question is answered from the report, not a rebuild.
- **Overwriting a PDF that is open in a viewer fails** (Windows: file busy). Write
  `<name>_REV<n>.pdf`, and tell the user to rename it over the old one after closing the viewer.
- **Write down the page list.** The write-up states which pages were rebuilt, which were
  deliberately not, and why — the next run audits against that list instead of re-deriving it.
