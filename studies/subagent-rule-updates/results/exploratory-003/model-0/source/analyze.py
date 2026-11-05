"""Recompute descriptive tables from recorded branch actions. No model calls."""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

from harness import ARMS, BRIEFINGS, TASKS, WORKER_TYPES, score


def analyze(output: Path) -> dict:
    output = Path(output)
    manifest = json.loads((output / "manifest.json").read_text())
    records = []
    for path in sorted(output.glob("rep-*/branches/*/result.json")):
        row = json.loads(path.read_text())
        if row.get("score") is not None:
            recomputed = score(row["task"], row["events"], row["files"], finished=row["score"]["finished"],
                               active_rule_version=row["controller_rule_version"])
            if recomputed != row["score"]:
                raise ValueError(f"Stored score does not match recorded actions: {path}")
        records.append(row)
    groups = defaultdict(list)
    for row in records:
        groups[row.get("briefing", "briefed"), row["arm"], row["worker_type"], row["task"]].append(row)
    rows = []
    errors = {"provider_error", "delivery_instrumentation_error", "manager_protocol_error", "model_protocol_error"}
    for briefing, arm, worker_type, task in [(b, a, w, t) for b in BRIEFINGS for a in ARMS for w in WORKER_TYPES for t in TASKS]:
                data = groups[briefing, arm, worker_type, task]
                if not data and briefing not in manifest["config"].get("briefings", ["briefed"]):
                    continue
                valid = [r for r in data if r["status"] not in errors and r.get("score") is not None]
                rows.append({
                    "briefing": briefing, "arm": arm, "worker_type": worker_type, "task": task,
                    "planned": manifest["config"]["repetitions"], "recorded": len(data), "scored": len(valid),
                    "finished": sum(r["status"] == "finished" for r in valid),
                    "task_success": sum(r["score"]["task_success"] for r in valid),
                    "policy_violation": sum(r["score"]["policy_adherence"] is False for r in valid),
                    "policy_unknown": sum(r["score"]["policy_adherence"] is None for r in valid),
                    "aborted_policy_violations": sum(r.get("score") is not None and r["status"] in errors and r["score"]["policy_adherence"] is False for r in data),
                    "note_completed": sum(r["score"]["note_completed"] for r in valid),
                    "approval_workflow_ok": sum(r["score"]["approval_workflow_ok"] for r in valid),
                    "unnecessary_or_wrong_approval": sum(bool(r["score"]["unnecessary_or_wrong_approval_requests"]) for r in valid),
                    "delivery_verified": sum(r.get("delivery_verified", False) for r in data),
                    "relayed_U1": sum("U1" in r.get("relay_user_message_ids", []) for r in data),
                    "statuses": dict(Counter(r["status"] for r in data)),
                })
    summary = {"model": manifest["selected_model"], "planned_branches": manifest["planned_branches"],
               "recorded_branches": len(records), "statuses": dict(Counter(r["status"] for r in records)), "groups": rows,
               "observed_policy_violations_all_recorded": sum(r.get("score") is not None and r["score"]["policy_adherence"] is False for r in records),
               "scope": "One synthetic dependency-approval scenario. No compaction or automatic extraction. Descriptive counts only."}
    (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    lines = ["# Exploratory rule-update results", "", f"Model: `{summary['model']['id']}`.", "",
             summary["scope"], "", f"Recorded {len(records)} of {summary['planned_branches']} planned branches.", "",
             "Success, violation, note, and unnecessary-approval counts use the scored denominator. Protocol/infrastructure errors are separate, including any violations observed before those branches aborted. Missing branches are not treated as successes or model failures. Unparsable dependency states are unknown, not compliant.", "",
             "| Briefing | Delivery | Worker | Task | Recorded/planned | Scored | Success | Violation | Policy unknown | Note done | Approval workflow OK | Wrong/extra approval | U1 relayed | Aborted violations |",
             "|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for r in rows:
        lines.append(f"| {r['briefing']} | {r['arm']} | {r['worker_type']} | {r['task']} | {r['recorded']}/{r['planned']} | {r['scored']} | {r['task_success']} | {r['policy_violation']} | {r['policy_unknown']} | {r['note_completed']} | {r['approval_workflow_ok']} | {r['unnecessary_or_wrong_approval']} | {r['relayed_U1']} | {r['aborted_policy_violations']} |")
    lines += ["", "## Status counts", "", "```json", json.dumps(summary["statuses"], indent=2), "```", "",
              "New-worker creation-pin and refreshed-store inputs are identical before any further update. Existing-worker manager-relay and creation-pin inputs are also identical because R0 delivery is controlled. Differences within those pairs reflect sampling/execution variation, not distinct mechanisms.", "",
              "Manager messages are source-linked assisted relays. The manager may select U0/U1 but cannot create authenticated amendments in free-form text. Existing and new workers have separately tailored briefs, so their difference alone is not a causal estimate of persistence.", "",
              "Unbriefed branches receive only the work order, with no manager brief or relayed user messages. There, `manager_relay` means no automatic rule delivery, so only the delivery arm decides whether the worker sees the amendment.", ""]
    (output / "tables.md").write_text("\n".join(lines))
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    analyze(parser.parse_args().output)
