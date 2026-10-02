"""Hand-label validation of the process detectors.

  python3 validate.py dump   -> results/validation_items.md (blind: no arm, no flags) and
                                results/validation_key.json (item -> run, write index, detector flags)
  python3 validate.py score  -> reads results/validation_labels.json ({"item id": [0 or 1, "note"]})
                                and prints precision, recall and Cohen's kappa

Sampling: all writes from results/retail.jsonl and results/airline.jsonl; a write is "flagged" if
any primary detector fires on it. Seed 0. 40 flagged + 40 unflagged retail, 20 + 20 airline.
"""
import collections, json, random, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import detectors as D  # noqa: E402

FILES = [HERE / "results/retail.jsonl", HERE / "results/airline.jsonl"]
N = {"retail": (40, 40), "airline": (20, 20)}


def all_writes():
    out = []
    for p in FILES:
        for line in p.read_text().splitlines():
            r = json.loads(line)
            res = D.analyze(r)
            prim = set(D.PRIMARY[r["domain"]])
            for w in res["writes"]:
                fl = [f for f in w["flags"] if f in prim]
                out.append((r, w, fl))
    return out


def show(r, w):
    ev = r["events"]
    i = w["idx"]
    lines = []
    tools = [e for e in ev[:i] if e[0] == "tool"]
    lines.append("Earlier tool calls: " + ("; ".join(
        f"{e[1]}({', '.join(f'{k}={json.dumps(v)[:40]}' for k, v in (e[2] or {}).items())})"
        f"{' -> ERROR ' + e[3][:60] if str(e[3]).startswith('Error') else (' -> ' + e[3][:40] if e[1].startswith('find_user') else '')}"
        for e in tools) or "none"))
    turns = [e for e in ev[:i] if e[0] in ("user", "agent")][-4:]
    for e in turns:
        lines.append(f"**{e[0]}**: {e[1][:1500]}")
    e = ev[i]
    lines.append(f"**WRITE**: `{e[1]}({json.dumps(e[2])[:600]})` -> {e[3][:200]}")
    if len(e) > 5 and r["domain"] == "airline":
        pre = dict(e[5])
        if "reservation" in pre:
            res = pre["reservation"]
            pre["reservation"] = {k: res.get(k) for k in ("origin", "destination", "flight_type", "cabin",
                                                         "created_at", "insurance", "total_baggages",
                                                         "nonfree_baggages")}
            pre["reservation"]["flights"] = [(f["flight_number"], f["date"]) for f in res.get("flights", [])]
            pre["reservation"]["n_passengers"] = len(res.get("passengers", []))
        lines.append(f"DB before write: {json.dumps(pre)[:900]}")
    return "\n\n".join(lines)


def dump():
    rng = random.Random(0)
    ws = all_writes()
    items, key = [], {}
    for dom, (nf, nu) in N.items():
        fl = [x for x in ws if x[0]["domain"] == dom and x[2]]
        un = [x for x in ws if x[0]["domain"] == dom and not x[2]]
        print(f"{dom}: {len(fl)} flagged writes, {len(un)} unflagged writes")
        pick = rng.sample(fl, min(nf, len(fl))) + rng.sample(un, min(nu, len(un)))
        items += pick
        key[f"_pop_{dom}"] = [len(fl), len(un)]
    rng.shuffle(items)
    md = ["# Detector validation items (blind)\n",
          "Label each write 1 if it breaks any checked rule (see README), else 0.\n"]
    for k, (r, w, fl) in enumerate(items):
        iid = f"V{k:03d}"
        key[iid] = {"domain": r["domain"], "arm": r["arm"], "task": r["task"], "trial": r["trial"],
                    "idx": w["idx"], "flags": fl, "all_flags": w["flags"]}
        md.append(f"\n## {iid} ({r['domain']})\n\n{show(r, w)}\n")
    (HERE / "results/validation_items.md").write_text("\n".join(md))
    (HERE / "results/validation_key.json").write_text(json.dumps(key, indent=1))
    print(f"{len(items)} items written")


