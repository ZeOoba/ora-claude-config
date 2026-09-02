#!/usr/bin/env python3
"""ORA retired-skill-serving guard -- detects a retired skill still live in an
installed skill bundle.

WHY (2026-08-28, ORA Automation Audit Revision 19): `conversation-archival`
was formally retired in the canonical `ora-skills` repo 2026-08-05 (moved to
`_archive/conversation-archival_retired-2026-08-05/`) but was still present
and invocable in a live session's skill catalog on 2026-08-28 -- 23 days
later. Root cause: LAMS/Cowork does not read skills live from the repo. It
reads a PACKAGED, INSTALLED bundle under
`AppData/Roaming/Claude/local-agent-mode-sessions/skills-plugin/<plugin-id>/
<version-id>/skills/`, built at whatever point `package-and-stage-skill` last
ran and Gabriel last clicked "Save skill." A skill retired in the source repo
after that point keeps shipping inside the stale installed bundle until the
next repackage+reimport -- no existing guard checked this; the only reason
the leak surfaced at all was an unrelated audit pass noticing the skill in
its own live catalog. This probe makes that check standing instead of
accidental.

WHAT IT DOES
  1. Enumerates genuinely-retired skill names from `ora-skills/_archive/`.
     Every top-level `_archive/<entry>/` that directly contains a SKILL.md
     is a candidate (this covers every naming convention observed to date:
     `<name>_retired-YYYY-MM-DD`, bare `<name>` with no suffix at all --
     e.g. `deal-screen`, `cap-rate-snapshot` -- and version-snapshot names
     like `<name>_v1.2_archived-YYYY-MM-DD`). The candidate's name is the
     `_retired-YYYY-MM-DD` capture group when that pattern matches, else the
     raw directory name. A candidate is DROPPED if that name is ALSO a live
     top-level skill directory in the repo root -- this is what excludes
     version-snapshot archives of a still-current skill (e.g.
     `lease-abstraction-pipeline_v1.2_archived-2026-06-11`, where
     `lease-abstraction-pipeline` is still very much live) without having to
     enumerate every version-snapshot naming variant by hand. Reimport-prep/
     batch-staging scratch folders (e.g. `2026-08-21_batch5-reimport/`) are
     excluded structurally: they nest their skill copies one level deeper and
     never carry a SKILL.md directly at their own top level.
  2. Enumerates every installed plugin-bundle instance across BOTH locations
     Cowork uses:
       - `local-agent-mode-sessions/skills-plugin/<plugin-id>/<version-id>/
         skills/` -- the standalone Save-skill cache (where individually
         imported skills like ora-skills' own land). Only the
         MOST-RECENTLY-MODIFIED `<version-id>` per `<plugin-id>` is treated
         as currently served -- an older, superseded version directory left
         behind by a prior reimport should not raise a false alarm for a
         name that only lingers in dead weight, never in what Cowork
         actually loads.
       - `local-agent-mode-sessions/<session-id>/<sub-id>/rpm/plugin_<id>/
         skills/<skill>/` -- the marketplace/plugin-bundle runtime cache
         (found 2026-08-28: real, contains `cowork-plugin-management` and
         `desktop-commander` on this machine; empty of any ora-skills content
         today, but `ora-skills/tools/build_plugin.py` exists specifically to
         ship ora-skills content as a plugin bundle, so this tree is a real
         future landing spot, not a hypothetical one). All `rpm/plugin_*/`
         entries found are treated as live -- no version-directory layer was
         observed here to filter by staleness.
  3. Flags any retired name still present in an installed bundle from either
     location.

This guard is READ-ONLY -- it never repackages, reimports, or deletes an
installed bundle. Fixing a flagged leak is `package-and-stage-skill`'s job
(repackage the current repo state, then Gabriel clicks "Save skill" to
reinstall); this probe only makes the gap visible.

Exit 0 = clean (or nothing retired yet to check). Exit 1 = [ACTION], at least
one retired skill is still being served from an installed bundle. Exit 2 =
PROBE ERROR -- the filesystem scan itself failed (permission error, or a
directory removed mid-scan by a concurrent reimport); the caller's
scheduled-run alarm wiring treats any non-zero exit as an alarm, so this is
not silently missed, but is worth distinguishing from a genuine leak in the
alarm body if the caller inspects stderr.

USAGE
  python retired-skill-serving-guard.py
  python retired-skill-serving-guard.py --selftest
"""
import argparse
import os
import re
import sys
import tempfile

