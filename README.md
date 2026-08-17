# pyxis-catalog-translation

> Hermes skill for automatic, industry-level **English → Simplified Chinese** PDF translation that preserves the original layout — English text is redacted and Chinese is inserted **in-place** at the same coordinates, with the same color, size, weight, and baseline. Built for Pyxis Lab product catalogs (industrial water-analysis instrumentation), but the pipeline works for any EN→ZH technical document.

## Features

- **In-place translation** — never rebuilds/reflows the PDF; layout, photos, gradients, and backgrounds survive
- **Exact visual fidelity** — original baseline positions, bold/regular weights, and true text colors, including Type3/outlined display text (titles, headers) whose colors live in glyph programs, recovered via `get_texttrace()` + rendered-pixel sampling
- **Proportional Latin + CJK typography** — Microsoft YaHei (or your platform's CJK font) subsetted with fontTools to ~100 KB per face; never the built-in CJK fallback that renders Latin full-width ("SP-350" → "S P - 3 5 0")
- **Glossary-driven** — unified EN→CN water-treatment terminology with reviewer-approved industry wording
- **Translation memory** — persistent EN→ZH term memory (`translation_memory.py`): every run queries prior translations first and merges its new terms back, so terminology stays consistent across a whole catalog; glossary entries stay authoritative and conflicts are logged, never silently overwritten
- **Hard safety rules** — product codes, brand names, units, and CAS numbers preserved; zero invented content
- **Built-in QA loop** — render sample pages to PNG for visual inspection; terminology/unit audits documented in the skill

## Requirements

- Python 3.10+
- [PyMuPDF](https://pypi.org/project/PyMuPDF/) (`pip install pymupdf`)
- [fontTools](https://pypi.org/project/fonttools/) (`pip install fonttools`)
- A CJK font (auto-detected per platform, see [Fonts](#fonts))

## Install into Hermes

```bash
# 1. Clone into your Hermes skills directory (global or a profile's skills)
git clone https://github.com/sadmanshkib/pyxis-catalog-translation.git \
  "$HOME/.hermes/skills/pyxis-catalog-translation"

# profile-specific:
#   "$HOME/.hermes/profiles/<profile>/skills/pyxis-catalog-translation"

# 2. Install Python deps
pip install pymupdf fonttools

# 3. Verify the skill is picked up
hermes skills list   # should show pyxis-catalog-translation
```

The repo root *is* a valid skill directory (`SKILL.md` + `scripts/`), so it works as-is.

## Usage

```bash
# 1. EXTRACT — line-merged text runs with bbox, baseline, bold flag, TRUE color
python scripts/extract_spans.py "in.pdf" -o work/spans.json
#   quick text-layer probe for a page range:
python scripts/extract_spans.py "in.pdf" --pages 1-3 -o work/probe.json

# 2. TRANSLATE — produce work/translations.json mapping span_id -> 中文
#    (load the glossary in SKILL.md; translate prose/labels, keep codes/units/brands)
#    Semantics: missing key or value == source text  -> keep as-is
#               "" (empty string)                    -> remove the English span
#    Consult the translation memory first so prior terms are reused verbatim:
python scripts/translation_memory.py lookup --tm translation_memory.json --text "<term>"

# 3. APPLY — redact English, insert Chinese at original baselines
python scripts/apply_translation.py "in.pdf" work/spans.json \
    work/translations.json -o "out_translated.pdf"

# 4. QA — render pages for visual inspection
python scripts/render_page.py "out_translated.pdf" --pages 1,6 -d 150 -o work/qa/

# 5. LEARN — merge this run's new terms back into the translation memory
python scripts/translation_memory.py merge --tm translation_memory.json \
    --spans work/spans.json --translations work/translations.json --source page8 \
    --export translation_memory.md
```

Then visually verify the PNGs, spot-check the text layer, and run the terminology/unit audits from `SKILL.md` (search for `QA Checklist`). The translation memory (`translation_memory.json`) starts empty and grows with every run; glossary files remain the authoritative reference and are never overwritten by it.

## Fonts

| Platform | Default regular | Default bold |
|---|---|---|
| Windows | `C:\Windows\Fonts\msyh.ttc` (Microsoft YaHei) | `C:\Windows\Fonts\msyhbd.ttc` |
| macOS | `/System/Library/Fonts/PingFang.ttc` | same |
| Linux | Noto Sans CJK (SC face) / WenQuanYi | Noto Sans CJK Bold / regular |

Override with environment variables:

```bash
export PYXIS_FONT_REGULAR=/path/to/regular.ttc
export PYXIS_FONT_BOLD=/path/to/bold.ttc
```

TTC collections are opened face-aware: the Simplified Chinese face is preferred (name contains SC/CN/HK/Simplified). If no font can be resolved, the script falls back to PyMuPDF's built-in `china-s` (functional but renders Latin full-width — not recommended for production).

## How it works

```
extract_spans.py      apply_translation.py
  get_text("dict")      Pass 1: ink-tight redaction (origin-based rects)
  + line merging          - removes ONLY text glyphs (images/line art kept)
  + baseline origin     Pass 2: insert Chinese at ORIGINAL baselines
  + bold flags            - collision-corrected for taller CJK glyphs
  + color:                - same color (texttrace / pixel sampling)
    get_texttrace()       - same size (auto-scaled only when it must fit)
    → render-pixel        - same weight (real bold face, not faux stroke)
    sampling fallback     - fontTools-subsetted YaHei (~100 KB embed)
```

Key engineering decisions (see `SKILL.md` → Pitfalls for the full list):

- **Ink-tight redaction**: raw span bounding boxes overlap neighboring text (leading); redacting the full box erases adjacent kept text (e.g. a small model-number kicker above a big title). Rect = `origin_y ± glyph ink` only.
- **Baseline-origin insertion**: Chinese is placed on the original baseline so vertical rhythm matches; pushed down only when taller CJK glyphs would collide with kept text above.
- **Real bold**: stroke-based faux bold turns CJK glyphs into black blobs — a true bold font face is subsetted instead.
- **Missing-glyph guard**: characters the subset font lacks (e.g. U+2082 subscript two is absent from YaHei) are sanitized to ASCII before insertion — never .notdef nulls.
- **`span["color"]` lies**: it reports 0 for Type3/outlined display text; trust the render.

## Project layout

```
pyxis-catalog-translation/
├── SKILL.md            # The Hermes skill: rules, glossary, workflow, QA, pitfalls
├── scripts/
│   ├── extract_spans.py          # span extraction + color recovery
│   ├── apply_translation.py      # in-place redact + insert engine
│   ├── render_page.py            # page → PNG for visual QA
│   └── translation_memory.py     # persistent EN→ZH term memory (lookup/merge)
├── requirements.txt
└── LICENSE
```

## License

MIT — see [LICENSE](LICENSE).
