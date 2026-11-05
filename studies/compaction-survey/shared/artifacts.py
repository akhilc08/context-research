"""Pack or restore each study's raw artifacts as one archive per study.

Each study keeps its scripts and Markdown at its top level. Everything in its
subdirectories (inputs, raw outputs, caches) lives in `<study>/artifacts.tar.gz`,
except Markdown files and files that Markdown in the thread links to. Extract the
archives before rerunning a study's scripts.

    python3 shared/artifacts.py restore            # every study
    python3 shared/artifacts.py restore e17_operator_ledger
    python3 shared/artifacts.py pack e17_operator_ledger

Archives are deterministic: sorted members, zeroed timestamps and owners, so packing
the same files twice gives identical bytes. Packing deletes a file only after reading
it back from the finished archive and matching its SHA-256.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import os
import re
import sys
import tarfile
from pathlib import Path

THREAD = Path(__file__).resolve().parents[1]
ARCHIVE = "artifacts.tar.gz"
STUDY = re.compile(r"^[ex]\d{2}_")
LINK = re.compile(r"\]\(([^)\s#]+)")


def studies(names: list[str]) -> list[Path]:
    found = sorted(p for p in THREAD.iterdir() if p.is_dir() and STUDY.match(p.name))
    if not names:
        return found
    chosen = [THREAD / n for n in names]
    missing = [p.name for p in chosen if p not in found]
    if missing:
        raise SystemExit(f"Unknown studies: {missing}")
    return chosen


def linked_files() -> set[Path]:
    """Non-Markdown files that some Markdown file in the thread links to."""
    targets = set()
    for md in THREAD.rglob("*.md"):
        for target in LINK.findall(md.read_text(errors="replace")):
            if "://" not in target and not target.startswith(("/", "mailto:")):
                targets.add((md.parent / target).resolve())
    return targets


def members(study: Path, keep: set[Path]) -> list[Path]:
    out = []
    for path in sorted(study.rglob("*")):
        if not path.is_file() or path.parent == study or "__pycache__" in path.parts:
            continue
        if path.suffix == ".md" or path.resolve() in keep or path.name == ARCHIVE:
            continue
        out.append(path)
    return out


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def pack(study: Path, keep: set[Path]) -> str:
    files = members(study, keep)
    if not files:
        return f"{study.name}: nothing to pack"
    target = study / ARCHIVE
    if target.exists():
        raise SystemExit(f"{target} exists. Restore it first, then pack again.")
    expected = {}
    buffer = io.BytesIO()
    with gzip.GzipFile(fileobj=buffer, mode="wb", mtime=0, compresslevel=9) as gz:
        with tarfile.open(fileobj=gz, mode="w", format=tarfile.PAX_FORMAT) as tar:
            for path in files:
                data = path.read_bytes()
                name = path.relative_to(study).as_posix()
                expected[name] = sha256(data)
                info = tarfile.TarInfo(name)
                info.size, info.mtime, info.mode = len(data), 0, 0o644
                info.uid = info.gid = 0
                info.uname = info.gname = ""
                tar.addfile(info, io.BytesIO(data))
    target.write_bytes(buffer.getvalue())
    with tarfile.open(target, "r:gz") as tar:
        seen = {m.name: sha256(tar.extractfile(m).read()) for m in tar.getmembers()}
    if seen != expected:
        target.unlink()
        raise SystemExit(f"{study.name}: archive did not read back identically. Nothing deleted.")
    for path in files:
        path.unlink()
    for directory in sorted((p for p in study.rglob("*") if p.is_dir()), key=lambda p: len(p.parts), reverse=True):
        if not any(directory.iterdir()):
            directory.rmdir()
    return f"{study.name}: packed {len(files)} files into {target.stat().st_size / 1e6:.1f} MB"


def restore(study: Path) -> str:
    source = study / ARCHIVE
    if not source.exists():
        return f"{study.name}: no archive"
    written = skipped = 0
    with tarfile.open(source, "r:gz") as tar:
        for member in tar.getmembers():
            data = tar.extractfile(member).read()
            dest = (study / member.name).resolve()
            if not dest.is_relative_to(study.resolve()):
                raise SystemExit(f"{study.name}: unsafe path in archive: {member.name}")
            if dest.exists():
                if sha256(dest.read_bytes()) != sha256(data):
                    raise SystemExit(f"{study.name}: {member.name} differs from the archive. Not overwriting.")
                skipped += 1
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
            written += 1
    return f"{study.name}: restored {written} files ({skipped} already present)"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=("pack", "restore"))
    parser.add_argument("studies", nargs="*", help="Study directory names. Defaults to every study.")
    args = parser.parse_args()
    keep = linked_files() if args.command == "pack" else set()
    for study in studies(args.studies):
        print(pack(study, keep) if args.command == "pack" else restore(study), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