ORA_SKILLS = os.path.join(os.path.expanduser("~"), "ora-skills")
LOCAL_AGENT_MODE_SESSIONS = os.path.join(
    os.path.expanduser("~"), "AppData", "Roaming", "Claude",
    "local-agent-mode-sessions")
BUNDLE_ROOT = os.path.join(LOCAL_AGENT_MODE_SESSIONS, "skills-plugin")

RETIRED_DIR_RE = re.compile(r"^(?P<name>.+)_retired-\d{4}-\d{2}-\d{2}$")
RPM_PLUGIN_DIR_RE = re.compile(r"^plugin_.+$")


def retired_skill_names(ora_skills_root):
    """Every genuinely-retired skill name -- any top-level `_archive/<entry>/`
    that directly contains a SKILL.md, with its name resolved from the
    `_retired-YYYY-MM-DD` suffix when present (else the raw directory name),
    and dropped if that name is also a live top-level skill directory in the
    repo root (excludes version-snapshot archives of a still-current skill).
    Batch/scratch staging folders never match: they don't carry a SKILL.md at
    their own top level, only nested one level deeper."""
    archive = os.path.join(ora_skills_root, "_archive")
    if not os.path.isdir(archive):
        return set()

    live_names = {
        entry for entry in os.listdir(ora_skills_root)
        if os.path.isdir(os.path.join(ora_skills_root, entry)) and entry != "_archive"
    }

    def _is_version_snapshot_of_a_live_skill(entry):
        # e.g. "lease-abstraction-pipeline_v1.2_archived-2026-06-11" is a version
        # snapshot of the still-live "lease-abstraction-pipeline", not a retirement.
        # Prefix-match against every live name rather than trying to parse the
        # suffix (version-snapshot suffixes aren't a single fixed pattern).
        return any(entry.startswith(live + "_") for live in live_names)

    names = set()
    for entry in os.listdir(archive):
        entry_path = os.path.join(archive, entry)
        if not os.path.isdir(entry_path):
            continue
        if not os.path.isfile(os.path.join(entry_path, "SKILL.md")):
            continue
        m = RETIRED_DIR_RE.match(entry)
        candidate = m.group("name") if m else entry
        if candidate in live_names:
            continue  # still live under this exact name -- not a retirement
        if not m and _is_version_snapshot_of_a_live_skill(entry):
            continue  # a version snapshot of a still-live skill, not a retirement
        names.add(candidate)
    return names


def _newest_version_skills_dirs(bundle_root):
    """{plugin_id: skills_dir} for the skills-plugin cache, one entry per
    plugin_id -- only the most-recently-modified version_id directory (by
    mtime of the version_id dir itself). An older, superseded version left
    behind by a prior reimport is excluded, so a name that only lingers
    there can never raise a false [ACTION]."""
    result = {}
    if not os.path.isdir(bundle_root):
        return result
    for plugin_id in os.listdir(bundle_root):
        plugin_path = os.path.join(bundle_root, plugin_id)
        if not os.path.isdir(plugin_path):
            continue
        newest_version_path, newest_mtime = None, None
        for version_id in os.listdir(plugin_path):
            version_path = os.path.join(plugin_path, version_id)
            if not os.path.isdir(version_path):
                continue
            mtime = os.path.getmtime(version_path)
            if newest_mtime is None or mtime > newest_mtime:
                newest_version_path, newest_mtime = version_path, mtime
        if newest_version_path is None:
            continue
        skills_dir = os.path.join(newest_version_path, "skills")
        if os.path.isdir(skills_dir):
            result[plugin_id] = skills_dir
    return result


