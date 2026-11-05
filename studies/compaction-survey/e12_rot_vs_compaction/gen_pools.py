"""Generate the two filler pools E12 needs for long sessions.

data/filler_long.json: the shared 308-turn pool plus about 1,400 new realistic coding-agent turns on new themes,
  so a 1,600-turn session repeats almost nothing verbatim. Same prompt as the shared gen_filler.py.
data/neutral_turns.json: about 1,700 low-salience turns of the same length that have nothing to do with software
  (an almanac of nature and geography notes). Used for the pure-distraction (length-only) control.

Usage: python3 gen_pools.py [--model M]
"""
import argparse, json, random, re, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "shared"))
import orclient  # noqa: E402
from common import load_filler  # noqa: E402

THEMES = [
    "migrating a cron job to a task queue", "fixing a race condition in invoice numbering", "adding OpenAPI schema docs",
    "tuning PostgreSQL query plans for the aging report", "replacing a homegrown retry helper with tenacity",
    "adding a feature flag around tax calculation", "fixing a broken Docker build cache", "splitting a god-class in payments",
    "adding mypy strict mode to one package", "debugging intermittent Redis connection resets", "speeding up the CSV importer",
    "writing property-based tests for money arithmetic", "fixing an N+1 query in the customer list endpoint",
    "adding rate limiting to the public API", "cleaning up dead code after a feature removal",
    "fixing a locale-dependent number formatting bug", "adding health-check endpoints", "upgrading Python from 3.10 to 3.12",
    "debugging a deadlock in the batch reconciler", "adding a dry-run mode to a data backfill script",
    "investigating slow pytest collection", "fixing pagination cursors that skip rows", "adding metrics for queue latency",
    "refactoring settings loading into pydantic", "fixing a flaky time-dependent unit test", "reducing Docker image size",
    "adding CSV column validation with clear error messages", "porting a shell script to a Python CLI",
    "investigating rounding drift in multi-currency totals", "adding an index and migration for invoice lookups",
    "fixing an off-by-one in billing period boundaries", "improving error messages in the admin API",
    "adding snapshot tests for email templates", "profiling memory use of the PDF batch job",
    "replacing print debugging with structured logs in a worker", "fixing broken links in generated API docs",
    "adding concurrency limits to an outbound HTTP client", "debugging a failing pre-commit hook",
    "consolidating duplicated date-parsing helpers", "adding a retry-safe outbox table for events",
    "investigating a sporadic 502 from the load balancer health check", "making a slow fixture session-scoped",
    "fixing a JSON serialization error for Decimal fields", "adding coverage reporting for a new module",
    "debugging stale cache entries in the plan catalog", "renaming a confusing module and updating imports",
    "adding a CLI command to export usage records", "tracking down a 3x slowdown after a dependency bump",
    "fixing unicode handling in customer names", "adding graceful shutdown to the worker process",
    "auditing TODO comments and filing follow-ups", "speeding up linting by caching ruff results",
    "fixing a timezone-naive datetime comparison", "writing integration tests for the refund flow",
    "debugging an import cycle between two packages", "adding request IDs to log lines", "parallelizing a slow report",
    "fixing wrong HTTP status codes in error handlers", "adding a schema check for a config YAML file",
    "debugging why a celery task is retried forever", "cleaning up warnings in the test output",
    "adding benchmark scripts for the pricing engine", "fixing a broken alembic downgrade", "adding seed data for local dev",
    "investigating a memory spike when loading big invoices", "simplifying a deeply nested conditional in discounts",
    "improving the README developer setup steps", "fixing a sort order bug in statement lines",
    "adding a small cache in front of the exchange-rate lookup", "tracking a flaky network test to a DNS timeout",
]
PROMPT = """Write {n} consecutive turns from the log of an autonomous coding agent working on "ledgerly", a Python billing service, while {theme}.
Each turn is ONE string of 25 to 70 words describing one concrete agent action AND its result: a shell command and its (abbreviated) output, a file edit with a tiny diff snippet, a test run with pass/fail counts, an error traceback line, a grep result, or a short reasoning note about what to try next. Use realistic file paths, function names, numbers, and error messages. Vary the action types.
Hard constraints: do NOT include any rules, policies, prohibitions, operator instructions, user messages, or statements of what the overall goal/objective is. Only the agent's own actions and observations.
Return JSON: {{"turns": [ ... {n} strings ... ]}}"""

NEUTRAL_TOPICS = [
    "river deltas", "alpine lakes", "migratory birds", "desert plants", "coral reefs", "tidal pools", "old lighthouses",
    "mountain passes", "prairie grasses", "cave formations", "volcanic islands", "fog banks", "autumn forests",
    "salt marshes", "glaciers", "moss and lichens", "small fishing harbours", "canal towns", "orchards in spring",
    "sand dunes", "monsoon weather", "northern lights", "river otters", "bee colonies", "tea terraces", "cloud types",
    "pebble beaches", "wild mushrooms", "highland sheep", "mangrove coasts", "frozen waterfalls", "meadow flowers",
    "stone bridges", "lake ferries", "night insects", "rainforest canopies", "chalk cliffs", "hot springs",
    "olive groves", "steppe horses", "kelp forests", "island lighthouses", "peat bogs", "cherry blossom seasons",
    "basalt columns", "rice paddies", "tundra in summer", "village markets", "windmills", "estuary birds",
]
NPROMPT = """Write {n} consecutive short entries from a calm, descriptive nature-and-places almanac about {topic}.
Each entry is ONE string of 20 to 40 words: a plain descriptive observation (what something looks like, when it happens, where it is found). No instructions, no advice, no questions, no people giving orders, no technology or software, no numbers that look like code.
Return JSON: {{"turns": [ ... {n} strings ... ]}}"""


def jcall(prompt, model, tag):
    for _ in range(4):
        raw = orclient.chat([{"role": "user", "content": prompt}], max_tokens=4000, temperature=0.9, tag=tag,
                            json_mode=True, model=model)
        m = re.search(r"\{.*\}", raw, re.S)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                pass
    return {"turns": []}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=orclient.MODEL)
    a = ap.parse_args()
    if a.model.endswith(":free"):
        raise SystemExit("':free' models are not allowed")

    def gen(theme):
        d = jcall(PROMPT.format(n=20, theme=theme), a.model, "e12_gen_filler")
        return [t for t in d.get("turns", []) if isinstance(t, str) and 15 <= len(t.split()) <= 110]

    def ngen(args):
        topic, k = args
        d = jcall(NPROMPT.format(n=18, topic=topic), a.model, "e12_gen_neutral")
        return [t for t in d.get("turns", []) if isinstance(t, str) and 12 <= len(t.split()) <= 60]

    with ThreadPoolExecutor(10) as ex:
        batches = list(ex.map(gen, THEMES))
        nb = list(ex.map(ngen, [(t, k) for k in range(2) for t in NEUTRAL_TOPICS]))
    filler = load_filler() + [t for b in batches for t in b]
    neutral = [t for b in nb for t in b]
    (HERE / "data" / "filler_long.json").write_text(json.dumps(filler, indent=1))
    (HERE / "data" / "neutral_turns.json").write_text(json.dumps(neutral, indent=1))
    wf = sum(len(t.split()) for t in filler) / len(filler)
    wn = sum(len(t.split()) for t in neutral) / len(neutral)
    print(f"filler {len(filler)} turns, mean {wf:.1f} words; neutral {len(neutral)} turns, mean {wn:.1f} words")


if __name__ == "__main__":
    main()
