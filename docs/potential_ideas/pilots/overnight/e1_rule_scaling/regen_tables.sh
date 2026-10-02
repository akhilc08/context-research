#!/bin/sh
# Regenerate every E1 table from the raw result files (no model calls).
cd "$(dirname "$0")"
python3 analyze.py results_fixed.jsonl > tables_fixed.md
[ -f results_scaled.jsonl ] && python3 analyze.py results_scaled.jsonl > tables_scaled.md
echo "wrote tables_fixed.md${1:+ }$( [ -f tables_scaled.md ] && echo and tables_scaled.md)"