def _rpm_plugin_skills_dirs(session_root):
    """[rpm_plugin_skills_dir, ...] for every `rpm/plugin_<id>/skills/`
    directory found under any `<session-id>/<sub-id>/` pair beneath
    `local-agent-mode-sessions`. No version-directory layer was observed
    here (each plugin_<id> holds skills/ directly), so every match found is
    treated as currently live -- unlike the skills-plugin cache, there is no
    staleness signal available to filter by."""
    found = []
    if not os.path.isdir(session_root):
        return found
    for session_id in os.listdir(session_root):
        session_path = os.path.join(session_root, session_id)
        if not os.path.isdir(session_path) or session_id == "skills-plugin":
            continue
        for sub_id in os.listdir(session_path):
            rpm_path = os.path.join(session_path, sub_id, "rpm")
            if not os.path.isdir(rpm_path):
                continue
            for entry in os.listdir(rpm_path):
                if not RPM_PLUGIN_DIR_RE.match(entry):
                    continue
                skills_dir = os.path.join(rpm_path, entry, "skills")
                if os.path.isdir(skills_dir):
                    found.append(skills_dir)
    return found


def installed_bundle_skill_dirs(bundle_root, session_root=None):
    """{skill_name: [bundle_skills_dir, ...]} across both installed-plugin
    locations Cowork uses (skills-plugin, newest version only per plugin_id;
    and rpm/plugin_*/, every match). `session_root` defaults to
    `bundle_root`'s parent (the shape LOCAL_AGENT_MODE_SESSIONS/BUNDLE_ROOT
    already have in production) so callers that only pass bundle_root keep
    working."""
    if session_root is None:
        session_root = os.path.dirname(os.path.normpath(bundle_root))

    found = {}

    def _add(skills_dir):
        for skill_name in os.listdir(skills_dir):
            if os.path.isdir(os.path.join(skills_dir, skill_name)):
                found.setdefault(skill_name, []).append(skills_dir)

    for skills_dir in _newest_version_skills_dirs(bundle_root).values():
        _add(skills_dir)
    for skills_dir in _rpm_plugin_skills_dirs(session_root):
        _add(skills_dir)

    return found


def find_leaks(ora_skills_root, bundle_root, session_root=None):
    """Return {retired_name: [bundle_skills_dir, ...]} for every retired
    skill still present in at least one installed bundle."""
    retired = retired_skill_names(ora_skills_root)
    installed = installed_bundle_skill_dirs(bundle_root, session_root)
    return {name: installed[name] for name in retired if name in installed}


def _touch_skill_md(path):
    os.makedirs(path, exist_ok=True)
    with open(os.path.join(path, "SKILL.md"), "w", encoding="utf-8") as f:
        f.write("---\nname: x\n---\n")


