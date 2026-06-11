#!/usr/bin/env python3
"""
ORA Claude Setup Self-Audit  (read-only, fail-open)
====================================================
Deterministic daily health scan of the Claude Code + Cowork setup.
Adds the checks the existing probes do NOT cover:
  1. FLEET PRESENCE     -- are the expected tasks (decided 14-task baseline, 2026-06-09) present in the live store ~/.claude/scheduled-tasks/?
  2. SKILL FRONTMATTER  -- any SKILL.md with collapsed/unparseable frontmatter?
  3. SECRET SCAN        -- any live credential literal in config/backups/logs?
  4. CONNECTOR ALLOWLIST-- any non-Outlook (Gmail/Google/Drive) connector re-authed?
  5. MEMORY/FLEET DRIFT -- does documented fleet count match the live registry?

Companion to (does NOT replace): fleet-status.py, doctrine-integrity-probe.py,
governor-drift-probe.py, memory-integrity-probe.py, eos-telemetry-rollup.py.

Design rules (mirror the EOS reliability spec):
  * READ-ONLY. Never writes, sends, or mutates anything.
  * FAIL-OPEN per check. Any exception in one check -> that check reports SKIP, others continue.
  * Exit 0 always unless --strict and a CRITICAL is found (for an out-of-band dead-man wrapper).
  * stdlib only. No network. Fast (<2s typical).

Usage:  python setup-self-audit.py [--json] [--strict]
"""
import os, sys, json, re, glob, datetime, traceback

HOME = os.path.expanduser("~")
CLAUDE = os.path.join(HOME, ".claude")
ROAMING = os.path.join(os.environ.get("APPDATA", os.path.join(HOME, "AppData", "Roaming")), "Claude")
NOW = datetime.datetime.now(datetime.timezone.utc)

results = []  # list of dicts: {check, status (OK|WARN|CRIT|SKIP), detail, items[]}

def add(check, status, detail, items=None):
    results.append({"check": check, "status": status, "detail": detail, "items": items or []})

# (dead helpers _parse_ts / _load_registry removed 2026-06-07: Check 1 is presence-only against
#  the live store ~/.claude/scheduled-tasks/. The orphaned-LAMS reader they fed is gone — its
#  lingering definition previously caused a setup audit to mis-flag this script as still on LAMS.)

# ---- Check 1: FLEET PRESENCE (live store = ~/.claude/scheduled-tasks/) ----
# The app migrated scheduler stores 2026-06-06; the LAMS registry is orphaned. The live
# store keeps only SKILL.md per task (no on-disk lastRunAt) -> this probe verifies the
# EXPECTED task set is present on disk; run-liveness is verified by the Health Guard email,
# the GitHub ora-cowork-watchdog, and the scheduled-tasks MCP (callable only inside Claude).
NEW_STORE = os.path.join(CLAUDE, "scheduled-tasks")
# Decided baseline 2026-06-09 (Gabriel): 5 core + 9 ops = 14. The 8 Tier-2 internal tasks were
# RETIRED the same day (archived to _archive_2026-06-09_retired; do NOT re-register).
EXPECTED_TASKS = {"ora-health-guard", "ora-am-brief", "ora-setup-audit", "ora-pm-ledger",
                  "ora-deal-sourcing-scan",
                  "ora-automation-health-monitor", "ora-consolidate-memory-monthly",
                  "ora-dashboard-refresh", "ora-dormant-thread-revival",
                  "ora-master-workbook-ingest", "ora-skill-text-audit",
                  "ora-week-ahead-briefing", "ora-weekly-hygiene",
                  "ora-weekly-tooling-intel-sweep"}

def _live_tasks():
    out = []
    if os.path.isdir(NEW_STORE):
        for d in sorted(os.listdir(NEW_STORE)):
            if d.startswith("_"):  # _archive*, _shared
                continue
            if os.path.exists(os.path.join(NEW_STORE, d, "SKILL.md")):
                out.append(d)
    return out

def check_fleet():
    try:
        if not os.path.isdir(NEW_STORE):
            add("fleet", "SKIP", "live scheduler store ~/.claude/scheduled-tasks/ not found")
            return
        live = _live_tasks()
        note = "liveness via Health Guard email / GitHub ora-cowork-watchdog / scheduled-tasks MCP (lastRunAt not on disk)"
        missing = sorted(EXPECTED_TASKS - set(live))
        extra = sorted(set(live) - EXPECTED_TASKS)
        if missing:
            add("fleet", "CRIT", f"{len(live)} live tasks; MISSING expected: {', '.join(missing)} | {note}", live)
        elif extra:
            add("fleet", "WARN", f"{len(live)} live tasks; all {len(EXPECTED_TASKS)} expected present + extras: {', '.join(extra)} | {note}", live)
        else:
            add("fleet", "OK", f"all {len(EXPECTED_TASKS)} expected tasks present in ~/.claude/scheduled-tasks/ | {note}", live)
    except Exception as e:
        add("fleet", "SKIP", f"error: {e}")

