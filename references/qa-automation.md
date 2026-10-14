# Programmatic QA for an in-place translation

Every check below is code with a printed verdict, run on the **delivered** file — not on an
intermediate, and not by eye alone. A vision pass over a few pages complements these; it does not
replace them. Numbers to quote in the write-up come from these runs.

## 1. Text layer, source language gone

```python
import re, fitz
text = "".join(p.get_text() for p in fitz.open(out_pdf))
assert re.findall(r'[\u4e00-\u9fff]', text) == []      # EN→ZH: reverse the range for ZH→EN
```

Unmatched / ambiguous spans are **kept as-is and logged**, never guessed (e.g. the ~10 spans whose
source uses non-ASCII quote variants).

## 2. Render-OCR residue (raster sources: the only honest check)

When the page is a scan, the text layer proves nothing — the source glyphs are pixels. OCR the
rendered page (RapidOCR, 200–250 dpi) over **every** page and report the hits:

- real hits → fix them, then re-run until 0;
- line-art misreads → list them with page and reason (`回` in the two shaded rectangles of a
  figure; `口` in a diagram; an `8`-row read as a glyph). Identical hits in the source are noted as
  such. Say which is which — an unexplained count is not a QA result.
- a different sampler/OCR engine is a second opinion, not proof: on a white-on-halftone URL the
  first pass was unreadable and the string was verified by rendering it beside the source.

## 3. Numeric fidelity (diff, do not eyeball)

Extract every source unit's numbers and diff against the translation (998 units on one manual run).
Flag → explain each one, in writing. Legitimate classes seen: Chinese ordinal section numbers set as
Arabic (一、→ 1.), date/phone spacing normalised (`2013-11-1415:39` → `2013-11-14 15:39`,
`+864****3350` → `+86 400 998 3350`), figure numbers fused with the following range by OCR
(`Figure 3.5.8` / `3.5.9` / `3.5.10` + `4-20mA`, verified at 900–1200 dpi). Re-OCR at 1200 dpi when
a callout is ambiguous at reading resolution — never resolve a number by inference.

## 4. Collisions and overlaps

A clash detector over the placed units (`qa_clash`-style: pairwise intersection of drawn boxes) plus
a de-overlap pass. Report the residual count **with a reason per group**: TOC title/dot-leader pairs
are one label at identical coordinates; dense protocol legends and screenshot UI labels sit closer
than the source because the target language is 2–3× longer — each inspected and stated as such.

## 5. Metadata — two places, both English

- PDF **Info** (title/author/creator/producer) *and* the **XMP** `dc:title`.
- Reason: iOS Quick Look (and several viewers) read the XMP, so an Info-only change still shows the
  source-language title on the device. A merge built by copying pages can end up with **empty**
  metadata — assert non-empty, then assert correct.

## 6. Frame consistency in a merged document

Header/footer sized per page looks ragged across a 50-page document (6.07–6.75 pt on one run).
Normalise to **one size per role** across pages (header 17 pt, footer 6.234 pt), then re-run the
normaliser over the delivered pages and list the spreads that remain with the reason they remain
(screenshot UI labels are genuinely different sizes; a label in front of a white input box may have
~57 pt where its siblings have ~150 pt). The normaliser's own rule — one size per role, never below
the legible floor, never overflowing the box — is what blocks unifying those.

## 7. Change containment (when patching an accepted deliverable)

Diff the new file against the **accepted previous generation** at 120 dpi and assert every changed
pixel lies inside a band this build was allowed to touch (267 500 changed pixels, **0 stray**). Bands:
header, footer, the re-worded block, the re-sized line, the patched raster region. For raster work use
band diffs at 600 dpi on both sides. Also assert page count, page size, and that no text layer
anywhere still carries a token that was supposed to change.

## 8. Word/Excel deliverables

- Open the file with **Word itself** (`verify_word_open.py`-style COM check), not only `python-docx`:
  field/TOC regeneration and font substitution happen there.
- Re-run the CJK-font pass **after** Word updates fields/TOC (regenerated runs get theme fonts back).
- Tables: pair label/value rows by printed line height, not left-to-right order (OCR merges two
  labels into one block while their values stay separate, which crosses them); column count = the
  commonest row width, so one odd row cannot create a permanently blank column.
- Figures: embed the source drawing per figure, in document order, with its printed caption and the
  translated call-outs beneath it; a spec table that exists as a real table in the source stays text.
- Check the paging/folio numbers survive (a generated Word file can lose the running folios).
