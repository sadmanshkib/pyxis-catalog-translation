---
name: pyxis-catalog-translation
description: "Use when translating Pyxis Lab PDFs EN→ZH in-place."
version: 1.1.0
author: Hermes (sadma profile ai-pdf-translation)
license: MIT
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [translation, pdf, pyxis, chinese, catalog, in-place]
    category: productivity
    related_skills: [pdf, ocr-and-documents]
---

# Pyxis Lab Catalog Translation (EN → Simplified Chinese, in-place)

Automatic industry-level translation of Pyxis Lab product catalogs/manuals from English to Simplified Chinese. The deliverable is a **translated PDF with the original layout preserved** — English text redacted and Chinese inserted at the same coordinates. Never rebuild/reflow the PDF.

## When to Use

- User drops a Pyxis Lab PDF (catalog, manual, datasheet) to translate to Chinese.
- User asks to continue/produce the 2026 catalog translation (60-page, `Original EN 2026_Catalog_DIGITAL_v2.0.pdf`).
- Any EN→ZH technical document where layout/photos/colors must survive.

## Hard Rules (violating any of these gets the work rejected — page_6 & page_20 drafts were already rejected once)

1. **Keep in English (never translate):** product model numbers (SP-350P, ST-765P, IK-766-BPT), part numbers (50228, 50206), brand/company names (Pyxis Lab®), app/product names (uPyxis®, CloudLink™, KRYOPTIX™, Titronex™), communication protocols (Modbus, RS-485, Bluetooth®, LoRa, TCP/IP), certification marks (CE, RoHS, UKCA, ETL, USEPA, ISO methods).
2. **Never translate units:** ppb, ppm, mg/L, µg/L, NTU, µS/cm, mV, Abs, au, ºF, ºC, MPa, Bar, psi, mbar, inch, mm, m, ft, V, VAC, VDC, mA, Hz, mL/min, L/min. Keep exact values and decimal separators (period, not comma).
3. **No invented content.** Never add specs, features, claims, or sections absent from source. If a string is ambiguous or missing, flag it — do not fabricate. Verify every number against source.
4. **Exact CAS numbers** verbatim (e.g. Napthenic Disulfonic Acid → 萘二磺酸（NDSA）, CAS# 1655-29-4).
5. **In-place only:** redact the English span, insert Chinese at the same bbox, same color, auto-scaled to fit. No rebuilt PDFs.
6. **Unified glossary:** same English term → same Chinese everywhere. Load `translation_glossary.md` + `bilingual_translation_reference.md` before translating.

## Core Terminology (non-negotiable)

| English | Chinese | Note |
|---|---|---|
| IP67 / IP65 | IP67 / IP65 | NO hyphen, NO "IP-67" |
| Bluetooth® 5.0 | 蓝牙 5.0® | ® stays on the version |
| fluorescent tracer | 荧光示踪药剂 | no redundant 化学品 |
| handheld fluorometer | 手持式荧光检测仪 | SP series |
| inline sensor | 管道式在线传感器 | |
| inline refractometer | 在线式折射仪 | |
| sample cell | 样品检测池 (handheld) / 流通检测池 (inline) | context-dependent |
| measurement cycle | 检测周期 | |
| wetted materials | 过流材质 | |
| protection rating | 防护等级 | |
| Brix Range | 白利糖度（°Brix）量程 | |
| refractory | 折射仪 | |
| isolation / isolated | 隔离型 | signal outputs |
| 4-20mA / RS485 Modbus output | 隔离 4-20mA 模拟输出、隔离 RS-485 Modbus 数字输出 | always include 隔离 |

## Reviewer-Approved Wording (2026-08 professional review — mandatory replacements)

Use these instead of literal translations. Same English source → same approved Chinese everywhere.

| English | Approved Chinese | Don't use |
|---|---|---|
| Offline Verification Devices | 离线现场检测设备 | 离线校准验证设备 (it's a field tester, not a calibration standard) |
| No Sample Cuvette Required | 无需配套比色皿 | 无需样品比色皿 |
| LOCK-IN feature when Reading has Stabilized | 读数稳定自动锁定功能 | any sentence containing raw "LOCK-IN" |
| Integrated Sample Cell Cleanliness Diagnostics Function for Cleaning Frequency | 内置样品池洁净度自检功能，自动提醒清洗周期 | 诊断功能，及时提示清洗维护 |
| Turbidity Over-Range Alarm features for Samples with Excessive Turbidity | 高浊度样品浊度超量程报警 | 浊度超量程报警功能，适用于高浊度样品 |
| Waterproof and Drop Resistant Design | 防水抗跌落结构 | 防水防摔设计 |
| Customizable Display Output Value as ppm Product vs. ppb Tracer | 可自定义显示单位：药剂浓度（ppm）或示踪剂 PTSA 浓度（ppb） | 显示值可自定义：产品浓度… ("Product" = water treatment chemical 药剂, not generic product) |

General rule: **no raw English marketing terms inside descriptive Chinese sentences** (LOCK-IN, etc.) — integrate into Chinese. English is allowed only for codes, brands, protocols, and units.

## Prerequisites

- Python 3.11 + PyMuPDF (fitz) + fontTools (`pip install pymupdf fonttools`).
- A CJK font — resolved automatically per platform; override via `PYXIS_FONT_REGULAR` / `PYXIS_FONT_BOLD` (see README).
- Optional domain references (adjust to your document's glossary):
  - `translation_glossary.md` / `bilingual_translation_reference.md` — build one per project domain; the Pyxis water-treatment glossary below is a working example.
- LLM (to produce translations.json): any capable model; the reference setup uses `deepseek/deepseek-chat` (quality) with a local fallback. Never use a small 4B model for production translation.

## Pipeline (scripts live in `scripts/` of this skill)

```bash
# 1. INSPECT — text layer present? page count?
python scripts/extract_spans.py "in.pdf" --pages 1-3 -o inspect.json   # quick probe
#   If pages yield no text → scanned PDF → OCR route (see Pitfalls).

# 2. EXTRACT — spans with bbox/font/size/color, line-merged into logical runs
python scripts/extract_spans.py "in.pdf" -o work/spans.json

# 3. TRANSLATE — the LLM (you) produces translations.json {span_id: 中文}
#    - Load glossary + bilingual reference first, then query the TRANSLATION MEMORY
#      (translation_memory.json — default next to the source PDF, override with --tm):
#        python scripts/translation_memory.py lookup --tm translation_memory.json --text "<term>"
#      Reuse every existing TM pair verbatim — same English term -> same Chinese everywhere.
#    - Classify each run: translate prose/labels; keep codes/units/brands as-is (span_id → same text).
#    - Chunk by page; for the 60-page catalog work section-by-section (per translation_overview.md structure).
#    - IMPORTANT: the merged runs in spans.json are the natural translation units.
#      Reject placeholder output; no invented content.
#    - SEMANTICS: missing key or value == source text → keep as-is; "" (empty string)
#      → REMOVE the English span entirely (redact, insert nothing) — use for orphan
#      subscript digits (e.g. the "2"/"3" of ClO₂/SO₃ split into separate spans).

# 4. APPLY in-place — redact English, insert Chinese, auto-scale to fit box
python scripts/apply_translation.py "in.pdf" work/spans.json work/translations.json -o "out_translated.pdf"

# 5. QA — render sample pages and VISUALLY verify (see QA section)
python scripts/render_page.py "out_translated.pdf" --pages 6,20 -d 150 -o work/qa/
#    then vision_analyze each PNG.

# 5b. LEARN — merge this run's new translations into the translation memory so
#     the NEXT transaction reuses them automatically (memory grows per run):
#     python scripts/translation_memory.py merge --tm translation_memory.json \
#         --spans work/spans.json --translations work/translations.json --source <pageno-or-name> \
#         --export translation_memory.md
#     Glossary entries are authoritative; conflicts are logged, never overwritten.

# 6. DELIVER — DEFAULT OUTPUT LOCATION (user convention):
#    save as <basename>_translated.pdf NEXT TO THE SOURCE PDF
#    e.g. "page 8.pdf" -> "page_8_translated.pdf" in the same folder.
#    Full-catalog deliverables additionally go to C:\Projects\Pyxis_Lab\Translation\Catalog\
#    as <Year>_Catalog_CN_Translated.pdf + update translation_overview.md / QA checklist.
#    Follow the next-to-source default unless the user asks otherwise.
#
#    IMPORTANT — desktop-app attachments: when the user drops a PDF in the chat,
#    the app stores a copy under profiles\<profile>\attachments\ — that is NOT
#    the user's folder. Resolve the ORIGINAL file location first (same filename
#    under the project tree, e.g. C:\Projects\Pyxis_Lab\AI_PDF _Translation\page 8.pdf;
#    verify with md5sum if unsure) and write the output there.
```

## QA Checklist (run every time, before delivery)

1. Page count matches source.
2. Render 3–5 representative pages (cover, spec table, section divider) at 150 DPI; vision_analyze each: no text overflow past bbox, no overlapping Chinese, no blank areas where English was, CJK glyphs render (not tofu), colors/positions preserved, photos untouched.
3. Spot-check extraction: `extract_spans.py` on the output, confirm ~99% coverage, no leftover English prose (codes/units/brands may remain by design).
4. Terminology audit: grep output text for forbidden forms — `IP-67`, `IP 67`, `化学品` near tracer, missing 蓝牙®.
5. Numbers audit: no invented/changed specs — every value traceable to source spans.
6. Unit rule: no translated units anywhere (磅/英寸/伏 are red flags).
7. **Fit / column safety** — programmatic, per page, on the delivered file (`references/fit-and-column-safety.md`): (a) nothing lost — every character of the version it replaced is still present (subsequence test on the whitespace-free text layer); (b) nothing past the page's own content edge (+ ≤ 4 pt tolerance); (c) no two drawn lines overlap; (d) no line below the 5 pt legibility floor.
8. **Residue + metadata**: the text layer holds no leftover CJK **and** a render-OCR pass (200–250 dpi) over every page reports 0 CJK (line-art misreads listed with page and reason); PDF **Info** *and* XMP `dc:title` both carry the English title; page count and page size match the source. More checks: `references/qa-automation.md`.
9. Confirm output saved to the designated output folder before reporting success.

## Pitfalls

- **PyMuPDF quirks (all fixed in the shipped scripts — do not "simplify" them away):**
  - `apply_redactions()` is a **Page** method, not a Document method.
  - Default redaction erases underlying images AND line art — the gradient/photo background dies, leaving white patches. Must call `page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE, graphics=fitz.PDF_REDACT_LINE_ART_NONE)` to keep backgrounds.
  - Raw span bboxes overlap neighboring text (leading) — redacting the full bbox ERASES adjacent kept text (e.g. the small "SP-350" kicker above a big title). Redact with ink-tight rects: `Rect(x0, origin_y - 0.8*fs, x1, origin_y + 0.28*fs)`.
  - `span["color"]` is unreliable: it reports `0` for Type3/outlined display text (titles, "KEY FEATURES" headers) whose true fill color lives inside the glyph programs. `extract_spans.py` therefore fills `color_rgb` from `page.get_texttrace()` first, then falls back to rendered-pixel mode sampling (dominant non-background color). Trust the render, never the span dict alone.
  - Insert Chinese at the span's ORIGINAL baseline (`span["origin"]`), not a bbox-derived baseline, and push down only when CJK glyphs (taller than Latin caps) would collide with kept text above — see `CJK_ASCENT`/`CLEARANCE` in the script.
  - `fitz.get_text_length()` takes no `fontfile`; measure with a `fitz.Font(fontfile=...)` object's `.text_length()` instead.
  - fontTools subsetting of Windows TTC files: open via `TTCollection(src).fonts[0]`, subset, save as .ttf (the "MERG/meta NOT subset" warnings are harmless).
- **Scanned/image-only pages**: empty span extraction → stop, route to `ocr-and-documents` (render pages + OCR) — never fabricate text.
- **Fonts (REV 4 — do not regress):** use Microsoft YaHei subsets (fontTools-subsetted `msyh.ttc` regular + `msyhbd.ttc` bold, ~110KB each) via `apply_translation.py`. NEVER use built-in `china-s` for mixed text — it renders Latin FULL-WIDTH ("SP-350" → "S P - 3 5 0") and looks broken. NEVER fake bold with `render_mode=2` stroke — it turns CJK glyphs into black blobs at any stroke width. The scripts handle both automatically.
- **Scaling**: Chinese is wider than English; auto-scale shrinks font to fit bbox. If a box is tiny, prefer shortening the Chinese (not overflowing).
- **Clipping at the paper edge (measured defect — 11 of 50 pages on the 2026-09 batch).** Sizing a string from the room *around* the source box measures room the string cannot use: left-aligned lines were fitted to **+80…+128 pt beyond the page's own content edge** and the tail was silently clipped by the viewer (p19 printed `…repair by a professional is r`). Usable width is the **ink gap beside the box**, bounded by the page's own measured content edges, with a 5 pt legibility floor — ruleset, the four per-page assertions and the batch-rebuild discipline in `references/fit-and-column-safety.md`. Read it before touching any fitter.
- **A batch defect is never one page.** Apply the fix to **every** page the defect touches (24 rebuilt when 1 was reported), find them numerically rather than by eye, and **never rebuild a page that carries hand corrections** — check by rebuilding to a temp file and comparing; if the builder does not reproduce the delivered page, leave it and say so.
- **One size per document role.** In a merged document, a header/footer fitted per page looks ragged (6.07–6.75 pt on one run). Normalise to one size per role across pages and re-run the normaliser on the *delivered* pages; screenshot/UI labels are legitimately different sizes — list the residual spreads with their reason instead of forcing them.
- **Metadata lives in two places.** Set the PDF **Info** *and* the XMP `dc:title`: iOS Quick Look reads the XMP, so an Info-only change still shows the source-language title. A PDF built by copying pages can end up with **empty** metadata — assert it is non-empty, then correct.
- **Redaction order**: add ALL redact annots first, `apply_redactions()`, THEN insert Chinese — otherwise redactions erase inserted text. Use no fill color (transparent) so images/backgrounds under text survive.
- **Fragmented spans**: `extract_spans.py` merges same-line adjacent spans (gap ≤ 2pt, same font/size/color) into runs — translating runs (not raw spans) avoids broken Chinese.
- **Trademark/® placement**: 蓝牙 5.0® — ® attaches to the version number in Chinese marketing text; keep Bluetooth® as-is in mixed English.
- **IP ratings**: source may say "IP-67"; output must be IP67.
- **Do not translate** the ~10 unmatched spans (Unicode quote variants): keep original, log them.
- **Never promise success without verifying**: page count, rendered PNG, extracted-text spot check.
- **Scope filesystem surveys to a project subfolder.** A recursive walk of all of
  `C:\Projects\Pyxis_Lab` crosses gigabytes of video/render output and dies on the tool
  timeout; use `search_files(target='files')` rooted at `Translation\<project>\` with
  `order='modified'`, or a per-folder `ls -lt`, and never a whole-tree sweep.
- **Terminology files live in the project's `old works\` folder**, not next to the source PDF:
  `AI TNS\old works\translation_memory.json` + `translation_glossary.md`. Look there first,
  merge new terms there (see `references/project-map.md`).

## Verification

- `extract_spans.py` prints pages + span count; compare text against known-good sample (e.g. `AI TNS\sample_page_6.txt`).
- `apply_translation.py` prints replaced/skipped counts.
- Final gate: rendered PNGs inspected with vision_analyze + QA checklist above. Deliver only what you verified.

## Project State, Deliverables & "What Changed?" Questions

- **The git mirror is NOT the source of truth.** The repo holds a snapshot of this skill and
  lags the real work. Check `git log`, `git status --porcelain` **and**
  `git rev-list --left-right --count origin/main...main`, then survey the project folders
  before reporting any status: a clean tree with nothing unpushed says nothing about what
  has been delivered since.
- **Every run leaves a method + QA write-up next to its deliverables** — read the run's own
  report instead of re-deriving its process from the artefacts. A status answer quotes those
  numbers and **separates committed / project-only / still-open**, listing the open items
  (deviations deliberately kept from source, questions awaiting the user). Presenting
  progress no artefact supports is the failure mode this project has rejected before.
- Paths, report names and the cheap survey commands: `references/project-map.md`;
  `scripts/project_status.sh` runs the whole survey read-only.

## Related Files

- Source of truth for the workflow: `SKILL.md` (this file) + `scripts/` in this repo.
- `references/project-map.md` — where the source PDFs, deliverables, glossary, translation
  memory and each run's report live, plus the survey recipe. `scripts/project_status.sh` —
  read-only status probe (git state, newest files per run folder, TM stats).
- **`references/fit-and-column-safety.md`** — the available-width ruleset (ink-gap bounds, page
  content edges, legibility floor, per-cell re-flow), the four per-page assertions, and the
  batch-rebuild discipline. Same geometry problem in both directions; the sibling
  `zh2en-pdf-inplace` skill carries the ZH→EN raster-repair variants.
- **`references/qa-automation.md`** — the programmatic QA suite: text-layer and render-OCR residue
  checks, numeric-fidelity diff, collision detection, metadata (Info + XMP), frame consistency in a
  merged document, changed-pixel containment, and the Word/Excel deliverable checks.
- Reference project layout (Pyxis Lab 2026 catalog, 60 pages):
  - source PDFs + per-page sample drafts under the project's translation folder
  - `translation_overview.md` (page map: 1 cover, 5-13 handheld, 15-31 inline, 33-36 liquid level, 38-47 panel, 49-52 accessories, 54-56 reagents, 58-59 software, 60 back cover)
- Output convention: translated PDFs save as `<name>_translated.pdf` next to the source by default.
