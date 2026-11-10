"""Adjudicate extracted tunable candidates, then label sessions and screen tasks. No paid calls without --live.

A model from a different family than the worker reads each finished run's candidates (file, line, and a
few lines of context) and says which values are tunables. It is not told the run's arm or the rules.
Gold-fix extractions are adjudicated the same way, as a check of the extractor. Then each run gets a
session label (bench/tunables.py label_session) and each task a screening verdict:

kept if the no-rule arm is "bare" in at least `min_bare` runs and each told arm "follows" in at least
`min_follows` runs, counting finished runs only.

python3 bench/adjudicate_tunables.py --run results/bench-tunables-screen-001/model-0 --live
python3 bench/adjudicate_tunables.py --run ... --summarize-only
"""
from __future__ import annotations

import argparse
import collections
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

STUDY = Path(__file__).resolve().parents[1]
if str(STUDY) not in sys.path:
    sys.path.insert(0, str(STUDY))

from bench import tunables as T  # noqa: E402
from relay import save  # noqa: E402

JUDGE = {"id": "anthropic/claude-opus-5.5", "provider": "Anthropic"}
SYSTEM = """You review numeric values added to a software project's source code.

For each numbered value, decide whether it is a TUNABLE: a policy number a project could reasonably want to
configure, such as a threshold, rate, limit, timeout, retry count, interval, delay, buffer or cache size,
page size, or tolerance used as a cutoff.

Not tunables: counters and indices, sizes fixed by a data format, protocol or status codes, limits set by an
external API or specification, mathematical or physical constants, unit conversions, version numbers, values
needed for correctness, and test data.

Judge the value itself. Ignore how it is written (inline, named constant, or read from the environment).
Answer with only a JSON object: {"values": [{"id": <id>, "tunable": true or false, "reason": "<short reason>"}]}
with one entry per value."""
MIN_BARE, MIN_FOLLOWS = 2, 2


def candidate_prompt(candidates: List[dict]) -> str:
    parts = []
    for c in candidates:
        number = int(c["value"]) if float(c["value"]).is_integer() else c["value"]
        parts.append("Value %d: %s in %s, line %d\n```python\n%s\n```" % (c["id"], number, c["path"], c["line"],
                                                                          c["snippet"]))
    return "\n\n".join(parts)


def parse_verdicts(text: str, ids: List[int]) -> Dict[int, dict]:
    # The judge sometimes writes a sentence or a fence around the object, so decode from where it starts.
    start = text.find('{"values"')
    if start < 0:
        raise ValueError("no values object in the judge's reply")
    data, _ = json.JSONDecoder().raw_decode(text[start:])
    verdicts = {int(v["id"]): {"tunable": bool(v["tunable"]), "reason": str(v.get("reason", ""))}
                for v in data["values"]}
    if set(verdicts) != set(ids):
        raise ValueError("verdict ids %s do not match candidate ids %s" % (sorted(verdicts), sorted(ids)))
    return verdicts


def records(run: Path) -> List[Path]:
    return sorted(run.glob("tasks/*/*/rep*/record.json")) + sorted(run.glob("tasks/*/setup.json"))


def _extraction(path: Path) -> Optional[dict]:
    data = json.loads(path.read_text())
    if path.name == "setup.json":
        gold = data.get("gold") or {}
        return gold.get("extraction") if gold.get("status") == "finished" else None
    return data.get("extraction") if data.get("status") == "finished" else None


def adjudicate(client: Any, run: Path, out: Path) -> dict:
    """Adjudications keyed by the record's path relative to the run. Existing entries are kept."""
    done = json.loads(out.read_text()) if out.exists() else {}
    for path in records(run):
        key = str(path.relative_to(run))
        extraction = _extraction(path)
        if key in done or extraction is None:
            continue
        cands = extraction["candidates"]
        if not cands:
            done[key] = {}
            continue
        messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": candidate_prompt(cands)}]
        response = client.complete(messages, json_mode=True, tag="adjudicate/" + key)
        verdicts = parse_verdicts(response["choices"][0]["message"]["content"], [c["id"] for c in cands])
        done[key] = {str(k): v for k, v in verdicts.items()}
        save(out, done)
    save(out, done)
    return done


def summarize(run: Path, adjudications: dict) -> dict:
    labels: Dict[str, Dict[str, List[str]]] = collections.defaultdict(lambda: collections.defaultdict(list))
    status: Dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    gold: Dict[str, Any] = {}
    for path in records(run):
        key = str(path.relative_to(run))
        data = json.loads(path.read_text())
        if path.name == "setup.json":
            ext = _extraction(path)
            tid = data["task_id"]
            gold[tid] = {"valid": bool(data.get("validation", {}).get("valid")),
                         "candidates": len(ext["candidates"]) if ext else None,
                         "tunables": sum(v["tunable"] for v in adjudications.get(key, {}).values()) if ext else None}
            continue
        status[data["task_id"]][data["status"]] += 1
        if data["status"] != "finished" or key not in adjudications:
            continue
        ext = data["extraction"]
        tunable_ids = [int(k) for k, v in adjudications[key].items() if v["tunable"]]
        labels[data["task_id"]][data["arm"]].append(T.label_session(data["arm"], ext["candidates"], tunable_ids,
                                                                    ext["unscorable"]))
    tasks = {}
    for tid in sorted(set(gold) | set(labels)):
        arms = {a: dict(collections.Counter(labels[tid][a])) for a in T.ARMS}
        kept = (arms["none"].get("bare", 0) >= MIN_BARE and arms["const"].get("follows", 0) >= MIN_FOLLOWS
                and arms["env"].get("follows", 0) >= MIN_FOLLOWS)
        tasks[tid] = {"gold": gold.get(tid), "arms": arms, "statuses": dict(status[tid]), "kept": kept}
    summary = {"criteria": {"min_bare": MIN_BARE, "min_follows": MIN_FOLLOWS}, "tasks": tasks,
               "kept": sorted(t for t, v in tasks.items() if v["kept"])}
    save(run / "screening.json", summary)
    return summary


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True, help="A screen_tunables model directory")
    parser.add_argument("--budget", type=float, default=15.0)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--summarize-only", action="store_true")
    args = parser.parse_args(argv)
    out = args.run / "adjudications.json"
    if not args.summarize_only:
        if not args.live:
            pending = [p for p in records(args.run) if _extraction(p) is not None]
            print("WOULD_ADJUDICATE records=%d (no model calls made)" % len(pending))
            return 0
        from provider import OpenRouterClient
        n = len(list(args.run.glob("adjudication-*")))
        client = OpenRouterClient(args.run / ("adjudication-%d" % n), model=JUDGE["id"], provider_name=JUDGE["provider"],
                                  budget_usd=args.budget, max_calls=5000, temperature=0.0, max_tokens=4000,
                                  reasoning_effort="low", timeout_retries=2, rate_limit_retries=6)
        try:
            adjudicate(client, args.run, out)
        finally:
            save(client.output_dir / "provider_summary.json", client.summary())
    summary = summarize(args.run, json.loads(out.read_text()) if out.exists() else {})
    kept = summary["kept"]
    print("SCREENING tasks=%d kept=%d %s" % (len(summary["tasks"]), len(kept), ",".join(kept)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
