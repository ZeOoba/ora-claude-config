#!/usr/bin/env python3
"""Tests for task-folder-registration-probe.py.

Covers the pure(-ish) reconciliation functions: list_skill_folders(),
is_one_time(), read_registry_entries(), find_unregistered(), and
find_orphaned_registrations(). Filesystem-touching functions use a real
tempdir (list_skill_folders, read_registry_entries) or an injected
exists_fn (find_orphaned_registrations) so nothing here touches the live
~/.claude or OneDrive scheduled-task trees.

Run: python test-task-folder-registration-probe.py   (exit 0 = all pass)
"""
import importlib.util
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(
    "tfrp", os.path.join(HERE, "task-folder-registration-probe.py"))
tfrp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tfrp)

sys.path.insert(0, os.path.join(HERE, "_shared"))
import store_discovery as sd

results = []


def expect(label, cond, detail=""):
    results.append((bool(cond), label))
    if not cond:
        print("  FAIL: %s %s" % (label, detail))


# --- list_skill_folders --------------------------------------------------------------
with tempfile.TemporaryDirectory() as root:
    os.makedirs(os.path.join(root, "ora-alpha"))
    with open(os.path.join(root, "ora-alpha", "SKILL.md"), "w", encoding="utf-8") as f:
        f.write("alpha content")
    os.makedirs(os.path.join(root, "ora-beta"))
    with open(os.path.join(root, "ora-beta", "SKILL.md"), "w", encoding="utf-8") as f:
        f.write("beta content")
    os.makedirs(os.path.join(root, "_archive_2026-01-01"))  # no SKILL.md directly inside
    os.makedirs(os.path.join(root, "not-a-task-dir"))  # no SKILL.md at all

    found = tfrp.list_skill_folders(root)
    expect("list_skill_folders: finds both real task dirs",
           set(found.keys()) == {"ora-alpha", "ora-beta"}, repr(found))
    expect("list_skill_folders: path points at the SKILL.md file",
           found["ora-alpha"].endswith("SKILL.md") and os.path.isfile(found["ora-alpha"]))

expect("list_skill_folders: empty-but-existing root -> {}",
       tfrp.list_skill_folders(tempfile.mkdtemp()) == {})
expect("list_skill_folders: missing root -> None",
       tfrp.list_skill_folders(os.path.join(tempfile.gettempdir(), "definitely-does-not-exist-xyz")) is None)

# --- is_one_time -----------------------------------------------------------------------
expect("is_one_time: explicit ONE-TIME marker",
       tfrp.is_one_time("---\nname: x\n---\nONE-TIME DIAGNOSTIC TASK -- fires once, then auto-disables."))
expect("is_one_time: lowercase one-off marker",
       tfrp.is_one_time("this is a one-off canary run, not a recurring automation"))
expect("is_one_time: normal recurring text -> False",
       not tfrp.is_one_time("This task fires quarterly (1st of Jan/Apr/Jul/Oct at 8 AM)."))
expect("is_one_time: empty text -> False", not tfrp.is_one_time(""))

# --- read_registry_entries ---------------------------------------------------------------
reg = {"scheduledTasks": [
    {"id": "ora-a", "cronExpression": "0 1 * * *", "enabled": True, "filePath": "/some/a/SKILL.md"},
    {"id": "ora-b", "cronExpression": None, "enabled": True, "filePath": "/some/b/SKILL.md"},
]}
with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as tf:
    json.dump(reg, tf)
    reg_path = tf.name
try:
    entries = tfrp.read_registry_entries(reg_path)
    expect("read_registry_entries: reads both entries verbatim",
           {e["id"] for e in entries} == {"ora-a", "ora-b"}, repr(entries))
    expect("read_registry_entries: preserves filePath/enabled",
           next(e for e in entries if e["id"] == "ora-a")["filePath"] == "/some/a/SKILL.md")
finally:
    os.unlink(reg_path)
