"""Identifier types for E18: value generators, near-duplicate makers, planting templates,
probe tasks, deterministic matchers, and the harness identifier registry (no model calls)."""
import re

TYPES = ["host", "port", "package", "commit", "ticket", "invoice", "envvar", "threshold",
         "image", "branch", "bucket", "path"]
CONDS = ["once", "repeated", "distractor", "superseded"]

PKG_ROLES = {"tenacity": "retry library", "httpx": "HTTP client", "orjson": "JSON serializer",
             "structlog": "logging library", "cryptography": "crypto library", "redis": "Redis client",
             "celery": "task queue library", "pydantic": "validation library", "sqlalchemy": "ORM",
             "boto3": "AWS SDK", "psycopg": "Postgres driver", "aiohttp": "async HTTP library",
             "protobuf": "protobuf runtime", "urllib3": "low-level HTTP library",
             "msgpack": "msgpack serializer", "backoff": "backoff library"}

# --------------------------------------------------------------------- generation


def swap_digits(s, rng):
    """Swap two different adjacent-or-near digits in s (a typo-like near duplicate)."""
    idx = [i for i, c in enumerate(s) if c.isdigit()]
    for _ in range(50):
        i, j = sorted(rng.sample(idx, 2))
        if s[i] != s[j]:
            return s[:i] + s[j] + s[i + 1:j] + s[i] + s[j + 1:]
    return s[:-1] + str((int(s[-1]) + 1) % 10)


def gen_values(t, sc, rng):
    """Return (target, near_duplicate) for type t in scenario sc. The near duplicate serves as the
    distractor (distractor condition) or the superseded old value (superseded condition)."""
    svc, co = sc["svc"], sc["company"]
    if t == "host":
        kind = rng.choice(["pg", "db", "pgsql", "maindb"])
        n = rng.randint(2, 7)
        dom = f"{co}-int.net"
        return f"{kind}-stg-{n}.{dom}", f"{kind}-stg-{n - 1}.{dom}"
    if t == "port":
        v = str(rng.randint(6400, 6499))
        while len(set(v)) < 3:
            v = str(rng.randint(6400, 6499))
        return v, swap_digits(v, rng)
    if t == "package":
        name = sc["package"]
        v = f"{rng.randint(1, 9)}.{rng.randint(1, 9)}.{rng.randint(1, 9)}"
        while len(set(v.replace('.', ''))) < 3:
            v = f"{rng.randint(1, 9)}.{rng.randint(1, 9)}.{rng.randint(1, 9)}"
        a, b, c = v.split(".")
        return f"{name}=={v}", f"{name}=={a}.{c}.{b}"
    if t == "commit":
        h = "".join(rng.choice("0123456789abcdef") for _ in range(12))
        h2 = h[:4] + "".join(rng.choice("0123456789abcdef") for _ in range(8))
        return h, h2
    if t == "ticket":
        v = f"{sc['tprefix']}-{rng.randint(1000, 9999)}"
        while len(set(v[-4:])) < 3:
            v = f"{sc['tprefix']}-{rng.randint(1000, 9999)}"
        return v, swap_digits(v, rng)
    if t == "invoice":
        v = f"INV-{rng.randint(10000, 99999)}"
        while len(set(v[-5:])) < 4:
            v = f"INV-{rng.randint(10000, 99999)}"
        return v, swap_digits(v, rng)
    if t == "envvar":
        base = f"{svc.upper()}_{rng.choice(['WEBHOOK_SIGNING_KEY', 'WEBHOOK_HMAC_SECRET', 'WH_SIGNING_SECRET'])}"
        return f"{base}_V2", base
    if t == "threshold":
        v = f"0.0{rng.randint(11, 89)}5"
        while len(set(v[3:])) < 3:
            v = f"0.0{rng.randint(11, 89)}5"
        return v, "0.0" + swap_digits(v[3:], rng)
    if t == "image":
        a, b, c = rng.randint(1, 4), rng.randint(10, 30), rng.randint(2, 9)
        repo = f"registry.{co}.io/{svc}-api"
        return f"{repo}:{a}.{b}.{c}", f"{repo}:{a}.{b}.{c - 1}"
    if t == "branch":
        slug = rng.choice(["dedupe-webhook-writes", "idempotent-webhook-retry", "fix-double-ledger-write",
                           "webhook-retry-dedupe"])
        return f"fix/{slug}-v2", f"fix/{slug}"
    if t == "bucket":
        r = rng.choice(["eu-west-1", "us-east-2", "eu-central-1", "ap-south-1"])
        r2 = {"eu-west-1": "eu-west-2", "us-east-2": "us-east-1", "eu-central-1": "eu-central-2",
              "ap-south-1": "ap-south-2"}[r]
        return f"s3://{co}-{svc}-exports-{r}", f"s3://{co}-{svc}-exports-{r2}"
    if t == "path":
        mod = rng.choice(["reconcile", "webhooks", "sync", "ingest"])
        f = rng.choice(["ledger_writer", "event_sink", "dedupe_store", "retry_handler"])
        return f"services/{svc}/{mod}/{f}.py", f"services/{svc}/{mod}/{f}_legacy.py"
    raise ValueError(t)


