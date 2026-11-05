"""Sanity check: run the detectors on tau-bench's gold action sequences.

Every gold write is preceded by a synthetic agent question and user "yes", so the confirmation
detector is neutral; any other flag on a gold trajectory is either a detector bug or a case where
the gold actions themselves deviate from the written policy. Usage: python gold_check.py
"""
import collections, json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import detectors, run
from tau_bench.types import Action


def gold_events(domain, ti):
    env = run.make_env(domain)
    env.task_index = ti
    env.data = env.data_load_func()
    task = env.tasks[ti]
    ev = [["user", "hi"]]
    for a in task.actions:
        if a.name in detectors.WRITES[domain]:
            ev += [["agent", "Shall I proceed? Would you like travel insurance?", 0], ["user", "yes"]]
        pre = run.snapshot(domain, env.data, a.name, a.kwargs) if a.name in detectors.WRITES[domain] else None
        r = env.step(Action(name=a.name, kwargs=a.kwargs))
        e = ["tool", a.name, a.kwargs, r.observation[:1500], 0]
        if pre is not None:
            e.append(pre)
        ev.append(e)
    return ev


def main():
    for domain, n in (("retail", 115), ("airline", 50)):
        c, ex = collections.Counter(), collections.defaultdict(list)
        for ti in range(n):
            res = detectors.analyze({"domain": domain, "events": gold_events(domain, ti)})
            for fl in res["run"]:
                c[fl] += 1
                ex[fl].append(ti)
        print(domain, dict(c))
        for k, v in ex.items():
            print("  ", k, v[:20])


if __name__ == "__main__":
    main()
