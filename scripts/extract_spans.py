#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 SHKIB SADMAN (sadmanshkib)
"""Extract text spans from a PDF into JSON for Pyxis in-place translation.

Merges adjacent same-line spans (same font/size/color, gap <= --gap) into
logical runs — those are the natural translation units.

Usage:
  python extract_spans.py in.pdf -o spans.json [--pages 6,14-15] [--min-size 4] [--gap 2]
"""
import argparse
import json

import fitz  # PyMuPDF


def parse_pages(spec, page_count):
    if spec in (None, "", "all"):
        return list(range(page_count))
    nums = []
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, b = (int(x) for x in part.split("-"))
            nums.extend(range(a - 1, b))
        else:
            nums.append(int(part) - 1)
    return sorted(set(n for n in nums if 0 <= n < page_count))


def trace_colors(page):
    """Exact text colors from the content stream (get_texttrace).

    span['color'] is unreliable (reports 0 for CMYK/other fills); texttrace
    carries the actual fill color. Returns [(Rect, (r,g,b) 0-255), ...].
    """
    out = []
    try:
        for t in page.get_texttrace():
            bbox = fitz.Rect(t["bbox"])
            c = t.get("color") or [0, 0, 0]
            if len(c) >= 4:  # CMYK
                k = min(1.0, c[3])
                r = 255 * (1 - min(1.0, c[0])) * (1 - k)
                g = 255 * (1 - min(1.0, c[1])) * (1 - k)
                b = 255 * (1 - min(1.0, c[2])) * (1 - k)
            elif len(c) == 3:  # RGB
                r, g, b = (min(1.0, max(0.0, v)) * 255 for v in c)
            else:  # gray
                v = min(1.0, max(0.0, c[0])) * 255
                r = g = b = v
            out.append((bbox, (round(r), round(g), round(b))))
    except Exception:
        pass
    return out


def assign_trace_colors(runs, page):
    """Fill run['color_rgb']: texttrace first, rendered-pixel sampling second.

    texttrace carries exact fill colors for normal fonts; spans drawn with
    Type3/outlined glyphs (titles, display text) have no stream color, so we
    sample the rendered page for their dominant non-background color.
    """
    trace = trace_colors(page)
    for run in runs:
        rb = fitz.Rect(run["bbox"])
        best, best_area = None, 0.0
        for tb, col in trace:
            inter = rb & tb
            a = inter.get_area()
            if a > best_area:
                best_area, best = a, col
        if best is not None and best_area > rb.get_area() * 0.25:
            run["color_rgb"] = list(best)
    missing = [r for r in runs if "color_rgb" not in r]
    if not missing:
        return
    pix = None
    try:
        pix = page.get_pixmap(dpi=150, colorspace=fitz.csRGB)
    except Exception:
        return
    s = 150 / 72.0
    for run in missing:
        col = sample_region(pix, fitz.Rect(run["bbox"]), s)
        if col is not None:
            run["color_rgb"] = list(col)


def sample_region(pix, bbox, s):
    """Dominant non-background color in a rendered region (stride 2)."""
    x0 = max(0, int(bbox.x0 * s))
    y0 = max(0, int(bbox.y0 * s))
    x1 = min(pix.width, int(bbox.x1 * s))
    y1 = min(pix.height, int(bbox.y1 * s))
    if x1 <= x0 or y1 <= y0:
        return None
    from collections import Counter
    cnt = Counter()
    for y in range(y0, y1, 2):
        for x in range(x0, x1, 2):
            cnt[pix.pixel(x, y)] += 1
    if not cnt:
        return None
    bg, _ = cnt.most_common(1)[0]
    far = Counter()
    for (r, g, b), n in cnt.items():
        d2 = (r - bg[0]) ** 2 + (g - bg[1]) ** 2 + (b - bg[2]) ** 2
        if d2 > 40 ** 2:
            far[(r, g, b)] += n
    if not far:
        return None
    nr, ng, nb = far.most_common(1)[0][0]  # mode = true fill color
    lum = 0.299 * nr + 0.587 * ng + 0.114 * nb
    chroma = max(nr, ng, nb) - min(nr, ng, nb)
    if lum < 70 and chroma < 30:
        return (0, 0, 0)  # near-black text
    return (nr, ng, nb)


def main():
    ap = argparse.ArgumentParser(description="Extract line-merged text spans from PDF pages (1-based).")
    ap.add_argument("pdf")
    ap.add_argument("-o", "--out", default="spans.json")
    ap.add_argument("--pages", default="all", help="e.g. 6,14-15 or 'all'")
    ap.add_argument("--min-size", type=float, default=4.0, help="drop spans smaller than this (pt)")
    ap.add_argument("--gap", type=float, default=2.0, help="max horizontal gap (pt) to merge spans in a line")
    args = ap.parse_args()

    doc = fitz.open(args.pdf)
    page_nums = parse_pages(args.pages, len(doc))

    runs = []
    for pno in page_nums:
        page = doc[pno]
        start = len(runs)
        d = page.get_text("dict")
        for block in d["blocks"]:
            if block.get("type") != 0:
                continue  # skip image blocks
            for line in block["lines"]:
                line_spans = []
                for span in line["spans"]:
                    text = span["text"]
                    if not text.strip():
                        continue
                    if span["size"] < args.min_size:
                        continue
                    line_spans.append(span)
                # merge adjacent spans into runs
                cur = None
                for sp in line_spans:
                    if cur is None:
                        cur = [sp]
                        continue
                    prev = cur[-1]
                    same_style = (
                        prev["font"] == sp["font"]
                        and abs(prev["size"] - sp["size"]) < 0.1
                        and prev.get("color") == sp.get("color")
                    )
                    gap = sp["bbox"][0] - prev["bbox"][2]
                    if same_style and 0 <= gap <= args.gap:
                        cur.append(sp)
                    else:
                        yield_run(cur, pno, runs, len(runs))
                        cur = [sp]
                if cur:
                    yield_run(cur, pno, runs, len(runs))
        assign_trace_colors(runs[start:], page)

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(runs, f, ensure_ascii=False, indent=1)
    print(json.dumps({"pages": [p + 1 for p in page_nums], "runs": len(runs), "out": args.out}))


def yield_run(spans, pno, runs, idx):
    text = "".join(s["text"] for s in spans).strip()
    if not text:
        return
    x0 = min(s["bbox"][0] for s in spans)
    y0 = min(s["bbox"][1] for s in spans)
    x1 = max(s["bbox"][2] for s in spans)
    y1 = max(s["bbox"][3] for s in spans)
    runs.append({
        "page": pno + 1,
        "span_id": f"p{pno + 1}s{idx}",
        "text": text,
        "bbox": [round(x0, 2), round(y0, 2), round(x1, 2), round(y1, 2)],
        "origin": [round(spans[0]["origin"][0], 2), round(spans[0]["origin"][1], 2)],
        "size": round(spans[0]["size"], 2),
        "font": spans[0]["font"],
        "color": spans[0].get("color", 0),
        "flags": spans[0].get("flags", 0),
    })


if __name__ == "__main__":
    main()
