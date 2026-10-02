"""E4 follow-up (exploratory, decided after seeing the main results): KV-store key reconciliation.

The main run showed the watchpoint re-injecting stale values: the extractor sometimes wrote an
update under a new key instead of reusing the old one, so the old value survived as an orphan
key, and because it disagreed with the (correct) notes, the comparator patched it back in as a
"[current]" reminder. This script rebuilds each task's store online with one extra call per
session that deletes keys superseded by a newer key for the same fact, then reruns pin,
watchpoint, and KV-only on the reconciled store. Per-session extraction output is reused from
the main run (recovered as the diff between consecutive store snapshots), so the only change is
the reconciliation step. Methods never see gold answers or stale labels.

    /private/tmp/supersede-venv/bin/python e4_dedupe.py --sets lme
"""
import argparse, json
from concurrent.futures import ThreadPoolExecutor

import e4
from e4 import call, cached, parse_json, render_kv, run_watch, question_prompt, ANSWER_SYSTEM, PIN_BLOCK

DEDUPE = (
    "Below is a key-value FACT STORE about a user. Each entry shows the session in which it was "
    "last written. Some keys may describe the SAME fact as another key (for example "
    "'user | parents length of stay' and 'parents | length of stay'), so the store holds an "
    "older and a newer value for one fact. For each such duplicate group, list the OLDER keys "
    "that are superseded by a newer key for the same fact. Do not list keys that describe "
    "different facts, and never list a key written in the latest session.\n"
    "Return JSON {{\"delete\": [\"<key>\", ...]}} (empty list if none).\n\nSTORE:\n{store}")


def run_dedupe_store(t, ext):
    store, written, snaps, log, prev = {}, {}, [], [], {}
    for i, snap in enumerate(ext["snapshots"]):
        upd = {k: v for k, v in snap.items() if prev.get(k) != v}
        prev = snap
        for k, v in upd.items():
            store[k] = v
            written[k] = i
        deleted = []
        if i > 0 and len(store) > 1:
            listing = "\n".join(f"- [session {written[k] + 1}] {k}: {v}" for k, v in store.items())
            j = parse_json(call(t, "dedupe", f"dd{i}", DEDUPE.format(store=listing), 1500, json_mode=True)) or {}
            for k in j.get("delete", []):
                k = str(k).strip().lower()
                if k in store and written[k] < i:  # guard: only older keys can be removed
                    deleted.append(k)
                    del store[k]
        snaps.append(dict(store))
        log.append({"n_updates": len(upd), "deleted": deleted})
    return {"snapshots": snaps, "log": log, "store_size": len(store), "store_chars": len(render_kv(store))}


def run_task(t):
    ext = json.loads(e4.unit_path(t, "extract").read_text())
    n300 = json.loads(e4.unit_path(t, "notes300").read_text())
    dd = cached(t, "extract_dd", lambda: run_dedupe_store(t, ext))

    def pin():
        kv = dd["snapshots"][-1]
        q = question_prompt(n300["notes"] + PIN_BLOCK.format(kv=render_kv(kv)), t["question"])
        return {"answer": call(t, "pin_dd", "answer", q, 400, system=ANSWER_SYSTEM), "calls": 1,
                "memory_chars": len(n300["notes"]) + len(render_kv(kv))}

    def kvo():
        q = question_prompt("(no notes)" + PIN_BLOCK.format(kv=render_kv(dd["snapshots"][-1])), t["question"])
        return {"answer": call(t, "kvonly_dd", "answer", q, 400, system=ANSWER_SYSTEM), "calls": 1}

    arms = {"pin_dd": cached(t, "pin_dd", pin), "watch_dd": cached(t, "watch_dd", lambda: run_watch(t, dd, unit="watch_dd")),
            "kvonly_dd": cached(t, "kvonly_dd", kvo)}

    def judge():
        base = json.loads(e4.unit_path(t, "judge").read_text())
        out = {"stale_label": base.get("stale_label", t["stale"])}
        abst = e4.ABST in t["answer"].lower()
        for a, r in arms.items():
            tmpl = e4.JUDGE_ABST if (t["set"] == "lme" and abst) else e4.JUDGE
            yn = call(t, "judge", f"yn_{a}", tmpl.format(q=t["question"], gold=t["answer"], ans=r["answer"]), 200)
            v4 = None
            if t["set"] == "lme" and out["stale_label"]:
                v4 = call(t, "judge", f"j4_{a}", e4.JUDGE4.format(q=t["question"], gold=t["answer"],
                          stale="; ".join(out["stale_label"]), ans=r["answer"]), 200).lower().split()[0].strip(".'\"")
            out[a] = {"yes": yn.lower().startswith("y"), "raw": yn, "v4": v4}
        return out
    j = cached(t, "judge_dd", judge)
    print(t["set"], t["qid"], {a: j[a]["yes"] for a in arms}, flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sets", nargs="+", default=["lme"])
    ap.add_argument("--n-synth", type=int, default=60)
    a = ap.parse_args()
    tasks = [t for t in e4.load_tasks(a.sets, a.n_synth) if e4.unit_path(t, "judge").exists()]
    with ThreadPoolExecutor(8) as ex:
        for f in [ex.submit(run_task, t) for t in tasks]:
            try:
                f.result()
            except Exception as e:
                print("FAILED", repr(e)[:300], flush=True)


if __name__ == "__main__":
    main()
