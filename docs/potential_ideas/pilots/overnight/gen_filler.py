"""Generate a cached pool of realistic, rule-free coding-agent turns."""
import json, random
from concurrent.futures import ThreadPoolExecutor
from common import json_call, FILLER_PATH

THEMES = ["fixing a flaky integration test", "adding pagination to an API endpoint", "profiling a slow report job",
          "refactoring the invoice PDF renderer", "upgrading the ORM and fixing deprecation warnings",
          "adding structured logging", "debugging a timezone bug in scheduling", "writing unit tests for currency rounding",
          "tracking down a memory leak in a worker", "cleaning up CLI argument parsing", "adding retries to a webhook sender",
          "improving search index rebuild speed", "fixing a CSV export encoding bug", "adding type hints across a module",
          "investigating a failing CI lint step", "speeding up the test suite with fixtures"]

PROMPT = """Write {n} consecutive turns from the log of an autonomous coding agent working on "ledgerly", a Python billing service, while {theme}.
Each turn is ONE string of 25 to 70 words describing one concrete agent action AND its result: a shell command and its (abbreviated) output, a file edit with a tiny diff snippet, a test run with pass/fail counts, an error traceback line, a grep result, or a short reasoning note about what to try next. Use realistic file paths, function names, numbers, and error messages. Vary the action types.
Hard constraints: do NOT include any rules, policies, prohibitions, operator instructions, user messages, or statements of what the overall goal/objective is. Only the agent's own actions and observations.
Return JSON: {{"turns": [ ... {n} strings ... ]}}"""

def gen(theme):
    d = json_call(PROMPT.format(n=20, theme=theme), max_tokens=4000, temperature=0.9, tag="gen_filler")
    return [t for t in d["turns"] if isinstance(t, str) and 15 <= len(t.split()) <= 110]

with ThreadPoolExecutor(16) as ex:
    batches = list(ex.map(gen, THEMES))
turns = [t for b in batches for t in b]
print(len(turns))
FILLER_PATH.write_text(json.dumps(turns, indent=1))
