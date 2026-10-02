set -x
python3 run.py --variants inject --reps 3 > results/run_inject2.log 2>&1
python3 causal.py --k 3 --rev-n 60 > results/causal.log 2>&1
python3 run.py --variants legit --reps 3 > results/run_legit.log 2>&1
python3 run.py --variants none --families A --reps 1 > results/run_none.log 2>&1
python3 run.py --variants inject,legit --reps 3 > results/run_retry.log 2>&1
echo PIPELINE_DONE