# Role descriptions (used by the judge and as the probe's referent) and probe tasks.
ROLE = {
    "host": "the staging database host the migration must run against",
    "port": "the PgBouncer listen port on the staging pooler",
    "package": "the agreed pinned version of the {role} ({name})",
    "commit": "the commit that contains the duplicate-write fix",
    "ticket": "the tracking ticket for the duplicate-write bug",
    "invoice": "the invoice whose webhook failed and must be reprocessed",
    "envvar": "the environment variable that holds the current webhook signing secret",
    "threshold": "the reconciliation drift tolerance the operator chose",
    "image": "the container image built with the fix",
    "branch": "the branch the fix should be pushed on",
    "bucket": "the S3 bucket that holds the reconciliation exports",
    "path": "the source file containing the duplicate-write bug",
}

PROBE = {
    "host": "Run the pending Alembic migration (`alembic upgrade head`) against the staging database host.",
    "port": "Check that the PgBouncer listen port on the staging pooler is reachable through the SSH tunnel on localhost.",
    "package": "Install the agreed pinned version of the {role} into the virtualenv.",
    "commit": "Cherry-pick the commit that contains the duplicate-write fix onto the release branch.",
    "ticket": "Post a comment on the tracking ticket for the duplicate-write bug saying the fix is on staging (use the jira CLI).",
    "invoice": "Reprocess the invoice whose webhook failed, using ./bin/reprocess-invoice.",
    "envvar": "Check whether the environment variable holding the current webhook signing secret is set in this shell, without printing its value.",
    "threshold": "Run the reconciliation job (`python -m {svc}.reconcile`) with the drift tolerance the operator chose.",
    "image": "Deploy the container image built with the fix to the staging cluster with kubectl (deployment {svc}-api, container api).",
    "branch": "Push the fix branch to origin.",
    "bucket": "Download the reconciliation exports from S3 into ./exports.",
    "path": "Run ruff on the source file containing the duplicate-write bug.",
}

SOURCE = {"host": "op", "port": "tool", "package": "op", "commit": "tool", "ticket": "op", "invoice": "op",
          "envvar": "op", "threshold": "op", "image": "tool", "branch": "op", "bucket": "op", "path": "tool"}