expect("read_registry_entries: missing file -> None",
       tfrp.read_registry_entries(os.path.join(tempfile.gettempdir(), "no-such-registry.json")) is None)

_bad_path = tempfile.mktemp(suffix=".json")
with open(_bad_path, "w", encoding="utf-8") as f:
    f.write("{not json")
try:
    expect("read_registry_entries: malformed json -> None",
           tfrp.read_registry_entries(_bad_path) is None)
finally:
    os.unlink(_bad_path)

# --- find_unregistered -------------------------------------------------------------------
folder_texts = {
    "ora-registered": "This task fires quarterly.",
    "ora-gap": "This task fires quarterly and needs registration.",
    "ora-canary": "ONE-TIME canary, auto-disabled after firing.",
}
unreg = tfrp.find_unregistered(folder_texts, registered_ids={"ora-registered"})
expect("find_unregistered: flags the true gap only",
       unreg == ["ora-gap"], repr(unreg))

expect("find_unregistered: registered id never flagged even if content looks one-time-ish",
       tfrp.find_unregistered({"ora-x": "quarterly task"}, {"ora-x"}) == [])
expect("find_unregistered: empty folders -> []",
       tfrp.find_unregistered({}, {"anything"}) == [])

# --- find_orphaned_registrations ----------------------------------------------------------
entries = [
    {"id": "ora-live", "enabled": True, "filePath": "/exists/SKILL.md"},
    {"id": "ora-dangling", "enabled": True, "filePath": "/missing/SKILL.md"},
    {"id": "ora-paused-missing", "enabled": False, "filePath": "/missing2/SKILL.md"},
]
exists = {"/exists/SKILL.md"}
orphans = tfrp.find_orphaned_registrations(entries, exists_fn=lambda p: p in exists)
expect("find_orphaned_registrations: flags only the enabled dangling entry",
       orphans == ["ora-dangling"], repr(orphans))
expect("find_orphaned_registrations: disabled entry with missing file is NOT flagged",
       "ora-paused-missing" not in orphans)
expect("find_orphaned_registrations: no entries -> []",
       tfrp.find_orphaned_registrations([], exists_fn=lambda p: True) == [])

# --- find_archived_registrations (added 2026-08-14, closing the ora-cam-reconciliation-annual
#     blind spot: an entry whose folder was moved under _archive_* keeps existing on disk at
#     its NEW path, so find_orphaned_registrations's plain os.path.isfile check can never catch
#     it -- confirmed 2 months of zero alarms, 2026-06-11 to 2026-08-14, for exactly this case) ---
archive_entries = [
    {"id": "ora-live", "enabled": True,
     "filePath": r"C:\Users\Owner\OneDrive - Oxford Capital Partners\Documents\Claude\Scheduled\ora-live\SKILL.md"},
    {"id": "ora-cam-reconciliation-annual", "enabled": True,
     "filePath": r"C:\Users\Owner\OneDrive - Oxford Capital Partners\Documents\Claude\Scheduled\_archive_2026-06-11_orphans\ora-cam-reconciliation-annual\SKILL.md"},
    {"id": "ora-paused-archived", "enabled": False,
     "filePath": r"C:\Users\Owner\.claude\scheduled-tasks\_archive_2026-08-09_retired\ora-paused-archived\SKILL.md"},
    {"id": "ora-forward-slash-archived", "enabled": True,
     "filePath": "C:/Users/Owner/.claude/scheduled-tasks/_archive_2026-08-13_retired/ora-forward-slash-archived/SKILL.md"},
]
archived = tfrp.find_archived_registrations(archive_entries)
expect("find_archived_registrations: flags the enabled entry under an _archive_* segment",
       "ora-cam-reconciliation-annual" in archived, repr(archived))
expect("find_archived_registrations: does not flag a normal live entry",
       "ora-live" not in archived)
expect("find_archived_registrations: disabled archived entry is NOT flagged (mirrors orphaned-check convention)",
       "ora-paused-archived" not in archived)