# ---- Check 2: SKILL FRONTMATTER ----
def _frontmatter_ok(path):
    # Read enough lines that a long multi-line description's closing fence is in range
    # (avoids false-positiving well-formed skills with verbose trigger descriptions).
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            head = [next(f, "") for _ in range(80)]
    except Exception:
        return None  # unreadable -> skip
    text = "".join(head)
    if "## name:" in text:                        # collapsed-onto-markdown-heading regression (the real failure)
        return False
    if not head or head[0].strip() != "---":      # must open with a YAML fence
        return False
    # closing fence: a line that is exactly '---' after line 0
    closing = any(l.strip() == "---" for l in head[1:])
    has_name = any(re.match(r"\s*name\s*:", l) for l in head)
    has_desc = any(re.match(r"\s*description\s*:", l) for l in head)
    return has_name and has_desc and closing

def check_skills():
    try:
        cli = os.path.join(CLAUDE, "skills", "*", "SKILL.md")
        mirror_root = os.path.join(ROAMING, "local-agent-mode-sessions", "skills-plugin")
        mirror = os.path.join(mirror_root, "**", "SKILL.md")
        cli_hits = set(glob.glob(cli))
        mirror_hits = set(glob.glob(mirror, recursive=True))
        # Transient guard: the Cowork mirror regenerates on app launch; if its dir is present but
        # momentarily empty (mid-sync), do NOT emit a hollow "OK" on just the local skill(s).
        if os.path.isdir(mirror_root) and not mirror_hits:
            add("skill-frontmatter", "SKIP",
                "Cowork skills mirror present but 0 SKILL.md found -- likely mid-sync after app launch; re-run shortly")
            return
        paths = cli_hits | mirror_hits
        if not paths:
            add("skill-frontmatter", "SKIP", "no SKILL.md found")
            return
        bad = sorted({os.path.basename(os.path.dirname(p)) for p in paths if _frontmatter_ok(p) is False})
        if bad:
            add("skill-frontmatter", "CRIT", f"{len(bad)} skill(s) with malformed frontmatter (won't trigger reliably)", bad)
        else:
            add("skill-frontmatter", "OK",
                f"all {len(paths)} SKILL.md parse cleanly ({len(mirror_hits)} Cowork + {len(cli_hits)} local)")
    except Exception as e:
        add("skill-frontmatter", "SKIP", f"error: {e}")

# ---- Check 3: SECRET SCAN ----
SECRET_PATTERNS = [
    re.compile(r"sk-ant-[A-Za-z0-9_\-]{8,}"),
    re.compile(r"\bak_[A-Za-z0-9]{12,}"),
    re.compile(r"x-api-key\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{12,}"),
    re.compile(r"Bearer\s+[A-Za-z0-9_\-\.]{16,}"),
    re.compile(r"(FRED_API_KEY|API_KEY|APIKEY|SECRET|TOKEN)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{12,}"),
]
SECRET_TARGETS = [
    os.path.join(HOME, ".claude.json"),
    os.path.join(ROAMING, "claude_desktop_config.json"),
    os.path.join(CLAUDE, "settings.json"),
    os.path.join(CLAUDE, "backups"),
    os.path.join(CLAUDE, "mcp-servers"),
    os.path.join(ROAMING, "logs"),
]
EXCLUDE_DIR_PARTS = ("_archive", "subagents", "node_modules", "file-history", "tool-results", os.sep + "tasks" + os.sep)

def _iter_files(target):
    if os.path.isfile(target):
        yield target
    elif os.path.isdir(target):
        for root, dirs, files in os.walk(target):
            if any(x in root for x in EXCLUDE_DIR_PARTS):
                continue
            for fn in files:
                yield os.path.join(root, fn)

# claude_desktop_config.json / .claude.json are the LEGITIMATE homes for an MCP key -> not a leak.
# mcp-builder reference docs carry example "x-api-key:" strings -> documentation, not real keys.
LEGIT_KEY_HOMES = {"claude_desktop_config.json", ".claude.json"}
DOC_FALSE_POSITIVE_PARTS = ("mcp-builder", "/reference/", "evaluation.md")

