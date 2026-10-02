"""Fix the gate thresholds on the calibration split only, before any gated arm is run.

Events: the final compaction of each ungated arm (plain, structured, always) in each calibration transcript.
Label: primary harm. Threshold: maximize Youden's J (ties to the lower threshold). Writes thresholds.json.
python3 calibrate.py
"""
import json, os
from pathlib import Path

from labels import harm, judged, youden_threshold, auroc

HERE = Path(__file__).resolve().parent
OUT = Path(os.environ.get("E10_OUT", str(HERE)))
split = json.loads((HERE / "split.json").read_text())
evs = []
for tid in split["calibration"]:
    p = OUT / "raw" / f"t{tid:04d}.json"
    if not p.exists():
        continue
    rec = json.loads(p.read_text())
    if not rec.get("base_done") or not judged(rec, ["plain", "structured", "always"]):
        continue
    for arm in ("plain", "structured", "always"):
        a = rec["arms"][arm]
        evs.append(dict(tid=tid, arm=arm, y=harm(a), rt_generic=a["sig"]["rt_generic"]["score"],
                        rt_aligned=a["sig"]["rt_aligned"]["score"], pc=a["sig"]["pc"]["score"]))
y = [e["y"] for e in evs]
out = dict(n_events=len(evs), n_transcripts=len({e["tid"] for e in evs}), harm_rate=sum(y) / len(y))
for s in ("rt_generic", "pc", "rt_aligned"):
    sc = [e[s] for e in evs]
    out[s] = youden_threshold(sc, y)["threshold"]
    out[s + "_detail"] = dict(youden_threshold(sc, y), auroc=auroc(sc, y))
(OUT / "thresholds.json").write_text(json.dumps(out, indent=1))
print(json.dumps(out, indent=1))