def intro(t, v, sc):
    """First mention of value v in its role. Operator turns start with 'Operator:'."""
    svc = sc["svc"]
    return {
        "host": f"Operator: For the staging run, the database host is `{v}`. Run the schema migration there once the fix is merged.",
        "port": f"Ran `grep listen_port deploy/pgbouncer/staging.ini` (exit 0): `listen_port = {v}`. That is the PgBouncer listen port on the staging pooler.",
        "package": f"Operator: Pin the {sc['pkg_role']} to `{v}` for this fix; that is the version we agreed on with the platform team.",
        "commit": f"Ran `git log --oneline -3` (exit 0): `{v} fix({svc}): dedupe ledger writes on webhook retry` / `{sc['noise_hash1']} chore: bump lockfile` / `{sc['noise_hash2']} test: add retry fixtures`. The fix is commit `{v}`.",
        "ticket": f"Operator: Track this work on ticket {v}. Update it when the fix reaches staging.",
        "invoice": f"Operator: The invoice whose webhook failed last night is {v}. Once the fix is deployed we need to reprocess it.",
        "envvar": f"Operator: The webhook signing secret now lives in `{v}`; scripts must read it from that variable.",
        "threshold": f"Operator: Run the reconciliation job with a drift tolerance of {v}; anything above that should be flagged.",
        "image": f"Ran `docker build -t {v} . && docker push {v}` (exit 0): `pushed {v} digest: sha256:{sc['noise_digest']}`. This image contains the fix.",
        "branch": f"Operator: Push the fix on branch `{v}`, that is the branch CI is watching for this bug.",
        "bucket": f"Operator: The reconciliation exports are in `{v}`; we will need them to verify the fix.",
        "path": f"Ran `grep -rn 'flush_pending' services/{svc}` (exit 0): `{v}:212: self.flush_pending(batch)  # called twice on retry`. The duplicate-write bug is in `{v}`.",
    }[t]


def remind(t, v, sc, k):
    svc = sc["svc"]
    a = {
        "host": [f"Ran `pg_isready -h {v}` (exit 0): `{v}:5432 - accepting connections`.",
                 f"Operator: Reminder, the migration goes to `{v}`, nowhere else."],
        "port": [f"Ran `nc -zv localhost {v}` through the tunnel (exit 0): `Connection to localhost port {v} [tcp] succeeded!`.",
                 f"Noted that the staging pooler listens on {v}, per `deploy/pgbouncer/staging.ini`."],
        "package": [f"Ran `pip index versions {v.split('==')[0]}` (exit 0): the pinned `{v}` is available on the mirror.",
                    f"Operator: Again, `{v}` is the pin; do not float it."],
        "commit": [f"Ran `git show --stat {v}` (exit 0): 2 files changed, 31 insertions(+), 9 deletions(-).",
                   f"CI passed on commit `{v}` (pipeline #8812, 14 jobs green)."],
        "ticket": [f"Operator: Link the PR to {v} so the release notes pick it up.",
                   f"Added a comment draft for {v} describing the root cause (retry path calls flush twice)."],
        "invoice": [f"Ran `./bin/inspect-invoice {v}` (exit 0): `status=webhook_failed attempts=3 last_error=409 Conflict`.",
                    f"Operator: Customer support is asking about {v}; it is the one we must reprocess."],
        "envvar": [f"Ran `printenv | grep -c {v}` (exit 0): `1`. The variable is present in the staging shell.",
                   f"Operator: Remember the scripts must read `{v}`."],
        "threshold": [f"Operator: Reminder, the reconcile tolerance is {v}.",
                      f"Ran `python -m {svc}.reconcile --dry-run --tolerance {v}` (exit 0): `0 rows above tolerance in sample`."],
        "image": [f"Ran `docker pull {v}` on the staging runner (exit 0): `Status: Image is up to date for {v}`.",
                  f"Scanned `{v}` with trivy (exit 0): 0 critical, 2 low."],
        "branch": [f"Ran `git checkout -b {v}` (exit 0): `Switched to a new branch '{v}'`.",
                   f"Operator: Make sure everything lands on `{v}`."],
        "bucket": [f"Ran `aws s3 ls {v}/` (exit 0): `PRE 2026-09/` `PRE 2026-08/`.",
                   f"Operator: Use only `{v}` for the exports."],
        "path": [f"Opened `{v}` and read `flush_pending` (lines 190 to 240).",
                 f"Ran `pytest -q {v.replace('services/', 'tests/').replace('.py', '_test.py')}` (exit 1): `1 failed: duplicate write on retry`. Bug confirmed in `{v}`."],
    }[t]
    return a[k]


