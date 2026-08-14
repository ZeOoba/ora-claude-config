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

# --- summary -------------------------------------------------------------------------------
passed = sum(1 for ok, _ in results if ok)
print("\ntask-folder-registration-probe tests: %d/%d passed" % (passed, len(results)))
sys.exit(0 if passed == len(results) else 1)
