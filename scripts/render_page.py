#!/usr/bin/env python3
"""Render selected PDF pages to PNGs for visual QA (Pyxis pipeline).

Usage:
  python render_page.py in.pdf --pages 6,20 -d 150 -o qa_dir/
"""
import argparse
import json
import os

import fitz  # PyMuPDF


def parse_pages(spec, page_count):
    if spec in (None, "", "all"):
        return list(range(page_count))
    nums = []
    for part in spec.split(","):
        part = part.strip()
        if "-" in part:
            a, b = (int(x) for x in part.split("-"))
            nums.extend(range(a - 1, b))
        else:
            nums.append(int(part) - 1)
    return sorted(set(n for n in nums if 0 <= n < page_count))


def main():
    ap = argparse.ArgumentParser(description="Render PDF pages to PNG.")
    ap.add_argument("pdf")
    ap.add_argument("--pages", default="all")
    ap.add_argument("-d", "--dpi", type=int, default=150)
    ap.add_argument("-o", "--outdir", default=".")
    args = ap.parse_args()

    doc = fitz.open(args.pdf)
    pages = parse_pages(args.pages, len(doc))
    os.makedirs(args.outdir, exist_ok=True)
    files = []
    for pno in pages:
        pix = doc[pno].get_pixmap(dpi=args.dpi)
        out = os.path.join(args.outdir, f"page_{pno + 1:02d}.png")
        pix.save(out)
        files.append(out)
    print(json.dumps({"rendered": len(files), "files": files}))


if __name__ == "__main__":
    main()