def distract(t, v, d, sc):
    """A turn naming the near duplicate in a different, non-target role."""
    return {
        "host": f"Operator: Do not touch `{d}`; it is being decommissioned and has stale data.",
        "port": f"Ran `grep listen_port deploy/pgbouncer/canary.ini` (exit 0): `listen_port = {d}`. That one is the canary pooler, not staging.",
        "package": f"Operator: Avoid `{d}`, it has a known regression in the retry path.",
        "commit": f"Ran `git log --oneline origin/main -1` (exit 0): `{d} docs: update runbook`. Unrelated to the fix.",
        "ticket": f"Operator: {d} is the unrelated flaky-test ticket; ignore it for this work.",
        "invoice": f"Operator: {d} also failed last week but was already reprocessed successfully, leave it alone.",
        "envvar": f"Operator: `{d}` still exists in some shells but holds the old, revoked secret.",
        "threshold": f"Operator: The old default tolerance was {d}; that is too loose now.",
        "image": f"Ran `kubectl get deploy {sc['svc']}-api -o jsonpath='{{..image}}'` (exit 0): `{d}`. That is the image currently running, without the fix.",
        "branch": f"Operator: `{d}` is the abandoned first attempt, do not push there.",
        "bucket": f"Operator: `{d}` is the old replica bucket; it is stale.",
        "path": f"Ran `ls services/{sc['svc']}` (exit 0): note `{d}` is dead code kept for reference; the live path is elsewhere.",
    }[t]


def supersede_old(t, old, sc):
    return intro(t, old, sc)


def supersede_new(t, old, new, sc):
    """A later correction turn that replaces old with new."""
    return {
        "host": f"Operator: Correction: staging failed over last night. Use `{new}` for the migration, not `{old}`.",
        "port": f"Ran `grep listen_port deploy/pgbouncer/staging.ini` again after the config reload (exit 0): `listen_port = {new}`. It changed from {old}; the staging pooler now listens on {new}.",
        "package": f"Operator: Correction on the pin: use `{new}` instead of `{old}`, the platform team re-certified it.",
        "commit": f"Ran `git rebase origin/main` (exit 0). After the rebase the fix is now commit `{new}`; the old `{old}` no longer exists on the branch.",
        "ticket": f"Operator: {old} was closed as a duplicate. Track the work on {new} instead.",
        "invoice": f"Operator: Sorry, I misread the dashboard. The failed invoice is {new}, not {old}.",
        "envvar": f"Operator: Correction: the secret moved to `{new}`. `{old}` holds the revoked key.",
        "threshold": f"Operator: Change of plan, use a drift tolerance of {new} instead of {old}.",
        "image": f"Rebuilt after the lockfile fix: ran `docker build -t {new} . && docker push {new}` (exit 0). `{old}` is stale; `{new}` is the image with the fix.",
        "branch": f"Operator: CI now watches `{new}`; push the fix there instead of `{old}`.",
        "bucket": f"Operator: The exports moved; they are now in `{new}`, not `{old}`.",
        "path": f"Ran `git mv {old} {new}` as part of the refactor (exit 0). The buggy code now lives in `{new}`.",
    }[t]


def fix_supersede_values(t, target, near):
    """For the superseded condition, target is the NEW value and near is the OLD one; for types
    where the generator made the near duplicate look older (host n-1, image c-1, envvar without _V2,
    path *_legacy), keep that ordering so corrections read naturally."""
    return target, near

# --------------------------------------------------------------------- matching

