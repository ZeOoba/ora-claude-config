"""Repo-hygiene invariant: every sidecar append-event-log.py writes next to
event_log.md must be git-ignored, and none may be tracked.

Run: python test-memory-sidecar-hygiene.py
Stdlib only. ASCII-only. Self-contained.

WHY (2026-09-12): PR #172 (063fa61) added a permanent `event_log.md.lock`
sidecar for its msvcrt byte-range lock, and renamed the atomic-insert scratch
file from a fixed `event_log.md.tmp-append` to a unique
`event_log.md.tmp-append.<pid>.<ns>`. Neither change touched .gitignore. The
three earlier sidecars (.inplace-backup, .tmp-append, .pending/) each got an
exact-name ignore line when they were introduced, so the lock was simply not
ignored, and the exact `.tmp-append` line stopped matching the new unique
names. memory-commit-sweep.py then committed the lock (9ce0923) -- it sweeps
whatever `git status` reports, and that is correct: the gap was the ignore rule.

The sidecar suffixes are DERIVED FROM THE SCRIPT'S SOURCE, not hand-listed, so a
future sidecar added without an ignore line fails here instead of reaching a
commit. An extraction floor guards against the extractor silently finding
nothing (a zero here would mean "couldn't look", not "all clean").
"""

import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCRIPT = os.path.join(REPO, "maintenance", "append-event-log.py")
MEM_REL = "projects/C--Users-Owner-OneDrive---Oxford-Capital-Partners/memory"
LOG_REL = MEM_REL + "/event_log.md"

# Sidecars known to exist as of 2026-09-12. The extractor must find at least
# these; it may find more (that is the point), never fewer.
KNOWN_FLOOR = {".lock", ".pending", ".inplace-backup", ".tmp-append"}

for _v in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR",
           "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_PREFIX"):
    os.environ.pop(_v, None)


def git(*args):
    proc = subprocess.run(["git"] + list(args), cwd=REPO,
                          capture_output=True, text=True)
    return proc.returncode, proc.stdout.strip()


def sidecar_names():
    """append-event-log.py source -> concrete example sidecar suffixes.

    Scans every line that mentions `log`/`LOG` (any case, whole word) for the
    ways a sibling-of-the-log name gets built:
      log + ".lock"   /   LOG + ".x"     (concatenated dot-literal)
      "%s.tmp-append.%d.%d" % (log, ..)  (printf, tuple or bare)
      "{}.x".format(log)                 (str.format)
      f"{log}.x"                         (f-string)
    Docstring/comment mentions of the same forms are matched too; that only
    re-finds a real sidecar, never a false one. Placeholders are filled with
    digits so the example name is exactly what the script would put on disk.

    Known limit: a sidecar built from a directory join, e.g.
    os.path.join(os.path.dirname(log), "x"), is not a `event_log.md.*` sibling
    and is out of scope; the extraction floor catches a rename that drops a
    known one.
    """
    with open(SCRIPT, encoding="utf-8") as f:
        src = f.read()
    suffixes = set()
    for line in src.splitlines():
        if not re.search(r"\blog\b", line, re.I):
            continue
        suffixes.update(re.findall(r"\+\s*[\"'](\.[A-Za-z][^\"'\s]*)[\"']", line))
        suffixes.update(re.findall(r"[\"'](\.[A-Za-z][^\"'\s]*)[\"']\s*\+", line))
        for fmt in re.findall(r"[\"'](?:%s|\{\}|\{log\})(\.[A-Za-z][^\"'\s]*)[\"']",
                              line, re.I):
            suffixes.add(fmt)
    return {re.sub(r"%d|\{[^}]*\}", "12345", s) for s in suffixes}


def _base_suffix(s):
    return re.sub(r"(\.\d+)+$", "", s)


def test_extractor_finds_known_sidecars():
    found = {_base_suffix(s) for s in sidecar_names()}
    missing = KNOWN_FLOOR - found
    assert not missing, (
        "extractor lost track of known sidecars %s -- append-event-log.py changed "
        "how it names them; update sidecar_names() before trusting the other tests"
        % sorted(missing))


def test_every_sidecar_is_ignored():
    unignored = []
    for suffix in sorted(sidecar_names()):
        path = LOG_REL + suffix
        # .pending is a spool DIRECTORY ignored by a dir-only rule (`.pending/`);
        # check-ignore --no-index cannot know a nonexistent bare name is a
        # directory, so probe a spooled file inside it -- what would get committed.
        probes = [path + "/20260912T000000-entry.md"] if suffix == ".pending" else [path]
        for p in probes:
            rc, _ = git("check-ignore", "-q", "--no-index", p)
            assert rc != 128, "git check-ignore errored on %s" % p
            if rc != 0:
                unignored.append(p)
    assert not unignored, (
        "append-event-log.py sidecar(s) NOT git-ignored -- one `git add` or one "
        "memory-commit-sweep.py cycle from being committed:\n  %s\n"
        "Add an ignore line under the other event_log.md.* entries in .gitignore."
        % "\n  ".join(unignored))


def test_no_sidecar_is_tracked():
    rc, out = git("ls-files", "--", MEM_REL)
    assert rc == 0, "git ls-files failed"
    tracked = [l for l in out.splitlines()
               if os.path.basename(l).startswith("event_log.md.")]
    assert not tracked, (
        "event_log.md sidecar(s) tracked in the index (.gitignore does not untrack "
        "an already-tracked file; run `git rm --cached`):\n  %s" % "\n  ".join(tracked))


def test_memory_files_are_not_ignored():
    """Control: the sidecar checks only mean something if ordinary memory files are
    NOT ignored. Otherwise a parent rule hiding all of memory/ (with a lone
    !event_log.md re-include) would make every sidecar read as 'ignored' for the
    wrong reason. check-ignore exits 1 for not-ignored; 128 is a git error and
    must not read as a pass."""
    for p in (LOG_REL, MEM_REL + "/MEMORY.md", MEM_REL + "/zz_probe_new_note_2026.md"):
        rc, _ = git("check-ignore", "-q", "--no-index", p)
        assert rc != 128, "git check-ignore errored on %s" % p
        assert rc == 1, "%s is git-ignored -- a rule is too broad" % p


def main():
    tests = [v for k, v in sorted(globals().items())
             if k.startswith("test_") and callable(v)]
    failed = 0
    for t in tests:
        try:
            t()
            print("PASS %s" % t.__name__)
        except AssertionError as e:
            failed += 1
            print("FAIL %s: %s" % (t.__name__, e))
    print("%d/%d passed" % (len(tests) - failed, len(tests)))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
