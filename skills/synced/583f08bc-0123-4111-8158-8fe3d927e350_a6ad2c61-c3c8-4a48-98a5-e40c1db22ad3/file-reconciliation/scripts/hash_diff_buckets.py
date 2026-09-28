#!/usr/bin/env python3
"""Hash-diff a candidate directory tree against a canonical one and bucket every
candidate file as IDENTICAL / NEW / CONFLICT / NEAR-DUPE. Report-only by default —
never moves or deletes a file unless --apply is passed, per the "write/move needs
permission" rule for business file trees. Replaces the hand-rewritten Bash
(copy_and_archive/archive_only) that got reinvented 4+ times in one session.

Usage:
    python hash_diff_buckets.py <candidate_dir> <canonical_dir> [--apply] [--archive-dir DIR] [--report report.md]

Without --apply: prints/writes the bucket report only, moves nothing.
With --apply: for IDENTICAL and NEW-with-single-confident-destination buckets only,
    moves the candidate file into --archive-dir (default: <candidate_dir>/_archived)
    and writes a manifest line per file. CONFLICT and NEAR-DUPE are NEVER auto-applied —
    those always require a human decision (see file-reconciliation SKILL.md Mode A).
"""
import argparse
import hashlib
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def index_tree(root: Path):
    """Return (hash -> [paths]), (lowercased basename -> [paths]) for every file under root."""
    by_hash = {}
    by_name = {}
    for p in root.rglob("*"):
        if p.is_file():
            try:
                h = sha256_of(p)
            except OSError as e:
                print(f"WARN: could not hash {p}: {e}", file=sys.stderr)
                continue
            by_hash.setdefault(h, []).append(p)
            by_name.setdefault(p.name.lower(), []).append(p)
    return by_hash, by_name


def bucket_candidates(candidate_dir: Path, canonical_dir: Path):
    canon_by_hash, canon_by_name = index_tree(canonical_dir)
    buckets = {"IDENTICAL": [], "NEW": [], "CONFLICT": [], "NEAR-DUPE": []}

    for p in candidate_dir.rglob("*"):
        if not p.is_file():
            continue
        try:
            h = sha256_of(p)
        except OSError as e:
            print(f"WARN: could not hash {p}: {e}", file=sys.stderr)
            continue

        if h in canon_by_hash:
            buckets["IDENTICAL"].append((p, canon_by_hash[h]))
            continue

        name_matches = canon_by_name.get(p.name.lower(), [])
        if not name_matches:
            buckets["NEW"].append((p, []))
        elif len(name_matches) == 1:
            buckets["CONFLICT"].append((p, name_matches))
        else:
            buckets["NEAR-DUPE"].append((p, name_matches))

    return buckets


def write_report(buckets, out_path: Path, candidate_dir: Path, canonical_dir: Path):
    lines = [
        f"# Hash-diff report",
        f"Candidate: `{candidate_dir}`",
        f"Canonical: `{canonical_dir}`",
        "",
    ]
    for name in ("IDENTICAL", "NEW", "CONFLICT", "NEAR-DUPE"):
        items = buckets[name]
        lines.append(f"## {name} ({len(items)})")
        if name == "IDENTICAL":
            lines.append("Byte-identical to a canonical file already — safe to archive-only, never copy.")
        elif name == "NEW":
            lines.append("No same-named file anywhere in canonical — needs a destination decision, but no overwrite risk.")
        elif name == "CONFLICT":
            lines.append("Exactly one same-named canonical file exists, with DIFFERENT content. NEVER auto-resolve — "
                          "if these are document versions (leases, estoppels, etc.), see file-reconciliation SKILL.md "
                          "Mode B: extract and diff text, and prefer the executed/signed PDF over the newest-hash draft.")
        else:
            lines.append("Multiple same-named canonical files exist. Ambiguous — needs a human decision on which one, if any, this corresponds to.")
        for p, matches in items:
            match_str = "; ".join(str(m) for m in matches) if matches else "(none)"
            lines.append(f"- `{p}` -> {match_str}")
        lines.append("")
    out_path.write_text("\n".join(lines), encoding="utf-8")


def apply_safe_buckets(buckets, archive_dir: Path, candidate_dir: Path):
    archive_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = archive_dir / "manifest.tsv"
    now = datetime.now(timezone.utc).isoformat()
    applied = 0
    with manifest_path.open("a", encoding="utf-8") as manifest:
        for p, _matches in buckets["IDENTICAL"]:
            dest = archive_dir / p.relative_to(candidate_dir)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(p), str(dest))
            manifest.write(f"{now}\tIDENTICAL-archived\t{p}\t{dest}\n")
            applied += 1
    return applied


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("candidate_dir", type=Path)
    ap.add_argument("canonical_dir", type=Path)
    ap.add_argument("--apply", action="store_true", help="Archive IDENTICAL-bucket files only. CONFLICT/NEAR-DUPE never auto-applied.")
    ap.add_argument("--archive-dir", type=Path, default=None)
    ap.add_argument("--report", type=Path, default=Path("hash_diff_report.md"))
    args = ap.parse_args()

    if not args.candidate_dir.is_dir() or not args.canonical_dir.is_dir():
        print("Both candidate_dir and canonical_dir must exist.", file=sys.stderr)
        sys.exit(1)

    buckets = bucket_candidates(args.candidate_dir, args.canonical_dir)
    write_report(buckets, args.report, args.candidate_dir, args.canonical_dir)
    print(f"Report written to {args.report}")
    for name, items in buckets.items():
        print(f"  {name}: {len(items)}")

    if args.apply:
        archive_dir = args.archive_dir or (args.candidate_dir / "_archived")
        n = apply_safe_buckets(buckets, archive_dir, args.candidate_dir)
        print(f"Applied: archived {n} IDENTICAL file(s) to {archive_dir} (manifest.tsv appended). "
              f"CONFLICT/NEAR-DUPE/NEW require a human decision — see {args.report}.")


if __name__ == "__main__":
    main()