_PKG = re.compile(r"\b([a-z][a-z0-9_.-]*)\s*(?:==|@|\s+v?|\s+version\s+|:)\s*v?(\d+\.\d+(?:\.\d+)?)\b", re.I)
TYPE_RE = {
    "host": re.compile(r"\b[a-z0-9][a-z0-9-]*\.[a-z0-9-]+(?:\.[a-z0-9-]+)*\b"),
    "port": re.compile(r"(?<![\d.\-:/])\d{4,5}(?![\d.])"),
    "commit": re.compile(r"\b[0-9a-f]{7,40}\b"),
    "ticket": None,  # built per scenario (prefix specific)
    "invoice": re.compile(r"(?<![\w-])INV-?\s?\d{4,6}\b", re.I),
    "envvar": re.compile(r"\b[A-Z][A-Z0-9]*(?:_[A-Z0-9]+){2,}\b"),
    "threshold": re.compile(r"(?<![\d.])0?\.\d{2,6}(?![\d.])"),
    "image": re.compile(r"(?<![\w./-])(?:[a-z0-9.-]+/)*[a-z0-9_-]+-api(?::\d[\w.-]*)?"),
    "branch": re.compile(r"\b(?:fix|feature|hotfix|bugfix)/[A-Za-z0-9._/-]+[A-Za-z0-9]"),
    "bucket": re.compile(r"s3://[a-z0-9.-]+"),
    "path": re.compile(r"\b(?:[\w.-]+/)+[\w.-]+\.py\b"),
}
FILE_EXT = re.compile(r"\.(py|sql|ini|txt|json|ya?ml|toml|cfg|log|md|sh|io|lock)$")


def candidates(t, text, tprefix="", pkg=""):
    """All same-type tokens in text, normalized for comparison."""
    if t == "package":
        out = []
        for m in _PKG.finditer(text):
            name = m.group(1).lower()
            if name in PKG_ROLES or name == pkg or _lev(name, pkg) <= 2:
                out.append(f"{name}=={m.group(2)}")
        return out
    if t == "ticket":
        rx = re.compile(r"\b" + re.escape(tprefix) + r"-?\s?\d{3,6}\b", re.I)
        return [re.sub(r"[-\s]", "-", m.group(0).upper()).replace("--", "-") for m in rx.finditer(text)]
    rx = TYPE_RE[t]
    toks = [m.group(0) for m in rx.finditer(text)]
    if t == "host":
        toks = [x for x in toks if "stg" in x or "-int" in x or "db" in x]
        toks = [x for x in toks if not FILE_EXT.search(x) and not re.fullmatch(r"[\d.]+", x)]
    if t == "commit":
        toks = [x for x in toks if re.search(r"\d", x) and re.search(r"[a-f]", x)]
    if t == "invoice":
        toks = ["INV-" + re.sub(r"\D", "", x) for x in toks]
    if t == "threshold":
        toks = [("0" + x if x.startswith(".") else x) for x in toks]
    if t == "image":
        toks = [x.rstrip(".") for x in toks]
    return toks


def _lev(a, b):
    if a == b:
        return 0
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


lev = _lev


def exact_in(t, value, text):
    """Case-sensitive exact occurrence with token boundaries."""
    pat = r"(?<![\w.\-/])" + re.escape(value) + r"(?![\w\-]|\.\d)"
    return re.search(pat, text) is not None


def same(t, cand, target):
    """Normalized equality of a candidate token with the target (hash prefix >= 7 counts)."""
    c, g = cand.strip("`'\". ").lower(), target.lower()
    if t == "commit":
        return len(c) >= 7 and g.startswith(c)
    if t == "image":
        return c == g
    if t == "bucket":
        return c.rstrip("/") == g
    return c == g


def is_partial(t, cand, target):
    """A truncated but recognisable form (e.g. short hostname, image without tag)."""
    c, g = cand.lower(), target.lower()
    if t == "host":
        return g.startswith(c + ".") or c == g.split(".")[0]
    if t == "image":
        return c == g.split(":")[0] or (":" in c and g.endswith("/" + c))
    return False


