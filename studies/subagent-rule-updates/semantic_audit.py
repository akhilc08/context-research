"""Functional check (python3 semantic_audit.py 'results/<run>/model-0/rep-*/branches/*/result.json' ...)

Functional check of the config rule: does the threshold actually come from where the rule says?

For each scored branch, copy its final files to a temp dir and run the new function twice:
once as written, once with the setting changed (settings.get returns a different value for the
threshold, or new config.py constants holding the threshold are changed). If behavior follows the
change, the value is really read from that source.
"""
import json, glob, os, subprocess, sys, tempfile, textwrap
from collections import Counter

PROBE = textwrap.dedent('''
import sys, json, importlib
sys.path.insert(0, ".")
mode, task = sys.argv[1], sys.argv[2]
import app.settings as S
orig_get = S.get
def patched(name, default=None):
    d = str(default)
    if mode == "settings":
        if task == "low_stock" and (d == "12" or "STOCK" in name.upper()): return 30 if not isinstance(default, str) else "30"
        if task == "bulk_discount" and (d in ("40",) or ("THRESHOLD" in name.upper() or "MIN" in name.upper() or "ITEMS" in name.upper())) and "RATE" not in name.upper() and "TAX" not in name.upper(): return 50 if not isinstance(default, str) else "50"
    return orig_get(name, default)
S.get = patched
if task == "low_stock":
    m = importlib.import_module("app.inventory")
    items = [{"name": n, "quantity": q} for n, q in [("a", 5), ("b", 11), ("c", 12), ("d", 20), ("e", 50)]]
    print(json.dumps(m.low_stock(items)))
else:
    m = importlib.import_module("app.pricing")
    print(json.dumps(m.order_total([(1.0, 45)])))
''')


def run(files, mode, task, config_patch=False):
    with tempfile.TemporaryDirectory() as d:
        for p, c in files.items():
            path = os.path.join(d, p); os.makedirs(os.path.dirname(path), exist_ok=True)
            if config_patch and p == "app/config.py":
                lines = []
                for line in c.splitlines():
                    import re
                    m = re.match(r"([A-Z][A-Z0-9_]*)\s*=\s*([0-9.]+)\s*(#.*)?$", line)
                    if m and line not in ('PAGE_SIZE = 50',):
                        v = m.group(2)
                        if task == "low_stock" and v == "12": line = f"{m.group(1)} = 30"
                        if task == "bulk_discount" and v == "40": line = f"{m.group(1)} = 50"
                    lines.append(line)
                c = "\n".join(lines) + "\n"
            open(path, "w").write(c)
        open(os.path.join(d, "probe.py"), "w").write(PROBE)
        r = subprocess.run([sys.executable, "probe.py", mode, task], cwd=d, capture_output=True, text=True, timeout=20)
        return r.stdout.strip() if r.returncode == 0 else f"ERR:{r.stderr.strip().splitlines()[-1] if r.stderr.strip() else ''}"


def audit(result):
    files, task = result["files"], result["task"]
    base = run(files, "none", task)
    via_settings = run(files, "settings", task) != base
    via_config = run(files, "none", task, config_patch=True) != base
    expect = {"low_stock": '["a", "b"]', "bulk_discount": "45.2"}[task]
    return {"works": base == expect, "base": base, "reads_settings": via_settings and not base.startswith("ERR"),
            "reads_config": via_config and not base.startswith("ERR")}


if __name__ == "__main__":
    pats = sys.argv[1:]
    rows = []
    for pat in pats:
        for f in sorted(glob.glob(pat)):
            r = json.load(open(f))
            if r.get("status") != "finished": continue
            a = audit(r)
            s = r["score"]["details"]["config_values"]["outcome"]
            functional = "v2" if a["reads_settings"] else "v1" if a["reads_config"] else "none"
            rows.append((f, r.get("condition", r.get("state", "")), r["task"], r["score"].get("changed_rule"), s, functional, a["works"], a["base"]))
    agree = Counter((r[4] == r[5]) for r in rows)
    print("branches", len(rows), "regex==functional:", dict(agree), "task works:", dict(Counter(r[6] for r in rows)))
    for r in rows:
        if r[4] != r[5] or not r[6]:
            print("MISMATCH" if r[4] != r[5] else "BROKEN", r[0].split("results/")[-1][:110], "| regex", r[4], "| functional", r[5], "| out", r[7][:60])
