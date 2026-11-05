"""Run a sibling study's script on a second backbone (default nvidia/nemotron-3-ultra-550b-a55b:free; override with X1_MODEL).

The studies refuse ':free' ids to protect the shared daily free-model quota; the coordinator
lifts that guard here for small, budgeted replications. Reasoning is disabled for the second backbone,
because with reasoning on Qwen spent the output budget thinking and returns truncated text.
"""
import sys, threading
from pathlib import Path

OVERNIGHT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(OVERNIGHT / "shared"))
import orclient

import os
QWEN = os.environ.get("X1_MODEL", "nvidia/nemotron-3-ultra-550b-a55b:free")
d = list(orclient.chat.__defaults__)  # (max_tokens, temperature, model, reasoning_effort, ...)
d[2], d[3] = QWEN, None
orclient.chat.__defaults__ = tuple(d)

# Nemotron writes its reasoning into the visible reply even with reasoning disabled, so short
# output caps (the studies use 200 tokens for decisions) cut it off before the answer line.
# Raise every cap to at least MIN_OUT tokens; only output length changes, not the prompts.
MIN_OUT = 1500
_orig_chat = orclient.chat


def _chat_min_out(messages, max_tokens=400, *a, **k):
    return _orig_chat(messages, max(max_tokens, MIN_OUT), *a, **k)


_chat_min_out.__defaults__ = None
orclient.chat = _chat_min_out


def run_e1(argv):
    sys.path.insert(0, str(OVERNIGHT / "e01_rule_scaling"))
    import run
    run.set_model = lambda m: run.MODEL.__setitem__("id", m)
    run._SEM = threading.Semaphore(4)
    sys.argv = ["run.py"] + argv + ["--model", QWEN]
    run.main()


def run_e2(argv):
    sys.path.insert(0, str(OVERNIGHT / "e02_goal_resurrection"))
    import e2lib
    e2lib.set_model = lambda m: setattr(e2lib, "MODEL", m)
    import run
    run.L.set_model = e2lib.set_model
    sys.argv = ["run.py"] + argv + ["--model", QWEN, "--workers", "4"]
    run.main()


if __name__ == "__main__":
    {"e1": run_e1, "e2": run_e2}[sys.argv[1]](sys.argv[2:])
