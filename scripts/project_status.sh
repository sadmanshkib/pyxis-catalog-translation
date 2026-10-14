#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 SHKIB SADMAN (sadmanshkib)
# Read-only survey of the Pyxis translation project state.
#   bash scripts/project_status.sh
# Answers "what changed / where are we" without sweeping the whole project tree
# (a recursive walk of C:/Projects/Pyxis_Lab times out on the video/render trees).

REPO="C:/Projects/Pyxis_Lab/github/pyxis-catalog-translation"
PROJ="C:/Projects/Pyxis_Lab/Translation"
TM="C:/Projects/Pyxis_Lab/AI TNS/old works/translation_memory.json"

echo "== skill mirror repo: $REPO =="
git -C "$REPO" log --oneline -5 2>/dev/null || echo "  (not reachable / not a git repo)"
echo "-- working tree --"
git -C "$REPO" status --porcelain=v1 2>/dev/null | head -20
echo "-- ahead/behind origin/main (left=origin, right=local) --"
git -C "$REPO" rev-list --left-right --count origin/main...main 2>/dev/null \
  || echo "  (remote unreachable; local state only)"

for d in Catalog Extract PC-200_Manual PC-200_EN Manuals Ling-Hui Lynn; do
  echo
  echo "== newest files in $d =="
  ls -lt --time-style=long-iso "$PROJ/$d" 2>/dev/null \
    | grep -v -E '\.(png|jpg|jpeg|tif|tiff)$' | head -6
done

echo
echo "== per-run write-ups (method of record) =="
ls -lt --time-style=long-iso "$PROJ/Extract"/*.md "$PROJ/PC-200_Manual"/*.md \
  "$PROJ/Catalog"/*.md "$PROJ/PC-200_Manual/merge_fix/FIX_REPORT.md" 2>/dev/null | head -20

echo
echo "== translation memory: $TM =="
python - "$TM" <<'PY' 2>/dev/null || echo "  (TM file or python unavailable)"
import collections, json, sys
d = json.load(open(sys.argv[1], encoding='utf-8'))
e = d.get('entries', d)
print('entries', len(e), '| conflicts', len(d.get('conflicts', [])))
c = collections.Counter(v.get('source') for v in e.values() if isinstance(v, dict))
print('by source:', dict(c))
PY