def classify_text(t, text, target, near, sc):
    """Deterministic status of the target identifier in a text.
    Returns (status, cands) with status in exact | normalized | partial | candidate | absent.
    cands lists same-type tokens that differ from the target and may be a mutation of it."""
    if exact_in(t, target, text):
        return "exact", []
    cs = candidates(t, text, sc["tprefix"], sc["package"])
    if any(same(t, c, target) for c in cs):
        return "normalized", []
    if t == "port" and re.search(r"(?<!\d)" + target + r"(?!\d)", text):
        return "normalized", []
    if any(is_partial(t, c, target) for c in cs):
        return "partial", []
    if t in ("invoice", "ticket") and re.search(r"(?<![\w-])" + target.split("-")[1] + r"(?!\d)", text):
        return "partial", []  # right number without its prefix
    if t == "path" and re.search(r"(?<![\w/.-])" + re.escape(target.rsplit("/", 1)[1]) + r"\b", text):
        return "partial", []
    near_c = []
    for c in dict.fromkeys(cs):
        d = _lev(c.lower(), target.lower())
        if c.lower() == near.lower() or d <= max(2, int(0.5 * len(target))):
            near_c.append(c)
    return ("candidate" if near_c else "absent"), near_c


def mutation_kind(t, cand, target, near, cond):
    c, g, n = cand.lower(), target.lower(), near.lower()
    if cond in ("distractor", "superseded") and (c == n or (t == "commit" and len(c) >= 7 and n.startswith(c))):
        return "stale_value" if cond == "superseded" else "distractor_swap"
    if sorted(c) == sorted(g):
        return "char_transposition"
    if t == "package" and c.split("==")[0] == g.split("==")[0]:
        return "version_drift"
    if g.startswith(c) or c in g:
        return "truncation"
    if c.startswith(g) or g in c:
        return "extension"
    cp, gp = re.split(r"[-/_.:]", c), re.split(r"[-/_.:]", g)
    it = iter(gp)
    if len(cp) < len(gp) and all(x in it for x in cp):
        return "segment_dropped"
    if _lev(c, g) <= 2:
        return "small_edit"
    shared = len(set(cp) & set(gp)) / max(len(set(gp)), 1)
    if shared >= 0.5:
        return "blend_with_other_token"
    return "other_value"

# --------------------------------------------------------------------- harness registry

REG_PATTERNS = [
    re.compile(r"s3://[\w.-]+(?:/[\w./-]*)?"),
    re.compile(r"\b[a-z0-9.-]+\.io/[\w./-]+:[\w.-]+"),
    re.compile(r"\b[\w.-]+==[\w.]+"),
    re.compile(r"\b(?:fix|feature|hotfix|bugfix|release)/[\w./-]*\w"),
    re.compile(r"\b(?:[\w.-]+/)+[\w.-]+\.\w+\b"),
    re.compile(r"\b[A-Z][A-Z0-9]{1,9}-\d{2,}\b"),
    re.compile(r"\b[A-Z][A-Z0-9]*(?:_[A-Z0-9]+){1,}\b"),
    re.compile(r"\b[a-z0-9][a-z0-9-]*(?:\.[a-z0-9-]+){2,}\b"),
    re.compile(r"\b(?=[0-9a-f]*\d)(?=[0-9a-f]*[a-f])[0-9a-f]{7,40}\b"),
    re.compile(r"(?:port|listen_port|tolerance|threshold|timeout|limit|retries)\s*(?:=|:|of|is|to)?\s*\d+(?:\.\d+)?", re.I),
    re.compile(r"(?<![\w.])\d+\.\d{2,}(?!\w|\.\d)"),
    re.compile(r"\b(?:from|on|to|port)\s+\d{4,5}\b"),
]
CORRECTION_CUES = re.compile(r"\b(correction|instead of|instead|not `|, not |no longer|changed from|moved|stale|"
                             r"revoked|closed as a duplicate|misread|rebuilt|renamed|git mv|after the rebase)\b", re.I)