def check_secrets():
    try:
        crit, applog = {}, {}
        scanned = 0
        for tgt in SECRET_TARGETS:
            for fp in _iter_files(tgt):
                low = fp.replace("\\", "/").lower()
                if any(x in low for x in DOC_FALSE_POSITIVE_PARTS):
                    continue  # documentation examples, not real credentials
                try:
                    if os.path.getsize(fp) > 3_000_000:
                        continue
                    with open(fp, encoding="utf-8", errors="ignore") as f:
                        data = f.read()
                except Exception:
                    continue
                scanned += 1
                if any(p.search(data) for p in SECRET_PATTERNS):
                    base = os.path.basename(fp)
                    if base in LEGIT_KEY_HOMES:
                        continue                       # expected key home
                    elif base.endswith(".log"):
                        applog[base] = True            # app's own logs echo the active MCP key by design; local-only, rotate out
                    else:
                        crit[base] = True              # real leak: backup/memory/transcript/etc.
        if crit:
            add("secret-scan", "CRIT",
                f"credential literals in {len(crit)} non-legitimate file(s) of {scanned} scanned -- scrub these + confirm the key is rotated",
                sorted(crit))
        elif applog:
            add("secret-scan", "OK",
                f"no leak outside config; {len(applog)} app log(s) echo the active MCP key by design (expected, local-only, rotate out) of {scanned} scanned",
                sorted(applog))
        else:
            add("secret-scan", "OK", f"no credential literals outside the legitimate config ({scanned} scanned)")
    except Exception as e:
        add("secret-scan", "SKIP", f"error: {e}")

# ---- Check 4: CONNECTOR ALLOWLIST (Outlook-only doctrine) ----
FORBIDDEN_CONNECTORS = ("gmail", "google", "drive")  # Outlook-only doctrine targets Google email/cal/files; Guru/Midpage are non-email and user-retained
def check_connectors():
    try:
        cache = os.path.join(CLAUDE, "mcp-needs-auth-cache.json")
        if not os.path.exists(cache):
            add("connector-allowlist", "SKIP", "mcp-needs-auth-cache.json not found")
            return
        d = json.load(open(cache, encoding="utf-8"))
        bad = [k for k in d.keys() if any(f in k.lower() for f in FORBIDDEN_CONNECTORS)]
        if bad:
            add("connector-allowlist", "WARN",
                f"{len(bad)} non-Outlook connector(s) present (violates Outlook-only doctrine) -- disconnect at claude.ai",
                bad)
        else:
            add("connector-allowlist", "OK", "no forbidden (Gmail/Google/Drive) connectors authed")
    except Exception as e:
        add("connector-allowlist", "SKIP", f"error: {e}")

# ---- Check 5: MEMORY <-> FLEET DRIFT ----
def check_drift():
    try:
        live = len(_live_tasks())
        sor = os.path.join(CLAUDE, "projects",
                           "C--Users-Owner-OneDrive---Oxford-Capital-Partners--1-", "memory",
                           "00_system_of_record.md")
        if not os.path.exists(sor):
            add("memory-fleet-drift", "SKIP", "SoR unavailable")
            return
        txt = open(sor, encoding="utf-8", errors="replace").read()
        claimed = sorted(set(int(m) for m in re.findall(r"(\d{1,3})\s+(?:live )?tasks", txt)))
        if claimed and live not in claimed:
            add("memory-fleet-drift", "WARN",
                f"SoR task-count mentions {claimed} but the live store has {live} -- overwrite SoR section 7",
                [f"live={live}", f"documented={claimed}"])
        else:
            add("memory-fleet-drift", "OK", f"SoR fleet count consistent with live store ({live})")
    except Exception as e:
        add("memory-fleet-drift", "SKIP", f"error: {e}")

def main():
    as_json = "--json" in sys.argv
    strict = "--strict" in sys.argv
    for fn in (check_fleet, check_skills, check_secrets, check_connectors, check_drift):
        try:
            fn()
        except Exception:
            add(getattr(fn, "__name__", "?"), "SKIP", "uncaught: " + traceback.format_exc().splitlines()[-1])

    crit = [r for r in results if r["status"] == "CRIT"]
    warn = [r for r in results if r["status"] == "WARN"]

    if as_json:
        print(json.dumps({"ts": NOW.isoformat(), "results": results,
                          "verdict": "CRITICAL" if crit else ("ATTENTION" if warn else "OK")}, indent=1))
    else:
        print("=" * 70)
        print(f"ORA CLAUDE SETUP SELF-AUDIT  {NOW:%Y-%m-%d %H:%M}Z")
        print("=" * 70)
        icon = {"OK": "[ OK ]", "WARN": "[WARN]", "CRIT": "[CRIT]", "SKIP": "[skip]"}
        for r in results:
            print(f"{icon.get(r['status'],'[?]')} {r['check']}: {r['detail']}")
            for it in r["items"]:
                print(f"          - {it}")
        print("-" * 70)
        print(f"VERDICT: {'CRITICAL' if crit else ('ATTENTION' if warn else 'OK')}  "
              f"({len(crit)} critical, {len(warn)} warn)")

    sys.exit(1 if (strict and crit) else 0)

if __name__ == "__main__":
    main()
