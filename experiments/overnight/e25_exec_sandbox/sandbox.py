"""Fixed tool set for the E25 agent, confined to one sandbox directory per episode.

Safety design:
- The model never reaches a shell. Every subprocess is started with an argument list (shell=False) and a fixed
  command; the only model text that reaches a subprocess is a commit message, passed as one argv element to git.
- Paths from the model must be relative, contain no '..' component, resolve (os.path.realpath) inside the sandbox
  root, and may not touch .git. Writes refuse to follow a symlink.
- pytest and git run under macOS sandbox-exec with a profile that denies all network access and every file write
  outside the sandbox (and the grading directory), with a timeout and a minimal environment.
- git runs with hooks disabled (core.hooksPath=/dev/null), no remotes, and fixed author and dates.
"""
import os, re, subprocess, sys, xml.etree.ElementTree as ET
from pathlib import Path

SANDBOX_BASE = "/private/tmp/e25_sandboxes"
PY = sys.executable
GIT = next(g for g in ("/opt/homebrew/bin/git", "/Library/Developer/CommandLineTools/usr/bin/git", "/usr/bin/git")
           if os.path.exists(g))
MAX_READ = 12000
MAX_OUT = 4000

TOOLS = [
    {"type": "function", "function": {"name": "list_files", "description": "List files in the repository (recursively, excluding .git).",
     "parameters": {"type": "object", "properties": {"path": {"type": "string", "description": "Directory relative to the repository root. Default '.'"}}}}},
    {"type": "function", "function": {"name": "read_file", "description": "Read a text file from the repository.",
     "parameters": {"type": "object", "properties": {"path": {"type": "string", "description": "Path relative to the repository root."}}, "required": ["path"]}}},
    {"type": "function", "function": {"name": "write_file", "description": "Create or overwrite a text file in the repository with the given full content.",
     "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string", "description": "The complete new file content."}}, "required": ["path", "content"]}}},
    {"type": "function", "function": {"name": "run_tests", "description": "Run pytest on the repository, or on one test file if test_file is given.",
     "parameters": {"type": "object", "properties": {"test_file": {"type": "string", "description": "Optional test file path relative to the repository root, e.g. tests/test_x.py"}}}}},
    {"type": "function", "function": {"name": "git_status", "description": "Show `git status --short`.", "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {"name": "git_diff", "description": "Show the uncommitted changes (`git diff HEAD`).", "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {"name": "git_commit", "description": "Stage all changes and commit them with the given message.",
     "parameters": {"type": "object", "properties": {"message": {"type": "string"}}, "required": ["message"]}}},
    {"type": "function", "function": {"name": "finish", "description": "Signal that all requested work is done.",
     "parameters": {"type": "object", "properties": {"summary": {"type": "string"}}}}},
]


def _profile(*writable):
    allow = " ".join(f'(subpath "{os.path.realpath(w)}")' for w in writable)
    return ("(version 1)(allow default)(deny network*)(deny file-write*)"
            f'(allow file-write* {allow} (literal "/dev/null") (literal "/dev/tty") (subpath "/dev/fd"))')


def _env(home):
    return {"PATH": "/usr/bin:/bin:/opt/homebrew/bin", "HOME": str(home), "PYTHONDONTWRITEBYTECODE": "1",
            "LANG": "C.UTF-8", "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": "/dev/null",
            "GIT_AUTHOR_NAME": "agent", "GIT_AUTHOR_EMAIL": "agent@example.invalid",
            "GIT_COMMITTER_NAME": "agent", "GIT_COMMITTER_EMAIL": "agent@example.invalid"}


def _run(argv, cwd, writable, timeout=60, extra_env=None, split=False):
    env = _env(cwd)
    env["TMPDIR"] = str(cwd)
    env.update(extra_env or {})
    full = ["/usr/bin/sandbox-exec", "-p", _profile(*writable)] + argv
    try:
        p = subprocess.run(full, cwd=str(cwd), env=env, capture_output=True, text=True, timeout=timeout, shell=False)
        return (p.returncode, p.stdout, p.stderr) if split else (p.returncode, p.stdout + p.stderr)
    except subprocess.TimeoutExpired:
        return (-1, "", f"[timed out after {timeout}s]") if split else (-1, f"[timed out after {timeout}s]")


