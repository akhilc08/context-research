"""Run E18: recursive compaction chains, then the behavioral probe for every arm.

Phases (each resumable through an on-disk call cache):
  compact  - for every scenario x budget (120, 300) x summarizer (plain, verbatim): 10 recursive rounds.
             Round 1 compacts the planting segment; rounds 2 to 10 each add 8 filler turns. tail_k = 2.
  probe    - at R in {1, 3, 6, 10}, ask the agent for the exact command for each identifier's task, under
             arms full, plain, verbatim, registry, registry_rec, pin_op.

Usage: python3 run.py --phase compact|probe|all [--model MODEL] [--workers 8] [--limit N]
Raw outputs: data/<model-slug>/chains.jsonl, data/<model-slug>/probes.jsonl, data/<model-slug>/cache.jsonl
"""
import argparse, hashlib, json, sys, threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
from orclient import chat, MODEL  # noqa: E402
from common import SUMMARY_PROMPT, AGENT_SYSTEM, render, context_block  # noqa: E402
import idents as I  # noqa: E402

BUDGETS = [120, 300]
ROUNDS_PROBED = [1, 3, 6, 10]
TAIL_K = 2
VERBATIM_PROMPT = SUMMARY_PROMPT + (
    " Exception: copy every identifier (file paths, package names and versions, commit hashes, ticket and "
    "invoice ids, hostnames, ports, environment variable names, and numeric values) exactly, character for "
    "character, inside backticks.")
SUMMARIZERS = {"plain": SUMMARY_PROMPT, "verbatim": VERBATIM_PROMPT}
ARMS = ["full", "plain", "verbatim", "registry", "registry_rec", "pin_op"]
ASK_SUFFIX = ("\n\nReply with exactly one line, nothing else: either\nCOMMAND: <the exact shell command you will run>\n"
              "or, if you cannot run it without more information,\nASK: <your question to the operator>")


def slug(model):
    return model.replace("/", "_").replace(":", "_")


class Cache:
    def __init__(self, path):
        self.path, self.lock, self.d = path, threading.Lock(), {}
        if path.exists():
            for line in path.read_text().splitlines():
                try:
                    r = json.loads(line)
                    self.d[r["k"]] = r["v"]
                except Exception:
                    pass

    @staticmethod
    def _key(messages, max_tokens, temperature, model, salt):
        return hashlib.sha256(json.dumps([messages, max_tokens, temperature, model, salt]).encode()).hexdigest()

    def has(self, messages, max_tokens, temperature, model, salt=""):
        return self._key(messages, max_tokens, temperature, model, salt) in self.d

    def call(self, messages, max_tokens, temperature, model, tag, salt=""):
        k = self._key(messages, max_tokens, temperature, model, salt)
        if k in self.d:
            return self.d[k]
        v = chat(messages, max_tokens=max_tokens, temperature=temperature, model=model, tag=tag)
        with self.lock:
            self.d[k] = v
            with open(self.path, "a") as f:
                f.write(json.dumps({"k": k, "v": v}) + "\n")
        return v


def chain(cache, model, sc, words, summ):
    """Recursive compaction with per-round history. Returns list of {round, summary, tail_idx, seen}."""
    instr = SUMMARIZERS[summ].format(words=words)
    turns = sc["turns"]
    summary, tail, out = "", [], []
    for r, idx in enumerate(sc["chunks"], 1):
        seq = tail + idx
        body, tail = seq[:-TAIL_K], seq[-TAIL_K:]
        prior = f"[Summary of earlier turns]\n{summary}\n\n" if summary else ""
        # turn numbers in the log restart at the body's absolute position
        log = "\n".join(f"[turn {i + 1}] {turns[i]}" for i in body)
        prompt = f"{instr}\n\n{prior}[Log]\n{log}"
        summary = cache.call([{"role": "user", "content": prompt}], words * 3 + 600, 0.3, model,
                             f"e18|compact|{summ}{words}").strip()
        out.append({"round": r, "summary": summary, "tail": tail, "seen": seq[-1] + 1})
    return out


