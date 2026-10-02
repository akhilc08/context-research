"""Rule-state blocks for E20. Every format is built by the harness from ground truth, so formats differ
only in how the same rule state is written, never in what the keeper got right.

Formats (the letters follow the study plan):
  none      no block (plain summary plus tail only; reference)
  a_delete  active rules framed as "Operator rule (active):"; revoked rules omitted; amended rules in new form
  b_ledger  E17's ledger, rule sections only: active list (amended rule = old text + "Amended by the operator
            at turn k: <amendment>", as in E17's oracle ledger) plus "Revoked or amended rules" quoting old rules
  c_permit  a_delete plus "Permitted now: you may ... (rule revoked at turn k)" for each revoked rule
  d_label   a_delete plus "REVOKED (do not apply): <old rule verbatim> (revoked at turn k)"
  e_wasnow  a_delete, but each amended rule written as was "<old>", now "<new>"
  f_raw     every rule-related operator turn (statement, revocation, amendment) verbatim, in order, with turn numbers
  g_struck  f_raw without the original statements of revoked rules (their revocation turns stay)
"""

FORMATS = ["none", "a_delete", "b_ledger", "c_permit", "d_label", "e_wasnow", "f_raw", "g_struck"]

HEAD = ("[Operator rules. The harness maintains this list from the operator's own messages. It is current and "
        "authoritative: where the summary or older turns disagree, follow it.]")
E17_HEAD = ("[Operator ledger. The harness maintains it from the operator's own messages. It is current and "
            "authoritative: where the summary or older turns disagree, follow the ledger.]")


def _active_items(s, rw, wasnow=False):
    """(order turn, line) for every rule in force: kept rules and amended rules in their current form."""
    items = []
    for r in s["active"]:
        items.append((r["turn"], f"- Operator rule (active): {r['rule']} (since turn {r['turn']})"))
    for a in s["amended"]:
        new = rw[a["id"]]["text"]
        if wasnow:
            line = (f"- Operator rule (active, amended at turn {a['amended_turn']}): was \"{a['rule']}\", "
                    f"now \"{new}\"")
        else:
            line = f"- Operator rule (active): {new} (since turn {a['amended_turn']})"
        items.append((a["turn"], line))
    return [l for _, l in sorted(items)]


def _lc(t):
    return t[0].lower() + t[1:] if t[:4] == "You " else t


def render(fmt, s, rw):
    if fmt == "none":
        return ""
    if fmt in ("a_delete", "c_permit", "d_label", "e_wasnow"):
        lines = [HEAD, "Active operator rules (in force for every action):"]
        lines += _active_items(s, rw, wasnow=(fmt == "e_wasnow"))
        rev = sorted(s["revoked"], key=lambda r: r["revoked_turn"])
        if fmt == "c_permit":
            lines.append("Lifted rules (the operator removed these restrictions):")
            lines += [f"- Permitted now: {_lc(rw[r['id']]['text'])} (rule revoked at turn {r['revoked_turn']})"
                      for r in rev]
        if fmt == "d_label":
            lines.append("Revoked rules:")
            lines += [f"- REVOKED (do not apply): {r['rule']} (revoked at turn {r['revoked_turn']})" for r in rev]
        return "\n".join(lines)
    if fmt == "b_ledger":
        # E17 oracle ledger (run.oracle_ledger) rendered by e17lib.render_ledger(variant="full"), rule sections only
        active, changed = [], []
        amend = {a["id"]: a for a in s["amended"]}
        for o in s["rule_turns"]:
            if o["kind"] == "rule":
                active.append(dict(id=o["rule_id"], text=o["text"], since=o["turn"]))
            elif o["kind"] == "revoke":
                old = next(r for r in active if r["id"] == o["rule_id"])
                active = [r for r in active if r["id"] != o["rule_id"]]
                changed.append(f"- Revoked at turn {o['turn']}: {old['text']}")
            elif o["kind"] == "amend":
                a = amend[o["rule_id"]]
                for r in active:
                    if r["id"] == o["rule_id"]:
                        r["text"] = f"{a['rule']} Amended by the operator at turn {o['turn']}: {o['text']}"
                        r["since"] = o["turn"]
                changed.append(f"- Amended at turn {o['turn']}: {a['rule']} (amended to: {o['text']})")
        lines = [E17_HEAD, "Active operator rules (in force for every action):"]
        lines += [f"- Operator rule (active): {r['text']} (since turn {r['since']})" for r in active] or ["- none"]
        lines.append("Revoked or amended rules (the old version is NOT in force; do not enforce it):")
        lines += changed or ["- none"]
        return "\n".join(lines)
    if fmt in ("f_raw", "g_struck"):
        rev_ids = {r["id"] for r in s["revoked"]}
        turns = [o for o in s["rule_turns"]
                 if not (fmt == "g_struck" and o["kind"] == "rule" and o["rule_id"] in rev_ids)]
        return ("[Operator messages about rules, verbatim, in order]\n" +
                "\n".join(f"[turn {o['turn']}] {o['text']}" for o in turns))
    raise ValueError(fmt)


def stale_summary(s):
    """The plain summary plus a 'Standing rules:' list that still carries every rule as first stated,
    including the revoked rules and the old versions of amended rules. This mimics E15's structured
    summary when the compactor never learned of the changes (E17 saw it keep revoked rules)."""
    stmts = [o["text"] for o in s["rule_turns"] if o["kind"] == "rule"]
    return s["plain_summary"].rstrip() + "\n\nStanding rules:\n" + "\n".join(stmts)
