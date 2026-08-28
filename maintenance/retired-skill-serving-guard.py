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
  1. Enumerates genuinely-retired skill names from `ora-skills/_archive/` --
     ONLY directories matching `<name>_retired-YYYY-MM-DD` (the convention
     used by every real retirement so far). This is deliberately narrower
     than "any SKILL.md anywhere under _archive": most `_archive/` entries
     are reimport-prep/batch-staging scratch copies of skills that are still
     very much live (e.g. `2026-08-21_batch5-reimport/`), and treating those
     as retirements would flood this guard with false [ACTION]s on the first
     run.
  2. Enumerates every installed plugin-bundle instance under
     `local-agent-mode-sessions/skills-plugin/*/*/skills/` (there can be more
     than one installed version at once) and lists its skill folder names.
  3. Flags any retired name still present in an installed bundle.

This guard is READ-ONLY -- it never repackages, reimports, or deletes an
installed bundle. Fixing a flagged leak is `package-and-stage-skill`'s job
(repackage the current repo state, then Gabriel clicks "Save skill" to
reinstall); this probe only makes the gap visible.

Exit 0 = clean (or nothing retired yet to check). Exit 1 = [ACTION], at least
one retired skill is still being served from an installed bundle.

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
BUNDLE_ROOT = os.path.join(
    os.path.expanduser("~"), "AppData", "Roaming", "Claude",
    "local-agent-mode-sessions", "skills-plugin")

RETIRED_DIR_RE = re.compile(r"^(?P<name>.+)_retired-\d{4}-\d{2}-\d{2}$")


def retired_skill_names(ora_skills_root):
    """Names retired via the `<name>_retired-YYYY-MM-DD` convention -- the
    only pattern used by every real retirement to date. Scratch/reimport
    staging folders under _archive/ (dated-prefix names, batch dirs) don't
    match and are correctly excluded."""
    archive = os.path.join(ora_skills_root, "_archive")
    if not os.path.isdir(archive):
        return set()
    names = set()
    for entry in os.listdir(archive):
        m = RETIRED_DIR_RE.match(entry)
        if m and os.path.isdir(os.path.join(archive, entry)):
            names.add(m.group("name"))
    return names


def installed_bundle_skill_dirs(bundle_root):
    """{skill_name: [bundle_skills_dir, ...]} for every installed plugin
    bundle instance found under bundle_root (there can be several -- old
    versions aren't necessarily cleaned up on reimport)."""
    found = {}
    if not os.path.isdir(bundle_root):
        return found
    for plugin_id in os.listdir(bundle_root):
        plugin_path = os.path.join(bundle_root, plugin_id)
        if not os.path.isdir(plugin_path):
            continue
        for version_id in os.listdir(plugin_path):
            skills_dir = os.path.join(plugin_path, version_id, "skills")
            if not os.path.isdir(skills_dir):
                continue
            for skill_name in os.listdir(skills_dir):
                if os.path.isdir(os.path.join(skills_dir, skill_name)):
                    found.setdefault(skill_name, []).append(skills_dir)
    return found


def find_leaks(ora_skills_root, bundle_root):
    """Return {retired_name: [bundle_skills_dir, ...]} for every retired
    skill still present in at least one installed bundle."""
    retired = retired_skill_names(ora_skills_root)
    installed = installed_bundle_skill_dirs(bundle_root)
    return {name: installed[name] for name in retired if name in installed}


def _selftest():
    with tempfile.TemporaryDirectory() as tmp:
        skills_root = os.path.join(tmp, "ora-skills")
        archive = os.path.join(skills_root, "_archive")
        os.makedirs(archive)
        # a genuine retirement
        os.makedirs(os.path.join(archive, "old-skill_retired-2026-08-05"))
        # a reimport-scratch dir that must NOT be read as a retirement
        os.makedirs(os.path.join(archive, "2026-08-21_batch5-reimport", "still-live-skill"))

        bundle_root = os.path.join(tmp, "skills-plugin")
        skills_dir = os.path.join(bundle_root, "plugin-a", "v1", "skills")
        os.makedirs(os.path.join(skills_dir, "old-skill"))       # leaked
        os.makedirs(os.path.join(skills_dir, "still-live-skill"))  # not retired, fine

        retired = retired_skill_names(skills_root)
        assert retired == {"old-skill"}, retired

        installed = installed_bundle_skill_dirs(bundle_root)
        assert set(installed.keys()) == {"old-skill", "still-live-skill"}, installed

        leaks = find_leaks(skills_root, bundle_root)
        assert set(leaks.keys()) == {"old-skill"}, leaks
        assert leaks["old-skill"] == [skills_dir]

        # no retirements at all -> no leaks, not an error
        empty_root = os.path.join(tmp, "no-archive-yet")
        os.makedirs(empty_root)
        assert find_leaks(empty_root, bundle_root) == {}

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
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)

    if a.selftest:
        return _selftest()

    if not os.path.isdir(a.ora_skills_root):
        sys.stderr.write("no such directory: %s\n" % a.ora_skills_root)
        return 1

    retired = retired_skill_names(a.ora_skills_root)
    print("retired skills on record (name_retired-YYYY-MM-DD convention): %d" % len(retired))

    if not os.path.isdir(a.bundle_root):
        print("no installed skills-plugin bundle found at %s -- nothing to check "
              "(this session's surface may not use the LAMS bundle mechanism)" % a.bundle_root)
        return 0

    leaks = find_leaks(a.ora_skills_root, a.bundle_root)
    if not leaks:
        print("clean: no retired skill found in any installed bundle")
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