expect("find_archived_registrations: catches forward-slash paths too, not just backslash",
       "ora-forward-slash-archived" in archived)
expect("find_archived_registrations: sorted output",
       archived == sorted(archived))
expect("find_archived_registrations: no entries -> []",
       tfrp.find_archived_registrations([]) == [])
expect("find_archived_registrations: entry with no filePath -> not flagged, not a crash",
       tfrp.find_archived_registrations([{"id": "ora-nopath", "enabled": True, "filePath": None}]) == [])

# --- store_discovery.store_name / skill_folder_root (regression: probe originally passed
#     the label straight to discover_store() instead of resolving it to a store name first) ---
expect("store_name: cc -> claude-code-sessions", sd.store_name("cc") == "claude-code-sessions")
expect("store_name: lams -> local-agent-mode-sessions", sd.store_name("lams") == "local-agent-mode-sessions")
expect("store_name: unknown label -> None", sd.store_name("nope") is None)
expect("skill_folder_root: cc resolves to an expanded, non-empty path",
       bool(sd.skill_folder_root("cc")) and "%USERPROFILE%" not in sd.skill_folder_root("cc"))
expect("skill_folder_root: unknown label -> None", sd.skill_folder_root("nope") is None)

# --- find_stale_vs_git (OI-170): on-disk SKILL.md vs the blob committed at HEAD ---------------
#     The scheduler reads the WORKING TREE, not git, so a merged-but-not-checked-out SKILL.md
#     exists at the right path with the wrong bytes -- clean by all three sibling checks.
#     Both dependencies are injected, so nothing here shells out to git or touches a live tree.
_STALE_ENTRY = [{"id": "ora-t1", "filePath": "/x/SKILL.md", "enabled": True}]


def _stale(entries, verdict):
    return tfrp.find_stale_vs_git(entries, differs=lambda p: verdict)


expect("find_stale_vs_git: clean -> no finding",
       _stale(_STALE_ENTRY, tfrp.STATE_CLEAN) == [])
expect("find_stale_vs_git: behind upstream -> flagged (the OI-170 case)",
       _stale(_STALE_ENTRY, tfrp.STATE_BEHIND) == ["ora-t1"])
expect("find_stale_vs_git: uncommitted -> flagged (content in no commit)",
       _stale(_STALE_ENTRY, tfrp.STATE_UNCOMMITTED) == ["ora-t1"])
expect("find_stale_vs_git: no verdict (None) -> NOT a finding",
       _stale(_STALE_ENTRY, None) == [])
expect("find_stale_vs_git: disabled entry -> skipped (matches sibling checks)",
       _stale([{"id": "ora-t1", "filePath": "/x/SKILL.md", "enabled": False}],
              tfrp.STATE_BEHIND) == [])
expect("find_stale_vs_git: entry with no filePath -> not flagged, not a crash",
       _stale([{"id": "ora-t1", "filePath": None, "enabled": True}],
              tfrp.STATE_BEHIND) == [])
expect("find_stale_vs_git: no entries -> []", tfrp.find_stale_vs_git([]) == [])
expect("find_stale_vs_git: sorted output",
       _stale([{"id": "ora-z", "filePath": "/z/SKILL.md", "enabled": True},
               {"id": "ora-a", "filePath": "/a/SKILL.md", "enabled": True}],
              tfrp.STATE_BEHIND) == ["ora-a", "ora-z"])
expect("find_stale_states: carries the per-id reason",
       tfrp.find_stale_states(_STALE_ENTRY,
                              state_fn=lambda p: tfrp.STATE_UNCOMMITTED)
       == {"ora-t1": tfrp.STATE_UNCOMMITTED})


# --- OI-182: DIRECTION. The regression that motivated this whole change ------------------------
def _fake_git(*results):
    """Each call returns the next (returncode, stdout) in sequence."""
    seq = iter(results)

    def run(*_a, **_k):
        rc, out = next(seq)
        return type("R", (), {"returncode": rc, "stdout": out})()
    return run


