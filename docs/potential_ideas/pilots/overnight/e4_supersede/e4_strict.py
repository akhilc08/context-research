"""E4 follow-up (exploratory, decided after seeing the main results): a stricter watchpoint
comparator. The main run's comparator only checks that the tracked value is PRESENT in the
notes' restatement, so it passes notes that list a superseded value next to the current one.
Here a restatement passes only if it also adds no other content words. Everything else
(store, notes protocol, patch format) is unchanged; only the comparator differs.

    /private/tmp/supersede-venv/bin/python e4_strict.py --sets lme synth_std synth_hard
"""
import argparse, json
from concurrent.futures import ThreadPoolExecutor

import e4
from e4 import cached, call, run_watch, value_matches_strict


def run_task(t):
    ext = json.loads(e4.unit_path(t, "extract").read_text())
    w = cached(t, "watch_strict", lambda: run_watch(t, ext, unit="watch_strict", matcher=value_matches_strict))

    def judge():
        base = json.loads(e4.unit_path(t, "judge").read_text())
        out = {"stale_label": base.get("stale_label", t["stale"])}
        abst = t["set"] == "lme" and e4.ABST in t["answer"].lower()
        tmpl = e4.JUDGE_ABST if abst else e4.JUDGE
        yn = call(t, "judge", "yn_watch_strict", tmpl.format(q=t["question"], gold=t["answer"], ans=w["answer"]), 200)
        v4 = None
        if t["set"] == "lme" and out["stale_label"]:
            v4 = call(t, "judge", "j4_watch_strict", e4.JUDGE4.format(q=t["question"], gold=t["answer"],
                      stale="; ".join(out["stale_label"]), ans=w["answer"]), 200).lower().split()[0].strip(".'\"")
        out["watch_strict"] = {"yes": yn.lower().startswith("y"), "raw": yn, "v4": v4}
        return out
    j = cached(t, "judge_strict", judge)
    print(t["set"], t["qid"], j["watch_strict"]["yes"], flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sets", nargs="+", default=["lme", "synth_std", "synth_hard"])
    ap.add_argument("--n-synth", type=int, default=60)
    ap.add_argument("--workers", type=int, default=12)
    a = ap.parse_args()
    tasks = [t for t in e4.load_tasks(a.sets, a.n_synth) if e4.unit_path(t, "judge").exists()]
    with ThreadPoolExecutor(min(a.workers, 12)) as ex:
        for f in [ex.submit(run_task, t) for t in tasks]:
            try:
                f.result()
            except Exception as e:
                print("FAILED", repr(e)[:300], flush=True)


if __name__ == "__main__":
    main()
