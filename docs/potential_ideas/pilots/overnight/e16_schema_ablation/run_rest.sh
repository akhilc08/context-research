#!/bin/sh
# Follow-up phases, run in sequence after the main 3-round, 150-word run.
cd "$(dirname "$0")"
python3 run_e16.py run 40 30 --rounds 3 --words 150 --arms plain,e9_structured,schema,add_S1,pin,schema_pin,minimal,minimal_pin,full
python3 run_e16.py run 0 40 --rounds 3 --words 150 --arms minimal,minimal_pin
python3 run_e16.py judge 0 70
python3 run_e16.py run 0 40 --rounds 3 --words 300 --arms plain,e9_structured,schema,loo_S1,loo_S2,loo_S3,loo_S4,loo_S5,loo_S6,add_S1,add_S2,add_S3,add_S4,add_S5,pin,schema_pin,minimal,minimal_pin
python3 run_e16.py judge 0 40
python3 run_e16.py run 0 30 --rounds 6 --words 150 --arms plain,e9_structured,schema,add_S1,pin,schema_pin,minimal,minimal_pin,full
python3 run_e16.py judge 0 30
echo ALLDONE