# Call order inside _git_path_state: rev-parse --show-toplevel, THEN
# ls-files --error-unmatch (tracked check), THEN diff --quiet HEAD (worktree
# vs HEAD), THEN [upstream lookup, merge-base, base..upstream, worktree..upstream].
_TOP = (0, b"/repo\n")           # rev-parse --show-toplevel
_TRACKED = (0, b"")              # ls-files --error-unmatch  (rc0 = tracked)
_UNTRACKED = (1, b"")            # ls-files --error-unmatch  (rc1 = untracked)
_UP = (0, b"origin/main\n")      # rev-parse --abbrev-ref @{upstream}
_MB = (0, b"abc123\n")           # merge-base HEAD upstream
_WT_CLEAN = (0, b"")             # diff --quiet HEAD -- path       (worktree == HEAD)
_WT_DIRTY = (1, b"")             # diff --quiet HEAD -- path       (worktree != HEAD)
_UPSTREAM_CLEAN = (0, b"")       # diff --quiet upstream -- path   (content identical)
_UPSTREAM_DIFFERS = (1, b"")     # diff --quiet upstream -- path   (content differs)
_P = "/repo/x/SKILL.md"

# THE OI-182 REGRESSION: worktree == HEAD, and upstream did NOT touch this path
# since the merge-base -> we are merely AHEAD (committed, unpushed). Before this
# fix that produced a finding; it must now be CLEAN.
expect("OI-182: AHEAD of upstream (base..upstream empty) -> CLEAN, not a finding",
       tfrp._git_path_state(_P, run=_fake_git(_TOP, _TRACKED, _WT_CLEAN, _UP, _MB,
                                              (0, b"")))
       == tfrp.STATE_CLEAN)
expect("OI-182: BEHIND, content genuinely differs -> STATE_BEHIND",
       tfrp._git_path_state(_P, run=_fake_git(_TOP, _TRACKED, _WT_CLEAN, _UP, _MB,
                                              (1, b""), _UPSTREAM_DIFFERS))
       == tfrp.STATE_BEHIND)
expect("OI-182: uncommitted short-circuits BEFORE any upstream lookup",
       tfrp._git_path_state(_P, run=_fake_git(_TOP, _TRACKED, _WT_DIRTY))
       == tfrp.STATE_UNCOMMITTED)
expect("OI-182: no upstream configured, clean tree -> CLEAN (cannot be behind)",
       tfrp._git_path_state(_P, run=_fake_git(_TOP, _TRACKED, _WT_CLEAN, (128, b"")))
       == tfrp.STATE_CLEAN)

# Same-day follow-up finding #2 (independent review): DIVERGED but content-identical.
# base..upstream is non-empty (the path's HISTORY diverged) but the worktree-vs-
# upstream CONTENT check says they match -- confirmed live against real git repos
# with independently-committed byte-identical fixes. Must be CLEAN, not BEHIND.
expect("DIVERGED-but-identical: base..upstream non-empty, content matches -> CLEAN",
       tfrp._git_path_state(_P, run=_fake_git(_TOP, _TRACKED, _WT_CLEAN, _UP, _MB,
                                              (1, b""), _UPSTREAM_CLEAN))
       == tfrp.STATE_CLEAN)
expect("DIVERGED, content also differs -> BEHIND (the real case)",
       tfrp._git_path_state(_P, run=_fake_git(_TOP, _TRACKED, _WT_CLEAN, _UP, _MB,
                                              (1, b""), _UPSTREAM_DIFFERS))
       == tfrp.STATE_BEHIND)
expect("worktree-vs-upstream content check exit 128 -> None, not a finding",
       tfrp._git_path_state(_P, run=_fake_git(_TOP, _TRACKED, _WT_CLEAN, _UP, _MB,
                                              (1, b""), (128, b"")))
       is None)

