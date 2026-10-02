"""Copy the inputs E20 holds fixed from E17 into data/sessions_e20.json.

For each of E17's 60 sessions: the ground-truth rules (3 active, 3 revoked, 2 amended), the rule-related
operator turns (rule statements, revocations, amendments) with their turn numbers, every operator turn
(for reference), the last 6 turns (the verbatim tail E17 showed the agent), and E17's plain recursive
summary of everything before the tail (from E17's Space Bunny run). No model calls.

Usage: python3 prep.py
"""
import json

import e20lib as L

E17 = L.OVERNIGHT / "e17_operator_ledger"
TAIL = 6


def main():
    sessions = json.loads((E17 / "data" / "sessions.json").read_text())
    out = []
    for s in sessions:
        res = json.loads((E17 / "results" / "space_bunny" / "sessions" / f"{s['sid']}.json").read_text())
        t = s["truth"]
        n = len(s["turns"])
        out.append(dict(
            sid=s["sid"], n_turns=n, tail=s["turns"][-TAIL:], tail_start=n - TAIL + 1,
            plain_summary=res["summaries"]["plain"],
            operator_turns=s["operator_turns"],
            rule_turns=[o for o in s["operator_turns"] if o["kind"] in ("rule", "revoke", "amend")],
            active=t["active"], revoked=t["revoked"], amended=t["amended"]))
    (L.HERE / "data" / "sessions_e20.json").write_text(json.dumps(out, indent=1))
    print(len(out), "sessions")


if __name__ == "__main__":
    main()
