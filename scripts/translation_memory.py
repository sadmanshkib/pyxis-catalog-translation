#!/usr/bin/env python3
"""Translation Memory (TM) manager for the Pyxis catalog pipeline.

Persists EN->ZH term pairs across runs so every transaction reuses prior
translations (user requirement: same English term -> same Chinese everywhere).

Usage:
  # merge new material into the TM
  python translation_memory.py merge --tm tm.json \
      --spans spans.json --translations translations.json --source page8 \
      [--glossary glossary.md ...] [--export tm.md]

  # query the TM
  python translation_memory.py lookup --tm tm.json --text "Item"
  python translation_memory.py stats --tm tm.json

Priority: glossary sources beat page translations; first page translation
wins over later ones. Conflicts are logged, never silently overwritten.
"""
import argparse
import json
import os
import re
import sys
from datetime import date

TM_VERSION = 1


def load_tm(path):
    if not os.path.exists(path):
        return {"version": TM_VERSION, "entries": {}, "conflicts": []}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_tm(path, tm):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(tm, f, ensure_ascii=False, indent=1)
    print(json.dumps({"entries": len(tm["entries"]), "conflicts": len(tm["conflicts"]), "tm": path}))


def parse_glossary(path):
    """Parse markdown glossary tables: | EN | ZH | ... -> [(en, zh)]"""
    pairs = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line.startswith("|"):
                continue
            cells = [c.strip() for c in line.strip("|").split("|")]
            if len(cells) < 2:
                continue
            en, zh = cells[0], cells[1]
            # skip header/separator rows
            if en in ("", "English Original Term", "English", "---") or re.match(r"^[-: ]+$", en):
                continue
            if not en or not zh or re.match(r"^[-: ]+$", zh):
                continue
            # skip explanation rows where the "Chinese" column is an English
            # expansion (e.g. units table "| m | meter |") — real translations
            # always contain CJK characters
            if not re.search(r"[\u4e00-\u9fff]", zh):
                continue
            pairs.append((en, zh))
    return pairs


def add_entry(tm, en, zh, source):
    if not en or not zh:
        return "skip"
    en, zh = en.strip(), zh.strip()
    if en == zh:
        return "skip"  # explicit keep-as-is, covered by hard rules
    existing = tm["entries"].get(en)
    if existing is None:
        tm["entries"][en] = {"zh": zh, "source": source, "added": str(date.today())}
        return "added"
    if existing["zh"] == zh:
        return "same"
    # conflict: glossary is authoritative; first source wins otherwise
    if existing["source"] == "glossary" or source == "glossary":
        keep = "glossary" if existing["source"] == "glossary" else source
        drop = source if existing["source"] == "glossary" else existing["source"]
        if existing["source"] == "glossary" and source != "glossary":
            tm["conflicts"].append({"en": en, "kept": existing["zh"], "rejected": zh, "kept_source": "glossary", "rejected_source": source})
            return "conflict(glossary-wins)"
        if source == "glossary":
            tm["entries"][en] = {"zh": zh, "source": "glossary", "added": str(date.today())}
            tm["conflicts"].append({"en": en, "kept": zh, "rejected": existing["zh"], "kept_source": "glossary", "rejected_source": existing["source"]})
            return "conflict(updated-to-glossary)"
    tm["conflicts"].append({"en": en, "kept": existing["zh"], "rejected": zh,
                            "kept_source": existing["source"], "rejected_source": source})
    return "conflict(kept-first)"


def export_md(tm, path):
    lines = ["# Pyxis Translation Memory (auto-generated — do not edit by hand)",
             "", "| English | Chinese | Source | Added |", "|---|---|---|---|"]
    for en, e in sorted(tm["entries"].items()):
        lines.append(f"| {en} | {e['zh']} | {e['source']} | {e['added']} |")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(json.dumps({"export": path, "rows": len(tm["entries"])}))


def main():
    ap = argparse.ArgumentParser(description="Pyxis translation memory manager")
    sub = ap.add_subparsers(dest="cmd", required=True)

    m = sub.add_parser("merge")
    m.add_argument("--tm", required=True)
    m.add_argument("--spans", action="append", default=[])
    m.add_argument("--translations", action="append", default=[])
    m.add_argument("--glossary", action="append", default=[])
    m.add_argument("--source", default="manual")
    m.add_argument("--export", default=None)

    l = sub.add_parser("lookup")
    l.add_argument("--tm", required=True)
    l.add_argument("--text", required=True)

    s = sub.add_parser("stats")
    s.add_argument("--tm", required=True)

    args = ap.parse_args()

    if args.cmd == "merge":
        tm = load_tm(args.tm)
        stats = {"added": 0, "same": 0, "skip": 0, "conflict": 0,
                 "conflict(glossary-wins)": 0, "conflict(updated-to-glossary)": 0,
                 "conflict(kept-first)": 0}
        # glossary sources are authoritative
        for g in args.glossary:
            for en, zh in parse_glossary(g):
                stats[add_entry(tm, en, zh, "glossary")] += 1
        # page translations: pair spans.json + translations.json by span_id
        for sp_path, tr_path in zip(args.spans, args.translations):
            with open(sp_path, encoding="utf-8") as f:
                spans = {s["span_id"]: s["text"] for s in json.load(f)}
            with open(tr_path, encoding="utf-8") as f:
                trans = json.load(f)
            for sid, zh in trans.items():
                en = spans.get(sid)
                if not en:
                    continue
                stats[add_entry(tm, en, zh, args.source)] += 1
        save_tm(args.tm, tm)
        print(json.dumps(stats))
        if args.export:
            export_md(tm, args.export)
        if tm["conflicts"]:
            print("CONFLICTS:")
            for c in tm["conflicts"][-20:]:
                print(f"  {c['en']!r}: kept '{c['kept']}' ({c['kept_source']}) vs '{c['rejected']}' ({c['rejected_source']})")

    elif args.cmd == "lookup":
        tm = load_tm(args.tm)
        text = args.text.strip()
        exact = tm["entries"].get(text)
        hits = []
        if exact:
            hits.append((text, exact["zh"], exact["source"], "exact"))
        for en, e in tm["entries"].items():
            if en != text and (text in en or en in text):
                hits.append((en, e["zh"], e["source"], "partial"))
        if hits:
            for en, zh, src, kind in hits[:15]:
                print(f"{kind}: {en!r} -> {zh}  [{src}]")
        else:
            print("NO MATCH")

    elif args.cmd == "stats":
        tm = load_tm(args.tm)
        print(json.dumps({"entries": len(tm["entries"]), "conflicts": len(tm["conflicts"])}))


if __name__ == "__main__":
    main()
