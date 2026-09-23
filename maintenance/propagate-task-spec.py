"""Propagate an edited scheduled-task SKILL.md onto its LIVE fleet path, safely.

register-scheduled-task v2.29 "Editing a task's SKILL.md CONTENT", steps 4-6, in one tool:
  4. back up the live file beside itself (SKILL.md.bak-<tag>). An existing backup is never
     overwritten, and is refused if it no longer matches live (stale tag -> choose a new tag).
  5. write the edited content in the LIVE file's own EOL style (live files are a CRLF/LF mix, and
     core.autocrlf=true checks worktrees out as CRLF, so a naive copy flips every line). The write
     goes to a temp file, is verified, then atomically replaces live; any later failure restores
     the backup.
  6. verify: raw sha256 of live == the EOL-matched source; with --git-repo also
     `git hash-object --path <repo path> <live>` == the COMMITTED blob `git rev-parse <rev>:<repo path>`
     (git stores LF, so raw sha vs `git show` reports false drift). A failing git call is a refusal.

Refuses (writes nothing) on mixed EOL, an empty or missing live file, or a diff that replaces more
live lines than --max-replaced or adds more than --max-added (the planned edit size) -- the signal
that live drifted under you or the source carries changes you did not plan.

Dry run by default; --apply writes. Exit 1 if any pair was refused.
  python maintenance/propagate-task-spec.py --tag 2026-09-23-why --max-replaced 2 --max-added 3 \
      --pair <edited SKILL.md> <live SKILL.md> [--pair ...] [--git-repo <worktree> [--rev HEAD]] [--apply]
"""
import argparse
import difflib
import hashlib
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Result:
    ok: bool
    reason: str
    replaced: int = 0
    added: int = 0


class GitError(RuntimeError):
    pass


def eol_style(b: bytes) -> str:
    crlf = b.count(b"\r\n")
    lf = b.count(b"\n") - crlf
    if crlf and lf:
        return "mixed"
    return "crlf" if crlf else "lf"


def to_style(b: bytes, style: str) -> bytes:
    b = b.replace(b"\r\n", b"\n")
    return b.replace(b"\n", b"\r\n") if style == "crlf" else b


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _git(repo: Path, *args: str) -> str:
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    out = r.stdout.strip()
    if r.returncode != 0 or not re.fullmatch(r"[0-9a-f]{40}", out):
        raise GitError(f"git {' '.join(args[:2])} failed: {r.stderr.strip() or out or 'no output'}")
    return out


def committed_blob(repo: Path, rev: str, src: Path) -> tuple[str, str]:
    rel = src.resolve().relative_to(Path(repo).resolve()).as_posix()
    return rel, _git(repo, "rev-parse", f"{rev}:{rel}")


def propagate(src: Path, live: Path, max_replaced: int, tag: str, apply: bool,
              git_repo: Path | None = None, rev: str = "HEAD", max_added: int | None = None) -> Result:
    try:
        live_b = live.read_bytes()
        src_b = src.read_bytes()
    except OSError as e:
        return Result(False, f"unreadable: {e}")
    if not live_b.strip():
        return Result(False, "live file is empty")
    style = eol_style(live_b)
    if style == "mixed" or eol_style(src_b) == "mixed":
        return Result(False, f"mixed EOL (live={style}, src={eol_style(src_b)})")
    new_b = to_style(src_b, style)
    blob = rel = None
    if git_repo:
        try:
            rel, blob = committed_blob(git_repo, rev, src)
            if _git(git_repo, "hash-object", "--path", rel, str(src)) != blob:
                return Result(False, f"source differs from committed {rev}:{rel} (commit it first)")
        except (GitError, ValueError) as e:
            return Result(False, str(e))
    if new_b == live_b:
        return Result(True, "unchanged")
    ops = difflib.SequenceMatcher(None, live_b.splitlines(), new_b.splitlines(), autojunk=False).get_opcodes()
    replaced = sum(i2 - i1 for t, i1, i2, _, _ in ops if t in ("replace", "delete"))
    added = sum(j2 - j1 for t, _, _, j1, j2 in ops if t in ("replace", "insert"))
    cap_added = max_replaced if max_added is None else max_added
    if replaced > max_replaced or added > cap_added:
        return Result(False, f"replaces {replaced}/adds {added} line(s), planned at most {max_replaced}/{cap_added}",
                      replaced, added)
    if not apply:
        return Result(True, f"dry-run eol={style}", replaced, added)
    bak = live.with_name(f"{live.name}.bak-{tag}")
    if bak.exists():
        if sha(bak.read_bytes()) != sha(live_b):
            return Result(False, f"stale backup {bak.name} does not match live; choose a new --tag", replaced, added)
    else:
        shutil.copy2(live, bak)
        if sha(bak.read_bytes()) != sha(live_b):
            return Result(False, "backup did not match live", replaced, added)
    tmp = live.with_name(f"{live.name}.propagate-tmp")
    try:
        tmp.write_bytes(new_b)
        if sha(tmp.read_bytes()) != sha(new_b):
            raise OSError("temp write verification failed")
        os.replace(tmp, live)
        now = live.read_bytes()
        if sha(now) != sha(new_b) or eol_style(now) != style:
            raise OSError("post-write sha/EOL mismatch")
        if git_repo and _git(git_repo, "hash-object", "--path", rel, str(live)) != blob:
            raise OSError(f"live does not hash to committed blob {blob[:12]}")
    except (OSError, GitError) as e:
        shutil.copy2(bak, live)
        restored = sha(live.read_bytes()) == sha(live_b)
        return Result(False, f"{e}; live {'restored from backup' if restored else 'RESTORE FAILED -- check ' + bak.name}",
                      replaced, added)
    finally:
        if tmp.exists():
            tmp.unlink()
    return Result(True, f"applied eol={style} live_sha={sha(now)[:12]}" + (f" blob={blob[:12]}" if blob else ""),
                  replaced, added)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--pair", nargs=2, action="append", metavar=("EDITED", "LIVE"), required=True)
    ap.add_argument("--tag", required=True, help="backup suffix, e.g. 2026-09-23-insights5")
    ap.add_argument("--max-replaced", type=int, required=True, help="live lines each pair may replace")
    ap.add_argument("--max-added", type=int, help="lines each pair may add (default: --max-replaced)")
    ap.add_argument("--git-repo", type=Path, help="worktree holding the committed source (CC files)")
    ap.add_argument("--rev", default="HEAD", help="commit the source must match (default HEAD)")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    bad = 0
    for src, live in a.pair:
        r = propagate(Path(src), Path(live), a.max_replaced, a.tag, a.apply, a.git_repo, a.rev, a.max_added)
        bad += not r.ok
        print(f"{'OK    ' if r.ok else 'REFUSE'} {live}: {r.reason} (-{r.replaced} +{r.added})")
    print(f"{len(a.pair)} file(s), {bad} refused, mode={'APPLY' if a.apply else 'DRY'}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