def _selftest():
    import time

    with tempfile.TemporaryDirectory() as tmp:
        # ---- retired_skill_names(): all naming conventions + the live-name guard ----
        skills_root = os.path.join(tmp, "ora-skills")
        archive = os.path.join(skills_root, "_archive")
        os.makedirs(archive)

        # dated-suffix convention -- genuine retirement
        _touch_skill_md(os.path.join(archive, "old-skill_retired-2026-08-05"))
        # bare/unsuffixed convention -- also a genuine retirement (comment-8 class)
        _touch_skill_md(os.path.join(archive, "deal-screen"))
        # version-snapshot of a skill that is STILL LIVE under its base name --
        # must NOT be treated as a retirement, or a live skill false-alarms
        _touch_skill_md(os.path.join(archive, "lease-abstraction-pipeline_v1.2_archived-2026-06-11"))
        os.makedirs(os.path.join(skills_root, "lease-abstraction-pipeline"))  # the live skill
        # reimport-scratch dir -- no SKILL.md at ITS OWN top level, must not match
        os.makedirs(os.path.join(archive, "2026-08-21_batch5-reimport", "still-live-skill"))

        retired = retired_skill_names(skills_root)
        assert retired == {"old-skill", "deal-screen"}, retired

        # ---- installed_bundle_skill_dirs(): newest-version-only + rpm tree ----
        bundle_root = os.path.join(tmp, "skills-plugin")
        v1_skills = os.path.join(bundle_root, "plugin-a", "v1-old", "skills")
        v2_skills = os.path.join(bundle_root, "plugin-a", "v2-new", "skills")
        os.makedirs(os.path.join(v1_skills, "old-skill"))     # superseded version -- must be ignored
        os.makedirs(os.path.join(v1_skills, "orphan-only-in-old-version"))
        os.makedirs(os.path.join(v2_skills, "deal-screen"))   # current version -- leaked, must be caught
        # v2 must look newer than v1 to the mtime-based "current version" pick
        old_t = time.time() - 3600
        os.utime(os.path.join(bundle_root, "plugin-a", "v1-old"), (old_t, old_t))

        session_root = tmp  # local-agent-mode-sessions/ equivalent; sibling to skills-plugin
        rpm_skills = os.path.join(session_root, "sess-1", "sub-1", "rpm", "plugin_abc", "skills")
        os.makedirs(os.path.join(rpm_skills, "old-skill"))    # leaked via the rpm tree

        installed = installed_bundle_skill_dirs(bundle_root, session_root)
        assert "orphan-only-in-old-version" not in installed, \
            "a superseded version directory must not be scanned"
        assert set(installed.keys()) == {"deal-screen", "old-skill"}, installed
        assert installed["deal-screen"] == [v2_skills], installed["deal-screen"]
        assert installed["old-skill"] == [rpm_skills], installed["old-skill"]

        # ---- find_leaks(): both leaks, from two different installed locations ----
        leaks = find_leaks(skills_root, bundle_root, session_root)
        assert set(leaks.keys()) == {"old-skill", "deal-screen"}, leaks
        assert leaks["old-skill"] == [rpm_skills]
        assert leaks["deal-screen"] == [v2_skills]

        # no retirements at all -> no leaks, not an error
        empty_root = os.path.join(tmp, "no-archive-yet")
        os.makedirs(empty_root)
        assert find_leaks(empty_root, bundle_root, session_root) == {}

        # default session_root (derived from bundle_root's parent) matches production shape
        installed_default = installed_bundle_skill_dirs(bundle_root)
        assert set(installed_default.keys()) == {"deal-screen", "old-skill"}, installed_default

    print("selftest: PASS")
    return 0


def main(argv=None):
    for _stream in (sys.stdout, sys.stderr):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ora-skills-root", default=ORA_SKILLS)
    ap.add_argument("--bundle-root", default=BUNDLE_ROOT)
    ap.add_argument("--session-root", default=LOCAL_AGENT_MODE_SESSIONS)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)

    if a.selftest:
        return _selftest()

    if not os.path.isdir(a.ora_skills_root):
        sys.stderr.write("no such directory: %s\n" % a.ora_skills_root)
        return 1

    # PROBE ERROR (exit 2) is distinct from both clean (0) and a genuine
    # [ACTION] finding (1) -- a scheduled run that hits a permission error or
    # a directory deleted mid-scan (another session mid-reimport) must not
    # read as a leak, or as clean, either of which would be worse than a
    # loud, unambiguous "the probe itself could not finish."
    try:
        retired = retired_skill_names(a.ora_skills_root)
        print("retired skills on record (top-level _archive/ entries carrying a SKILL.md, "
              "any naming convention, excluding names still live in the repo root): %d" % len(retired))

        if not os.path.isdir(a.bundle_root) and not os.path.isdir(a.session_root):
            print("no installed skills-plugin or session tree found -- nothing to check "
                  "(this session's surface may not use the LAMS bundle mechanism)")
            return 0

        leaks = find_leaks(a.ora_skills_root, a.bundle_root, a.session_root)
    except OSError as e:
        sys.stderr.write("PROBE ERROR -- could not complete the filesystem scan: %s\n" % e)
        return 2
    if not leaks:
        print("clean: no retired skill found in any installed bundle "
              "(checked skills-plugin/<newest version> and rpm/plugin_*/)")
        return 0

    print("[ACTION] %d retired skill(s) still served from an installed bundle:" % len(leaks))
    for name, dirs in sorted(leaks.items()):
        for d in dirs:
            print("  %s -> %s" % (name, d))
    print("Fix: repackage via package-and-stage-skill (the retirement already "
          "happened in the repo -- this is a stale installed bundle, not a repo bug) "
          "then reinstall (Gabriel clicks 'Save skill').")
    return 1


if __name__ == "__main__":
    sys.exit(main())
