"""Propagate an edited scheduled-task SKILL.md onto its LIVE fleet path, safely.

register-scheduled-task v2.29 "Editing a task's SKILL.md CONTENT", steps 4-6, in one tool:
  4. back up the live file beside itself (SKILL.md.bak-<tag>; never overwrites an existing backup)
  5. write the edited content in the LIVE file's own EOL style (live files are a CRLF/LF mix, and
     core.autocrlf=true checks worktrees out as CRLF, so a naive copy flips every line)
  6. verify: raw sha256 of live == the EOL-matched source; for CC files also `git hash-object` of
     live == of the committed source (git stores LF, so raw sha vs `git show` reports false drift)

Refuses (writes nothing) when the live file mixes EOL styles, or when the diff replaces more
existing lines than --max-replaced (the number of planned edits) -- the signal that live drifted
under you or the source carries changes you did not plan.

Dry run by default; --apply writes.
  python maintenance/propagate-task-spec.py --tag 2026-09-23-why --max-replaced 2 \
      --pair <edited SKILL.md> <live SKILL.md> [--pair ...] [--git-repo <worktree>] [--apply]
"""
import argparse
import difflib
import hashlib
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


def hash_object(repo: Path, path: Path) -> str:
    return subprocess.run(["git", "-C", str(repo), "hash-object", "--path", "scheduled-tasks/x/SKILL.md", str(path)],
                          capture_output=True, text=True).stdout.strip()


def propagate(src: Path, live: Path, max_replaced: int, tag: str, apply: bool, git_repo: Path | None = None) -> Result:
    live_b = live.read_bytes()
    style = eol_style(live_b)
    if style == "mixed" or eol_style(src.read_bytes()) == "mixed":
        return Result(False, f"mixed EOL (live={style}, src={eol_style(src.read_bytes())})")
    new_b = to_style(src.read_bytes(), style)
    if new_b == live_b:
        return Result(True, "unchanged")
    ops = difflib.SequenceMatcher(None, live_b.splitlines(), new_b.splitlines(), autojunk=False).get_opcodes()
    replaced = sum(i2 - i1 for t, i1, i2, _, _ in ops if t in ("replace", "delete"))
    added = sum(j2 - j1 for t, _, _, j1, j2 in ops if t in ("replace", "insert"))
    if replaced > max_replaced:
        return Result(False, f"replaces {replaced} live line(s), planned at most {max_replaced}", replaced, added)
    if not apply:
        return Result(True, f"dry-run eol={style}", replaced, added)
    bak = live.with_name(f"{live.name}.bak-{tag}")
    if not bak.exists():
        shutil.copy2(live, bak)
        if sha(bak.read_bytes()) != sha(live_b):
            return Result(False, "backup did not match live", replaced, added)
    live.write_bytes(new_b)
    now = live.read_bytes()
    if sha(now) != sha(new_b) or eol_style(now) != style:
        return Result(False, "post-write sha/EOL mismatch", replaced, added)
    if git_repo and hash_object(git_repo, live) != hash_object(git_repo, src):
        return Result(False, "git hash-object mismatch vs committed source", replaced, added)
    return Result(True, f"applied eol={style} live_sha={sha(now)[:12]}", replaced, added)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--pair", nargs=2, action="append", metavar=("EDITED", "LIVE"), required=True)
    ap.add_argument("--tag", required=True, help="backup suffix, e.g. 2026-09-23-insights5")
    ap.add_argument("--max-replaced", type=int, required=True, help="planned edits per file")
    ap.add_argument("--git-repo", type=Path, help="worktree holding the committed source (CC files)")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    bad = 0
    for src, live in a.pair:
        r = propagate(Path(src), Path(live), a.max_replaced, a.tag, a.apply, a.git_repo)
        bad += not r.ok
        print(f"{'OK ' if r.ok else 'REFUSE'} {Path(live).parent.name}: {r.reason} (-{r.replaced} +{r.added})")
    print(f"{len(a.pair)} file(s), {bad} refused, mode={'APPLY' if a.apply else 'DRY'}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