def _clean(out, root):
    out = out.replace(os.path.realpath(root) + "/", "").replace(str(root) + "/", "")
    out = re.sub(r" in \d+\.\d+s", "", out)
    return out


def run_pytest(root, test_file, timeout=60):
    argv = [PY, "-m", "pytest", "-q", "-p", "no:cacheprovider", "-o", "console_output_style=classic"]
    if test_file:
        argv.append(test_file)
    _, out = _run(argv, root, [root], timeout)
    out = _clean(out, root)
    return out if len(out) <= MAX_OUT else "[output truncated]\n" + out[-MAX_OUT:]


def grade_hidden(root, hidden_file, gdir):
    """Copy root/src into a fresh grading dir with the hidden tests and a pristine pytest.ini; return {test: passed}."""
    import shutil
    gdir = Path(gdir)
    if gdir.exists():
        shutil.rmtree(gdir)
    (gdir / "tests").mkdir(parents=True)
    if (Path(root) / "src").is_dir():
        shutil.copytree(Path(root) / "src", gdir / "src", symlinks=True)
    (gdir / "pytest.ini").write_text("[pytest]\npythonpath = src\ntestpaths = tests\n")
    shutil.copy(hidden_file, gdir / "tests" / "test_hidden.py")
    xml = gdir / "junit.xml"
    _, out = _run([PY, "-m", "pytest", "-q", "-p", "no:cacheprovider", f"--junitxml={xml}"], gdir, [gdir], 90)
    res = {}
    if xml.exists():
        for tc in ET.parse(xml).getroot().iter("testcase"):
            ok = not any(ch.tag in ("failure", "error", "skipped") for ch in tc)
            res[tc.get("name")] = ok
    if not res:  # collection error (e.g. import failure): every hidden test fails
        for line in Path(hidden_file).read_text().splitlines():
            m = re.match(r"def (test_\w+)\(", line)
            if m:
                res[m.group(1)] = False
    return res


