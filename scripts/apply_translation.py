#!/usr/bin/env python3
"""Apply in-place Chinese translations to a PDF (Pyxis pipeline, REV 4).

Fixes baked in:
- Ink-tight redaction rects (origin-based): adjacent kept text (e.g. a small
  model-number kicker above a big title) is NOT erased even though the raw
  bboxes overlap in the original layout.
- Chinese inserted at the ORIGINAL baseline origin (vertical rhythm matches),
  pushed down only when taller CJK glyphs would collide with kept text above.
- Fonts: Microsoft YaHei (regular) + YaHei Bold (bold), subsetted via
  fontTools to the used glyphs (~100KB each) — proper proportional Latin.
  NEVER use built-in china-s for mixed text: it renders Latin full-width
  ("SP-350" -> "S P - 3 5 0"). Stroke faux-bold blobs CJK — never use.
- Color preserved; size preserved unless it must shrink to fit the box.

Usage:
  python apply_translation.py in.pdf spans.json translations.json -o out.pdf

translations.json maps span_id -> Chinese string. Missing/empty/identical
entries are skipped (left as-is). Redaction pass runs BEFORE inserting text.
"""
import argparse
import json
import os

import fitz  # PyMuPDF

CJK_FONT = "china-s"  # last-resort fallback only (full-width Latin)


def resolve_font_sources():
    """Resolve regular/bold CJK font paths.

    Priority: PYXIS_FONT_REGULAR / PYXIS_FONT_BOLD env vars, then platform
    defaults (Windows: Microsoft YaHei; macOS: PingFang; Linux: Noto CJK or
    WenQuanYi). Returns [(tag, path), ...]; entries may be None.
    """
    reg = os.environ.get("PYXIS_FONT_REGULAR")
    bold = os.environ.get("PYXIS_FONT_BOLD")
    if reg and bold:
        return [("reg", reg), ("bold", bold)]
    import sys
    if sys.platform == "win32":
        reg = reg or r"C:/Windows/Fonts/msyh.ttc"
        bold = bold or r"C:/Windows/Fonts/msyhbd.ttc"
    elif sys.platform == "darwin":
        reg = reg or "/System/Library/Fonts/PingFang.ttc"
        bold = bold or "/System/Library/Fonts/PingFang.ttc"
    else:  # linux
        candidates = [
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
            "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
        ]
        found = [c for c in candidates if os.path.exists(c)]
        reg = reg or (found[0] if found else None)
        bold = bold or (found[1] if len(found) > 1 else reg)
    return [("reg", reg), ("bold", bold)]


FONT_SOURCES = resolve_font_sources()
MIN_FS = 4.0
# CJK ink box relative to baseline (glyphs fill ~0.9em above, ~0.15em below)
CJK_ASCENT = 0.90
CLEARANCE = 1.5          # pt gap to neighboring kept text
REDACT_TOP = 0.80        # English glyph ink above baseline (caps + accents)
REDACT_BOTTOM = 0.28     # English glyph ink below baseline (descenders)
MAX_OVERFLOW = 1.10      # allow up to 10% wider than the box before shrinking


def collect_chars(translations_json):
    chars = set()
    with open(translations_json, encoding="utf-8") as f:
        data = json.load(f)
    for v in data.values():
        chars.update(str(v))
    chars.update("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz ()（）.,，。、；：%®™·+-–—/'\"&!?")
    return chars


def open_cjk_face(path):
    """Open a CJK font file; for TTC collections prefer the Simplified
    Chinese face (name contains SC/CN/HK/Simplified), else the first face."""
    from fontTools.ttLib import TTFont, TTCollection
    if path.lower().endswith(".ttc"):
        faces = TTCollection(path).fonts
        for f in faces:
            name = (f["name"].getDebugName(1) or "") + " " + (f["name"].getDebugName(4) or "")
            if any(k in name for k in ("SC", "CN", "HK", "Simplified")):
                return f
        return faces[0]
    return TTFont(path)


def make_font_subsets(translations_json, out_dir):
    """Subset CJK fonts (regular + bold) to used glyphs.
    Returns (regular_ttf, bold_ttf); entries may be None if unavailable."""
    try:
        from fontTools import subset
    except Exception:
        return None, None
    text = "".join(sorted(collect_chars(translations_json)))
    opts = subset.Options()
    outs = []
    for _tag, src in FONT_SOURCES:
        if not src or not os.path.exists(src):
            outs.append(None)
            continue
        try:
            f = open_cjk_face(src)
            ss = subset.Subsetter(options=opts)
            ss.populate(text=text)
            ss.subset(f)
            out = os.path.join(out_dir, os.path.basename(src).replace(".ttc", "") + "_subset.ttf")
            f.save(out)
            outs.append(out)
        except Exception:
            outs.append(None)
    return outs[0], outs[1]


SUP_DIGITS = {0x2070: "0", 0x00B9: "1", 0x00B2: "2", 0x00B3: "3",
              0x2074: "4", 0x2075: "5", 0x2076: "6", 0x2077: "7",
              0x2078: "8", 0x2079: "9"}


def sanitize_for_font(text, font):
    """Replace chars the subset font lacks (e.g. U+2082 subscript two,
    absent from YaHei) with ASCII equivalents; never insert .notdef nulls."""
    if font is None:
        return text
    out = []
    for c in text:
        cp = ord(c)
        if font.has_glyph(cp):
            out.append(c)
        elif cp in SUP_DIGITS:
            out.append(SUP_DIGITS[cp])
        elif 0x2080 <= cp <= 0x2089:  # subscript digits ₀-₉
            out.append(chr(ord("0") + cp - 0x2080))
        else:
            out.append(c)  # leave as-is (renders notdef if truly missing)
    return "".join(out)


