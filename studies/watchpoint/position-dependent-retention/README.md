# Pilot: position-dependent constraint retention

Run on 2026-09-23 against `qwen/qwen3-30b-a3b-instruct-2507` via OpenRouter. See [`studies/watchpoint/docs/paper-plan.md`](../docs/paper-plan.md) for the design, the results table, and the caveats. This directory holds the exact script (`run_pilot.py`, requires `OPENROUTER_API_KEY` in the environment) and its raw output (`results.json`, 150 trial records) so the numbers in that document are reproducible and auditable rather than just asserted.

To re-run: `OPENROUTER_API_KEY=... python3 run_pilot.py` (writes `results.json` in the working directory, overwriting this one).