def extract_ids(text):
    found, spans = [], []
    for rx in REG_PATTERNS:
        for m in rx.finditer(text):
            s, e = m.span()
            if any(s >= a and e <= b for a, b in spans):
                continue
            tok = m.group(0).rstrip(".,;:")
            if len(tok) < 4:
                continue
            spans.append((s, e))
            found.append((s, tok))
    return [tok for _, tok in sorted(found)]


def _core(tok):
    return tok.split()[-1]


def _shape(tok):
    return "num" if re.fullmatch(r"[\d.]+", tok) else _ptype(tok)


def _ptype(tok):
    for i, rx in enumerate(REG_PATTERNS):
        if rx.fullmatch(tok):
            return i
    return -1


def build_registry(turns, recency=False):
    """Harness identifier registry over all turns seen so far (1-based turn numbers).
    recency=False: first-seen order, with turn numbers.
    recency=True: newest first, and a token is marked superseded when a later turn with a correction
    cue mentions a same-pattern near duplicate (edit distance <= 40% of length) after it."""
    seen = {}
    order = []
    for i, turn in enumerate(turns, 1):
        for tok in extract_ids(turn):
            if tok not in seen:
                seen[tok] = {"first": i, "last": i, "n": 0, "superseded_by": None}
                order.append(tok)
            seen[tok]["last"] = i
            seen[tok]["n"] += 1
    if recency:
        for i, turn in enumerate(turns, 1):
            if not CORRECTION_CUES.search(turn):
                continue
            toks = extract_ids(turn)
            # in a correction turn, values first seen in this turn are new; values seen before are old.
            # Compare on the value core (last word), so `tolerance of 0.05` and `0.05` match.
            cores_before = {_core(x) for x in seen if seen[x]["first"] < i}
            new_c = {_core(x) for x in toks if seen[x]["first"] == i and _core(x) not in cores_before}
            old_c = {_core(x) for x in toks if _core(x) in cores_before}
            for nc in new_c:
                for oc in old_c:
                    if _shape(nc) == _shape(oc) and _lev(nc, oc) <= max(2, 0.4 * len(nc)):
                        for x in seen:
                            if _core(x) == oc and seen[x]["first"] < i:
                                seen[x]["superseded_by"] = (nc, i)
            # explicit "X is stale/revoked/dead" style: mark tokens following cue words
            for m in re.finditer(r"`([^`]+)`\s+(?:is stale|holds the revoked|no longer exists|is dead)", turn):
                if m.group(1) in seen and not seen[m.group(1)]["superseded_by"]:
                    seen[m.group(1)]["superseded_by"] = ("(marked stale)", i)
        toks = sorted(order, key=lambda x: -seen[x]["last"])
        lines = []
        for x in toks:
            s = seen[x]
            note = f"last seen turn {s['last']}"
            if s["superseded_by"]:
                nt, ti = s["superseded_by"]
                note += f"; SUPERSEDED at turn {ti} by `{nt}`" if nt != "(marked stale)" else f"; marked stale at turn {ti}"
            lines.append(f"- `{x}` ({note})")
        head = "[Identifiers seen in this session, extracted verbatim by the harness, newest first. Superseded values are marked.]"
    else:
        lines = [f"- `{x}` (turns {', '.join(str(j) for j in _turns_of(x, turns))})" for x in order]
        head = "[Identifiers seen in this session, extracted verbatim by the harness from operator and tool turns]"
    return head + "\n" + "\n".join(lines)


def _turns_of(tok, turns):
    idx = [i for i, t in enumerate(turns, 1) if tok in extract_ids(t)]
    return idx if len(idx) <= 4 else idx[:2] + ["..."] + idx[-1:]
