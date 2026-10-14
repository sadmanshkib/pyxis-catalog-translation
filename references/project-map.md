# Pyxis translation project — inventory & status survey

Where everything lives, and how to answer "what changed / what is the state" without
re-deriving work that already has a report. Read this before any orientation or audit
task on the Pyxis translation projects.

## The one rule that matters

**The git mirror is not the source of truth.** `C:\Projects\Pyxis_Lab\github\pyxis-catalog-translation`
(public mirror of `git@github.com:sadmanshkib/pyxis-catalog-translation.git`, Apache-2.0) holds
this skill's `SKILL.md` + `scripts/` and is updated far less often than the work happens.
A clean working tree with nothing ahead of `origin/main` means *nothing about progress*.
Always pair the git check with a scan of the project folders.

## Trees

| What | Where |
|---|---|
| Skill mirror repo (this skill + 4 scripts) | `C:\Projects\Pyxis_Lab\github\pyxis-catalog-translation` |
| Working project root | `C:\Projects\Pyxis_Lab\Translation\` |
| EN→ZH catalog deliverables + method docs | `Translation\Catalog\` — `2026_Catalog_CN_Translated.pdf`, `bilingual_translation_reference.md`, `translation_overview.md`, `translation_qa_checklist.md`, per-section source folders |
| Catalog source PDFs / DOCX | `AI TNS\old works\` — `Original EN 2026_Catalog_DIGITAL_v2.0.pdf` (+ compressed and DOCX variants), `2026_Catalog_DIGITAL_Local_translation).pdf`, early sample pages |
| Glossary + translation memory | `AI TNS\old works\translation_glossary.md`, `AI TNS\old works\translation_memory.json` — **not** next to the catalog PDF |
| ZH→EN manual/datasheet runs | `Translation\Manuals\EC-310 EC-320 EN\`, `Translation\Manuals\IK-765 Series Inline Probe Operation Manual\`, `Translation\PC-200_EN\`, `Translation\PC-200_Manual\` |
| ZH→EN docx runs | `Translation\Ling-Hui\FS_translation\`, `Translation\Ling-Hui\ST605_translation\` |
| Catalog-page batch (50 scanned pages → EN) | `Translation\Extract\` + the accepted set in `Extract\A-Now\` (round-trip copies in `Translation\Lynn\`) |

## Translation memory (`translation_memory.json`)

- Shape: `{"version": 1, "entries": {"<English source string>": {"zh": ..., "source": ..., "added": ...}}, "conflicts": [...]}`.
- `source` records which run added the term (datasheet/manual name, or a catalog page id).
- Merge each run with `scripts/translation_memory.py merge --tm <file> --spans ... --translations ... --source <tag>`;
  the glossary stays authoritative, conflicts are logged and never overwritten.
- Entry count grows per run — report it from the file (`len(d['entries'])`), never from memory.

## Each run leaves a method + QA write-up — read it first

| Document | Records |
|---|---|
| `Extract\Extract_INDEX.md` | one row per delivered page: what the page is, its fix history, QA result |
| `Extract\translation_overview*.md` | per-batch method, unit counts, verification numbers |
| `Extract\column_overrun_fix.md` | the fit-to-column defect pass: measured overruns, the code changes, the rebuilt page list, the assertions |
| `PC-200_Manual\translation_overview.md` | 50-page run: pipeline stages, scale numbers, verification, known limitations |
| `PC-200_Manual\merge_fix\FIX_REPORT.md` | post-review repair of the merged manual: per-item changes, containment diff, remaining size spreads, open items |
| `<project>\work\qa_report.txt`, `QA\*.txt` | the machine output behind those write-ups |

A status or audit answer quotes these instead of re-deriving method from the artefacts,
and **separates committed / project-only / still-open**. Open items are listed explicitly
(deviations deliberately kept from the source, questions awaiting the user) — silently
smoothing them over is the failure mode this project has already rejected drafts for.

## Survey recipe

`bash scripts/project_status.sh` runs the whole thing (read-only): git log/status/ahead-behind,
newest files per run folder, the write-ups, and the translation-memory stats.

The pieces, if you prefer them by hand:

```bash
R="C:/Projects/Pyxis_Lab/github/pyxis-catalog-translation"
git -C "$R" log --oneline -5
git -C "$R" status --porcelain
git -C "$R" rev-list --left-right --count origin/main...main   # left=origin, right=local
```

- **Scope every filesystem scan to a project subfolder.** A recursive walk of all of
  `C:\Projects\Pyxis_Lab` crosses the video/render trees and dies on the tool timeout.
  Use `search_files(target='files')` rooted at `Translation\<project>\` with
  `order='modified'` for a newest-first timeline, or a per-folder `ls -lt` in the terminal —
  never a whole-tree sweep.
- Filter out `*.png`/`*.tif` when listing a run folder — the QA renders dominate the listing
  and hide the scripts and reports you actually want.

## Sibling skills (don't restate their content here)

- `zh2en-pdf-inplace` — Chinese PDF → English in place: the full fit/width ruleset, raster
  repair, band-diff QA, whole-merge fixes, `references/` for the plan schema and scanned-manual→Word.
- `zh2en-pdf-translation` — ZH→EN datasheets (overlaps `zh2en-pdf-inplace`; keep the asset in one place).
- `docx-inplace-translation` — Word .docx ZH↔EN in place, including the EN→ZH font/theme pass order.
- `ocr-and-documents` — scanned sources with no text layer.
