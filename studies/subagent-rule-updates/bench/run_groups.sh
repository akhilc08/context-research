#!/usr/bin/env bash
# Run one benchmark config over case groups, at most 3 runners at once (16 GB host).
# Usage: bench/run_groups.sh <config> <groups-file> <cells> <output-prefix>
# Each line of the groups file is a comma list of case ids. Writes <output-prefix>-gN and a DONE marker.
set -u
cd "$(dirname "$0")/.."
config=$1; groups=$2; cells=$3; prefix=$4
run() {
  n=$1; cases=$2
  /opt/bench-venv/bin/python bench/run_bench.py --config "$config" --manifest bench/manifests/v1.json \
    --cells "$cells" --cases "$cases" --validation bench/manifests/validation-v1.json --allow-unscreened \
    --output "$prefix-g$n" --live > "$prefix-g$n.log" 2>&1
  echo "group $n exit $?"
}
export -f run; export config cells prefix
nl -ba -w1 -s' ' "$groups" | xargs -P 3 -L 1 bash -c 'run "$0" "$1"'
echo ALL_GROUPS_DONE > "$prefix.done"