def main():
    ap = argparse.ArgumentParser(description="In-place EN->ZH PDF translation.")
    ap.add_argument("pdf_in")
    ap.add_argument("spans_json", help="extract_spans.py output")
    ap.add_argument("translations_json", help='{"span_id": "中文"}')
    ap.add_argument("-o", "--out", required=True)
    args = ap.parse_args()

    with open(args.spans_json, encoding="utf-8") as f:
        spans = json.load(f)
    with open(args.translations_json, encoding="utf-8") as f:
        trans = json.load(f)

    by_page = {}
    for s in spans:
        by_page.setdefault(s["page"], []).append(s)
    # kept-as-is spans (no translation) — collision avoidance + redact safety
    kept_by_page = {}
    for s in spans:
        zh = trans.get(s["span_id"])
        if zh is None or zh.strip() == s["text"]:
            kept_by_page.setdefault(s["page"], []).append(s)

    reg_file, bold_file = make_font_subsets(
        args.translations_json, os.path.dirname(os.path.abspath(args.out)))
    reg_font = fitz.Font(fontfile=reg_file) if reg_file else None
    bold_font = fitz.Font(fontfile=bold_file) if bold_file else None

    doc = fitz.open(args.pdf_in)

    # Pass 1: redact translated spans with ink-tight rects (transparent fill)
    to_insert = {}  # page -> [(span, zh, fs)]
    replaced = removed = skipped = 0
    for pno, plist in sorted(by_page.items()):
        page = doc[pno - 1]
        for s in plist:
            zh_raw = trans.get(s["span_id"])
            if zh_raw is None or zh_raw.strip() == s["text"]:
                skipped += 1
                continue
            zh = zh_raw
            rect = fitz.Rect(s["bbox"])
            ox, oy = origin_of(s, rect)
            sp_size = s.get("size", 11) or 11
            ink = fitz.Rect(rect.x0, oy - REDACT_TOP * sp_size,
                            rect.x1, oy + REDACT_BOTTOM * sp_size)
            page.add_redact_annot(ink, fill=None)  # backgrounds survive
            if not zh.strip():
                removed += 1          # "" = remove the English span entirely
                continue
            fs = autoscale(zh, sp_size, rect.width,
                           font=bold_font if (s.get("flags", 0) & 16) else reg_font)
            # drop chars the subset font lacks (subscripts etc.) BEFORE insert
            zh = sanitize_for_font(
                zh, bold_font if (s.get("flags", 0) & 16) else reg_font)
            to_insert.setdefault(pno, []).append((s, zh, fs))
            replaced += 1

    # apply redactions per page; remove ONLY text, keep images + line art
    for pno in to_insert:
        doc[pno - 1].apply_redactions(
            images=fitz.PDF_REDACT_IMAGE_NONE,
            graphics=fitz.PDF_REDACT_LINE_ART_NONE,
        )

    # Pass 2: insert Chinese at original baselines with collision correction
    for pno, items in to_insert.items():
        page = doc[pno - 1]
        for (s, zh, fs) in items:
            rect = fitz.Rect(s["bbox"])
            ox, oy = origin_of(s, rect)
            base_y = oy
            for kept in kept_by_page.get(pno, []):
                kr = fitz.Rect(kept["bbox"])
                if kr.x1 < rect.x0 - 2 or kr.x0 > rect.x1 + 2:
                    continue  # no horizontal overlap
                em_top = base_y - CJK_ASCENT * fs
                if kr.y1 > em_top and kr.y0 < base_y:
                    base_y = max(base_y, kr.y1 + CLEARANCE + CJK_ASCENT * fs)
            rgb = to_rgb(s.get("color", 0), s.get("color_rgb"))
            bold = bool(s.get("flags", 0) & 16)
            if bold and bold_file:
                page.insert_text((rect.x0, base_y), zh, fontname="yaheibd",
                                 fontfile=bold_file, fontsize=fs, color=rgb)
            elif reg_file:
                page.insert_text((rect.x0, base_y), zh, fontname="yahei",
                                 fontfile=reg_file, fontsize=fs, color=rgb)
            else:
                page.insert_text((rect.x0, base_y), zh, fontname=CJK_FONT,
                                 fontsize=fs, color=rgb)

    doc.save(args.out, deflate=True, garbage=4)
    print(json.dumps({"replaced": replaced, "removed": removed,
                      "skipped": skipped,
                      "fonts": {"regular": reg_file, "bold": bold_file},
                      "out": args.out}))


def origin_of(s, rect):
    return s.get("origin", [rect.x0, rect.y1 - 0.2 * s.get("size", 11)])


def to_rgb(color_int, color_rgb=None):
    """Convert a span color to (r, g, b) tuple in 0..1.

    color_rgb (list [r,g,b] 0-255 from texttrace) wins; else convert the
    span color int via sRGB.
    """
    if color_rgb:
        return tuple(float(v) / 255.0 for v in color_rgb)
    if isinstance(color_int, (tuple, list)):
        return tuple(float(v) for v in color_int)
    try:
        rgb = fitz.sRGB_to_rgb(color_int)  # ints in 0..255
        return tuple(v / 255.0 for v in rgb)
    except Exception:
        return (0, 0, 0)


def autoscale(text, orig_size, max_width, font=None):
    """Return a font size that fits text within max_width (pt)."""
    fs = orig_size
    while fs > MIN_FS:
        if font is not None:
            tw = font.text_length(text, fontsize=fs)
        else:
            tw = fitz.get_text_length(text, fontname=CJK_FONT, fontsize=fs)
        if tw <= max_width * MAX_OVERFLOW:
            break
        fs -= 0.5
    return max(fs, MIN_FS)


if __name__ == "__main__":
    main()