def kappa(pairs):
    n = len(pairs)
    po = sum(a == b for a, b in pairs) / n
    pa = sum(a for a, _ in pairs) / n
    pb = sum(b for _, b in pairs) / n
    pe = pa * pb + (1 - pa) * (1 - pb)
    return (po - pe) / (1 - pe) if pe < 1 else float("nan")


def fixed_flags(key):
    """Primary flags of each sampled write under the post-hoc corrected detector."""
    rows = {}
    for p in FILES:
        for line in p.read_text().splitlines():
            r = json.loads(line)
            rows[(r["domain"], r["arm"], r["task"], r["trial"])] = r
    out = {}
    for i, k in key.items():
        if i.startswith("_"):
            continue
        r = rows[(k["domain"], k["arm"], k["task"], k["trial"])]
        prim = set(D.PRIMARY[r["domain"]])
        w = next(w for w in D.analyze(r, fixed=True)["writes"] if w["idx"] == k["idx"])
        out[i] = [f for f in w["flags"] if f in prim]
    return out


def score():
    key = json.loads((HERE / "results/validation_key.json").read_text())
    print("## Pre-registered detectors\n")
    _score(key)
    fx = fixed_flags(key)
    key2 = {i: (dict(v, flags=fx[i]) if not i.startswith("_") else v) for i, v in key.items()}
    print("\n## Post-hoc corrected confirmation detector (exploratory; same sample, so population weights "
          "use the pre-registered strata and the recall estimate is approximate)\n")
    _score(key2)


def _score(key):
    lab = json.loads((HERE / "results/validation_labels.json").read_text())
    print("| domain | flagged sampled | flagged and labeled violation | unflagged sampled | unflagged but labeled violation "
          "| precision | recall in sample | recall weighted to population | kappa (sample) |")
    print("|---|---|---|---|---|---|---|---|---|")
    tot = []
    for dom in ("retail", "airline", "all"):
        ids = [i for i in key if not i.startswith("_") and (dom == "all" or key[i]["domain"] == dom)]
        pairs = [(int(bool(key[i]["flags"])), int(lab[i][0])) for i in ids if i in lab]
        fl = [b for a, b in pairs if a]
        un = [b for a, b in pairs if not a]
        prec = sum(fl) / len(fl) if fl else float("nan")
        fnr = sum(un) / len(un) if un else float("nan")
        rec_s = sum(fl) / (sum(fl) + sum(un)) if (sum(fl) + sum(un)) else float("nan")
        doms = ["retail", "airline"] if dom == "all" else [dom]
        tp = fn = 0.0
        for d in doms:
            nf, nu = key[f"_pop_{d}"]
            fd = [int(lab[i][0]) for i in key if not i.startswith("_") and key[i]["domain"] == d and key[i]["flags"] and i in lab]
            ud = [int(lab[i][0]) for i in key if not i.startswith("_") and key[i]["domain"] == d and not key[i]["flags"] and i in lab]
            tp += nf * (sum(fd) / len(fd) if fd else 0)
            fn += nu * (sum(ud) / len(ud) if ud else 0)
        rec_w = tp / (tp + fn) if tp + fn else float("nan")
        print(f"| {dom} | {len(fl)} | {sum(fl)} | {len(un)} | {sum(un)} | {prec:.3f} | {rec_s:.3f} | {rec_w:.3f} | "
              f"{kappa(pairs):.3f} |")
    # per detector precision
    c = collections.defaultdict(lambda: [0, 0])
    for i in key:
        if i.startswith("_") or i not in lab:
            continue
        for f in key[i]["flags"]:
            c[f][0] += 1
            c[f][1] += int(lab[i][0])
    print("\nPer-detector precision (flagged items carrying that flag): " +
          ", ".join(f"{f} {v[1]}/{v[0]}" for f, v in sorted(c.items())))


if __name__ == "__main__":
    {"dump": dump, "score": score}[sys.argv[1]]()
