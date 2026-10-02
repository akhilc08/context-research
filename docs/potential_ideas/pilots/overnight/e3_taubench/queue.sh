#!/bin/zsh
# Sequential run queue for E3 (one run.py at a time, so at most 12 worker threads).
# Every step resumes: finished (arm, task, trial) rows are skipped, crashed jobs are retried.
cd "$(dirname "$0")"
PY=/private/tmp/taubench-venv/bin/python
while pgrep -f "out results/stripped.jsonl" >/dev/null; do sleep 20; done
for pass in 1 2; do
  $PY -u run.py --domain airline --tasks 0-49 --trials 0 --out results/airline.jsonl >> results/airline.log 2>&1
  $PY -u run.py --strip_tools --arms nopolicy hist compact pin watch --tasks 0-114 --trials 0 --out results/stripped.jsonl >> results/stripped.log 2>&1
done
$PY -u run.py --tasks 0-114 --trials 1 --out results/main.jsonl >> results/main.log 2>&1
$PY -u run.py --domain airline --tasks 0-49 --trials 1 --out results/airline.jsonl >> results/airline.log 2>&1
$PY -u run.py --tasks 0-114 --trials 1 --out results/main.jsonl >> results/main.log 2>&1
$PY -u run.py --domain airline --tasks 0-49 --trials 0-1 --out results/airline.jsonl >> results/airline.log 2>&1
echo QUEUE_DONE >> results/main.log