# Same-day follow-up finding #1 (independent review): UNTRACKED. `git diff --quiet
# HEAD -- path` exits 0 for an untracked file (confirmed live) -- it is NOT the
# rc128 the earlier draft assumed. ls-files --error-unmatch is the correct probe,
# but (finding #1's SECOND pass, below) only when gated on the file actually
# existing on disk -- ls-files rc1 alone cannot distinguish "untracked but
# present" from "path absent entirely", and _git_path_state calls the REAL
# os.path.isfile (not injected), so these two cases use a real temp file /
# a real absent path rather than mocking isfile.
_present_untracked = tempfile.mktemp(suffix=".md")
with open(_present_untracked, "w", encoding="utf-8") as _f:
    _f.write("untracked content")
_absent_path = tempfile.mktemp(suffix=".md")   # deliberately never created

expect("UNTRACKED-AND-PRESENT -> STATE_UNCOMMITTED (verified live: diff exits 0,"
       " not 128, for an untracked path -- ls-files is the correct gate)",
       tfrp._git_path_state(_present_untracked, run=_fake_git(_TOP, _UNTRACKED))
       == tfrp.STATE_UNCOMMITTED)
os.remove(_present_untracked)

# THE REGRESSION independent review's second pass caught: a brand-new SKILL.md
# merged to origin and never pulled has NOTHING on disk. ls-files still returns
# rc1 (same as untracked-present) -- without the isfile guard this misreported
# STATE_UNCOMMITTED ("commit it or revert it", which is impossible -- there is
# nothing to commit). It must fall through to step 1 and resolve via the
# existing upstream logic, landing on the SAME verdict the pre-step-0 function
# already got right: BEHIND when upstream has it, CLEAN when it does not.
expect("ABSENT path (ls-files rc1, but NOT on disk) -> falls through, NOT"
       " STATE_UNCOMMITTED -- resolves via upstream logic to BEHIND",
       tfrp._git_path_state(_absent_path,
                            run=_fake_git(_TOP, _UNTRACKED, _WT_CLEAN, _UP, _MB,
                                          (1, b""), _UPSTREAM_DIFFERS))
       == tfrp.STATE_BEHIND)
expect("ABSENT path, upstream doesn't have it either -> CLEAN, not a finding",
       tfrp._git_path_state(_absent_path,
                            run=_fake_git(_TOP, _UNTRACKED, _WT_CLEAN, (128, b"")))
       == tfrp.STATE_CLEAN)

expect("ls-files --error-unmatch failure (not tracked-or-untracked-or-absent) -> None",
       tfrp._git_path_state(_P, run=_fake_git(_TOP, (2, b""))) is None)

expect("_git_path_state: worktree-vs-HEAD failure (tracked) -> None, no verdict",
       tfrp._git_path_state(_P, run=_fake_git(_TOP, _TRACKED, (128, b""))) is None)
expect("_git_path_state: merge-base failure -> None (unrelated histories)",
       tfrp._git_path_state(_P, run=_fake_git(_TOP, _TRACKED, _WT_CLEAN, _UP,
                                              (128, b""))) is None)
expect("_git_path_state: base..upstream exit 128 -> None, not a finding",
       tfrp._git_path_state(_P, run=_fake_git(_TOP, _TRACKED, _WT_CLEAN, _UP, _MB,
                                              (128, b"")))
       is None)
expect("_git_path_state: not a git repo -> None (the LAMS/OneDrive case)",
       tfrp._git_path_state("/x/SKILL.md", run=_fake_git((128, b""))) is None)
expect("_git_path_state: git raising -> None, not an exception",
       tfrp._git_path_state(
           "/x/SKILL.md",
           run=lambda *a, **k: (_ for _ in ()).throw(OSError("no git"))) is None)

# --- summary -------------------------------------------------------------------------------
passed = sum(1 for ok, _ in results if ok)
print("\ntask-folder-registration-probe tests: %d/%d passed" % (passed, len(results)))
sys.exit(0 if passed == len(results) else 1)
