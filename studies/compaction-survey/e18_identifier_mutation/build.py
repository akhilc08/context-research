"""Build E18 scenarios: 16 transcripts, each planting 12 identifiers of different types.

Each identifier gets one condition, rotated so every type sees every condition 4 times:
  once        - mentioned once
  repeated    - mentioned three times (intro plus two reminders)
  distractor  - mentioned once, plus a turn naming a near duplicate in a different role
  superseded  - first given as an old value, later corrected to the target value
The planting segment (goal turn, planted turns, some filler) is compacted in round 1. Rounds 2 to 10
each add 8 filler turns from the shared realistic pool. Output: data/scenarios.json
"""
import json, random, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "shared"))
import idents as I  # noqa: E402

SEED = 18018
ROUNDS, LATER_CHUNK = 10, 8
PROJECTS = [("billing", "acme", "PAY"), ("search", "globex", "SRCH"), ("notifications", "initech", "NOTIF"),
            ("payroll", "umbrella", "PAYR"), ("inventory", "hooli", "STOCK"), ("auth", "stark", "AUTH"),
            ("shipping", "wayne", "SHIP"), ("analytics", "tyrell", "ANLT"), ("checkout", "cyberdyne", "CHK"),
            ("ledger", "soylent", "LEDG"), ("catalog", "vandelay", "CAT"), ("messaging", "wonka", "MSG"),
            ("reporting", "oscorp", "RPT"), ("scheduler", "aperture", "SCHED"), ("gateway", "massive", "GW"),
            ("refunds", "duff", "REF")]


def main():
    rng = random.Random(SEED)
    pool = [t for t in json.loads((HERE.parent / "shared" / "data" / "filler_turns.json").read_text())
            if not re.search(r"INV-\d|stg|s3://|==\d", t)]
    pkgs = list(I.PKG_ROLES)
    rng.shuffle(pkgs)
    scenarios = []
    for si, (svc, co, tp) in enumerate(PROJECTS):
        hexs = lambda n: "".join(rng.choice("0123456789abcdef") for _ in range(n))  # noqa: E731
        sc = {"id": f"s{si:02d}", "svc": svc, "company": co, "tprefix": tp, "package": pkgs[si],
              "pkg_role": I.PKG_ROLES[pkgs[si]], "noise_hash1": hexs(12), "noise_hash2": hexs(12),
              "noise_digest": hexs(16)}
        items, seqs = [], {}
        for ti, t in enumerate(I.TYPES):
            cond = I.CONDS[(ti + si) % 4]
            target, near = I.gen_values(t, sc, rng)
            role = I.ROLE[t].format(role=sc["pkg_role"], name=sc["package"])
            probe = I.PROBE[t].format(role=sc["pkg_role"], svc=svc)
            if cond == "superseded":
                seq = [("intro_old", I.intro(t, near, sc)), ("correction", I.supersede_new(t, near, target, sc))]
            elif cond == "distractor":
                seq = [("intro", I.intro(t, target, sc)), ("distractor", I.distract(t, target, near, sc))]
                if rng.random() < 0.5:  # distractor sometimes comes first
                    seq.reverse()
            elif cond == "repeated":
                seq = [("intro", I.intro(t, target, sc)), ("remind", I.remind(t, target, sc, 0)),
                       ("remind", I.remind(t, target, sc, 1))]
            else:
                seq = [("intro", I.intro(t, target, sc))]
            seqs[t] = seq
            items.append({"type": t, "cond": cond, "target": target, "near": near, "role": role,
                          "probe": probe, "source": I.SOURCE[t]})
        # random merge preserving within-type order
        planted, remaining = [], {t: list(s) for t, s in seqs.items()}
        while any(remaining.values()):
            t = rng.choice([k for k, v in remaining.items() if v])
            kind, text = remaining[t].pop(0)
            planted.append((t, kind, text))
        start = rng.randrange(len(pool))
        fill = [pool[(start + k) % len(pool)] for k in range(len(pool))]
        fi = 0
        turns = [f"Operator: We are fixing duplicate ledger writes in the {svc} service when webhooks are "
                 f"retried. Find the bug, fix it, ship it to staging, and clean up the affected data."]
        meta = [{"kind": "goal"}]
        for t, kind, text in planted:
            if rng.random() < 0.5:
                turns.append(fill[fi]); meta.append({"kind": "filler"}); fi += 1
            turns.append(text); meta.append({"kind": kind, "type": t})
        for _ in range(2):  # the verbatim tail after round 1 is filler, not a planted turn
            turns.append(fill[fi]); meta.append({"kind": "filler"}); fi += 1
        chunks = [list(range(len(turns)))]
        for r in range(2, ROUNDS + 1):
            idx = []
            for _ in range(LATER_CHUNK):
                turns.append(fill[fi]); meta.append({"kind": "filler"}); idx.append(len(turns) - 1); fi += 1
            chunks.append(idx)
        sc.update({"items": items, "turns": turns, "meta": meta, "chunks": chunks})
        # sanity: every target appears verbatim in the transcript
        full = "\n".join(turns)
        for it in items:
            assert it["target"] in full, (sc["id"], it)
        scenarios.append(sc)
    (HERE / "data").mkdir(exist_ok=True)
    (HERE / "data" / "scenarios.json").write_text(json.dumps(scenarios, indent=1))
    n_pl = [len(s["chunks"][0]) for s in scenarios]
    print(f"{len(scenarios)} scenarios, {sum(len(s['items']) for s in scenarios)} identifiers, "
          f"planting segment {min(n_pl)} to {max(n_pl)} turns, total turns {len(scenarios[0]['turns'])}+")


if __name__ == "__main__":
    main()