def build_context(arm, sc, ch, R):
    turns = sc["turns"]
    if arm == "full":
        n = ch["seen"]
        return "[Session transcript so far, verbatim]\n" + render(turns[:n])
    tail_txt = [turns[i] for i in ch["tail"]]
    # render the verbatim tail with absolute turn numbers
    tail_block = "[Most recent turns, verbatim]\n" + "\n".join(f"[turn {i + 1}] {turns[i]}" for i in ch["tail"])
    extras = ""
    seen = turns[:ch["seen"]]
    if arm == "registry":
        extras = I.build_registry(seen, recency=False)
    elif arm == "registry_rec":
        extras = I.build_registry(seen, recency=True)
    elif arm == "pin_op":
        extras = "[Operator messages from this session, pinned verbatim by the harness]\n" + "\n".join(
            f"[turn {i + 1}] {t}" for i, t in enumerate(seen) if t.startswith("Operator:"))
    parts = [f"[Summary of earlier turns in this session]\n{ch['summary']}"]
    if extras:
        parts.append(extras)
    parts.append(tail_block)
    del tail_txt
    return "\n\n".join(parts), extras


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", default="all")
    ap.add_argument("--model", default=MODEL)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--limit", type=int, default=0, help="only the first N scenarios")
    a = ap.parse_args()
    out = HERE / "data" / slug(a.model)
    out.mkdir(parents=True, exist_ok=True)
    cache = Cache(out / "cache.jsonl")
    S = json.loads((HERE / "data" / "scenarios.json").read_text())
    if a.limit:
        S = S[:a.limit]
    workers = min(a.workers, 8)

    if a.phase in ("compact", "all"):
        jobs = [(sc, w, s) for sc in S for w in BUDGETS for s in SUMMARIZERS]
        rows = []
        with ThreadPoolExecutor(workers) as ex:
            futs = {ex.submit(chain, cache, a.model, sc, w, s): (sc["id"], w, s) for sc, w, s in jobs}
            for i, f in enumerate(as_completed(futs), 1):
                sid, w, s = futs[f]
                rows.append({"scenario": sid, "budget": w, "summarizer": s, "rounds": f.result()})
                if i % 8 == 0:
                    print(f"chains {i}/{len(jobs)}", flush=True)
        rows.sort(key=lambda r: (r["scenario"], r["budget"], r["summarizer"]))
        with open(out / "chains.jsonl", "w") as f:
            for r in rows:
                f.write(json.dumps(r) + "\n")

    if a.phase in ("probe", "all"):
        chains = {(r["scenario"], r["budget"], r["summarizer"]): r["rounds"]
                  for r in map(json.loads, (out / "chains.jsonl").read_text().splitlines())}
        jobs = []
        for sc in S:
            for R in ROUNDS_PROBED:
                for w in BUDGETS:
                    for arm in ARMS:
                        if arm == "full" and w != BUDGETS[0]:
                            continue  # full context does not depend on the budget
                        summ = "verbatim" if arm == "verbatim" else "plain"
                        ch = chains[(sc["id"], w, summ)][R - 1]
                        if arm == "full":
                            ctx, extras = build_context("full", sc, ch, R), ""
                        else:
                            ctx, extras = build_context(arm, sc, ch, R)
                        for it in sc["items"]:
                            jobs.append((sc, R, None if arm == "full" else w, arm, it, ctx, extras))

        def do(job):
            sc, R, w, arm, it, ctx, extras = job
            user = f"{ctx}\n\n[New request from the operator]\n{it['probe']}{ASK_SUFFIX}"
            msgs = [{"role": "system", "content": AGENT_SYSTEM}, {"role": "user", "content": user}]
            raw = cache.call(msgs, 300, 0.7, a.model, f"e18|probe|{arm}")
            return {"scenario": sc["id"], "R": R, "budget": w, "arm": arm, "type": it["type"],
                    "cond": it["cond"], "target": it["target"], "near": it["near"], "reply": raw.strip(),
                    "ctx_chars": len(ctx), "extra_chars": len(extras)}

        print(f"{len(jobs)} probes", flush=True)
        rows = []
        with ThreadPoolExecutor(workers) as ex:
            futs = [ex.submit(do, j) for j in jobs]
            for i, f in enumerate(as_completed(futs), 1):
                rows.append(f.result())
                if i % 500 == 0:
                    print(f"probes {i}/{len(jobs)}", flush=True)
        rows.sort(key=lambda r: (r["scenario"], r["R"], r["budget"] or 0, r["arm"], r["type"]))
        with open(out / "probes.jsonl", "w") as f:
            for r in rows:
                f.write(json.dumps(r) + "\n")


if __name__ == "__main__":
    main()
