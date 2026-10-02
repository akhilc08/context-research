#!/bin/sh
# Main runs: confirmatory arms (2 trials), then the added method-comparison arms (trial 0).
cd "$(dirname "$0")"
PY=/private/tmp/taubench-venv/bin/python
W=${WORKERS:-25}
$PY run.py --domain both --trials 0-1 --workers $W \
  --arms hist compact pin pinrules watch nopolicy minimal compact_prog recipe recipe_noprog >> results/main_A.log 2>&1
$PY run.py --domain both --trials 0 --workers $W \
  --arms recipe_ckpt fifo headtail mask source e9 keeprules e15list prov anchor grace selfcheck roundtrip repair ledger >> results/main_B.log 2>&1
echo done >> results/main_B.log