class Sandbox:
    def __init__(self, root):
        self.root = Path(root)
        self.real = os.path.realpath(self.root)
        assert self.real.startswith(os.path.realpath(SANDBOX_BASE) + "/"), "sandbox must live under " + SANDBOX_BASE
        self.n_commits = 0

    # ---------------------------------------------------------------- setup
    def init_from(self, template):
        import shutil
        if self.root.exists():
            shutil.rmtree(self.root)
        shutil.copytree(template, self.root)
        self._git(["init", "-q", "-b", "main"])
        self._git(["add", "-A"])
        self._git(["commit", "-q", "-m", "initial import"], date=0)
        return self

    def _git(self, args, date=None, split=False):
        env = {}
        if date is not None:
            d = f"2026-01-01T00:{date // 60:02d}:{date % 60:02d}+0000"
            env = {"GIT_AUTHOR_DATE": d, "GIT_COMMITTER_DATE": d}
        argv = [GIT, "-c", "core.hooksPath=/dev/null", "-c", "commit.gpgsign=false",
                "-c", "core.fsmonitor=false", "-c", "safe.directory=*"] + args
        r = _run(argv, self.root, [self.root], 30, env, split=True)
        return (r[0], r[1]) if split else (r[0], r[1] + r[2])

    # ---------------------------------------------------------------- path checks
    def resolve(self, path, must_exist=False):
        """Return (relpath, abspath) or raise ValueError."""
        if not isinstance(path, str) or not path.strip() or "\x00" in path:
            raise ValueError("invalid path")
        path = path.strip()
        if path.startswith("./"):
            path = path[2:]
        if os.path.isabs(path) or path.startswith("~"):
            raise ValueError("absolute paths are not allowed; use a path relative to the repository root")
        parts = Path(path).parts
        if ".." in parts:
            raise ValueError("'..' is not allowed in paths")
        if parts and parts[0] == ".git":
            raise ValueError("the .git directory is not accessible")
        full = os.path.realpath(os.path.join(self.real, path))
        if full != self.real and not full.startswith(self.real + "/"):
            raise ValueError("path escapes the repository")
        rel = os.path.relpath(full, self.real)
        if rel.split("/")[0] == ".git":
            raise ValueError("the .git directory is not accessible")
        if must_exist and not os.path.exists(full):
            raise ValueError(f"{rel} does not exist")
        return rel, full

    # ---------------------------------------------------------------- tools
    def list_files(self, path="."):
        rel, full = self.resolve(path or ".", must_exist=True)
        out = []
        for dp, dns, fns in os.walk(full):
            dns[:] = sorted(d for d in dns if d not in (".git", "__pycache__", ".pytest_cache"))
            for f in sorted(fns):
                out.append(os.path.relpath(os.path.join(dp, f), self.real))
        return "\n".join(out[:300]) or "(empty)"

    def read_file(self, path):
        rel, full = self.resolve(path, must_exist=True)
        if os.path.isdir(full):
            raise ValueError(f"{rel} is a directory")
        text = Path(full).read_text(errors="replace")
        return text if len(text) <= MAX_READ else text[:MAX_READ] + "\n[truncated]"

    def write_file(self, path, content):
        rel, full = self.resolve(path)
        if not isinstance(content, str):
            raise ValueError("content must be a string")
        if len(content) > 100000:
            raise ValueError("content too large")
        if os.path.islink(os.path.join(self.real, rel)) or os.path.isdir(full):
            raise ValueError("cannot write to a symlink or directory")
        Path(full).parent.mkdir(parents=True, exist_ok=True)
        # re-check the parent after mkdir (a symlinked parent would have been caught by realpath already)
        if not os.path.realpath(Path(full).parent).startswith(self.real):
            raise ValueError("path escapes the repository")
        Path(full).write_text(content)
        return f"wrote {len(content)} characters to {rel}"

    def run_tests(self, test_file=None):
        tf = None
        if test_file:
            rel, full = self.resolve(test_file, must_exist=True)
            if not (rel.endswith(".py") and os.path.isfile(full)):
                raise ValueError("test_file must be an existing .py file")
            tf = rel
        return run_pytest(self.root, tf)

    def git_status(self):
        _, out = self._git(["status", "--short"])
        return out.strip() or "(clean)"

    def git_diff(self):
        _, out = self._git(["diff", "HEAD"])
        out = out.strip() or "(no changes)"
        return out if len(out) <= 6000 else out[:6000] + "\n[truncated]"

    def git_commit(self, message):
        if not isinstance(message, str) or not message.strip() or len(message) > 1000 or "\x00" in message:
            raise ValueError("invalid commit message")
        self._git(["add", "-A"])
        _, st = self._git(["status", "--porcelain"], split=True)
        if not st.strip():
            return "nothing to commit (working tree clean)"
        self.n_commits += 1
        code, out = self._git(["commit", "-q", "-m", message], date=self.n_commits)
        if code != 0:
            return "commit failed: " + out[-500:]
        _, h = self._git(["rev-parse", "--short", "HEAD"], split=True)
        _, files = self._git(["show", "--name-only", "--format=", "HEAD"], split=True)
        return f"[{h.strip()}] {message.splitlines()[0]}\nfiles: {', '.join(files.split())}"

    # ---------------------------------------------------------------- harness-side inspection (not tools)
    def commits(self):
        """List of dict(hash, message, files) for commits after the initial import, oldest first."""
        _, out = self._git(["log", "--reverse", "--format=%x1e%h%x1f%B%x1f", "--name-only"], split=True)
        res = []
        for rec in out.split("\x1e")[1:]:
            h, msg, files = rec.split("\x1f")
            res.append(dict(hash=h, message=msg.strip(), files=files.split()))
        return res[1:]

    def added_lines(self, path, commit=None):
        """Lines added to path by one commit (or by uncommitted changes vs HEAD when commit is None)."""
        args = ["show", "--format=", commit, "--", path] if commit else ["diff", "HEAD", "--", path]
        _, out = self._git(args, split=True)
        return sum(1 for x in out.splitlines() if x.startswith("+") and not x.startswith("+++") and x[1:].strip())

    def changed_since_initial(self):
        """Paths that differ between the initial commit and the working tree (including untracked)."""
        _, first = self._git(["rev-list", "--max-parents=0", "HEAD"], split=True)
        _, out = self._git(["diff", "--name-only", first.strip()], split=True)
        _, un = self._git(["ls-files", "--others", "--exclude-standard"], split=True)
        return sorted(set(out.split()) | set(un.split()))
