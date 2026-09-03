#!/usr/bin/env python3
"""
ORA Claude Setup Self-Audit  (read-only, fail-open)
====================================================
Deterministic daily health scan of the Claude Code + Cowork setup.
Adds the checks the existing probes do NOT cover:
  1. FLEET INTEGRITY    -- registry-derived (2026-07-09): every ENABLED task's SKILL.md
                           filePath resolves, and no live-store folder is registered in
                           NEITHER fleet (disk->registry orphan / dark task -- the one
                           direction no other probe checks).
  2. SKILL FRONTMATTER  -- STRUCTURAL check (deliberately NOT a strict YAML parse; see
                           _frontmatter_ok) for the collapsed-frontmatter regression class
                           across skill roots AND both scheduled-task fleet roots.
  3. SECRET SCAN        -- any live credential literal in config/backups/logs?
  4. CONNECTOR ALLOWLIST-- any non-Outlook (Gmail/Google/Drive) connector re-authed?
  5. MEMORY/FLEET DRIFT -- does SoR section 7 hardcode a task count that contradicts the
                           live registries? (counts belong to the generated roster, not prose)

Companion to (does NOT replace): fleet-status.py, doctrine-integrity-probe.py,
governor-drift-probe.py, memory-integrity-probe.py, eos-telemetry-rollup.py.

Design rules (mirror the EOS reliability spec):
  * READ-ONLY. Never writes, sends, or mutates anything.
  * FAIL-OPEN per check. Any exception in one check -> that check reports SKIP, others continue.
  * Exit 0 always unless --strict and a CRITICAL is found (for an out-of-band dead-man wrapper).
  * stdlib only. No network. Fast (<2s typical).

Usage:  python setup-self-audit.py [--json] [--strict]
"""
import os, sys, json, re, glob, datetime, traceback, subprocess, hashlib

HOME = os.path.expanduser("~")
CLAUDE = os.path.join(HOME, ".claude")
# ADDED 2026-08-15 (Automation Audit R10-1): the canonical skill-source repo.
# check_skill_mirror_drift() below compares its copies against CLAUDE/skills --
# module-level so tests can monkeypatch it independently of CLAUDE.
ORA_SKILLS_DIR = os.path.join(HOME, "ora-skills")
ROAMING = os.path.join(os.environ.get("APPDATA", os.path.join(HOME, "AppData", "Roaming")), "Claude")
NOW = datetime.datetime.now(datetime.timezone.utc)

results = []  # list of dicts: {check, status (OK|WARN|CRIT|SKIP), detail, items[]}

def add(check, status, detail, items=None):
    results.append({"check": check, "status": status, "detail": detail, "items": items or []})

# ---- Check 1: FLEET INTEGRITY (registry-derived, 2026-07-09) ----
# The hand-curated EXPECTED_TASKS baseline (2026-06-09) was RETIRED 2026-07-09: it
# predated the CC->LAMS consolidation and over-reported six migrated/retired tasks as
# MISSING. The expected set now comes from the LIVE registries, discovered via
# _shared/store_discovery.py (same single source as the other probes; roots + floors
# in _shared/scheduler-stores.json). What this check covers that NO other probe does:
# DISK->REGISTRY orphans -- folders in the live store ~/.claude/scheduled-tasks/
# registered in NEITHER fleet (dark task or leftover; the 2026-07-09
# 16-folders-vs-13-registrations drift class). Registry->disk (an ENABLED task whose
# SKILL.md filePath no longer resolves) is CRIT.
NEW_STORE = os.path.join(CLAUDE, "scheduled-tasks")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "_shared"))
try:
    import store_discovery as _sd
except Exception:
    _sd = None  # fail-open: fleet checks SKIP, others continue

def _live_tasks():
    out = []
    if os.path.isdir(NEW_STORE):
        for d in sorted(os.listdir(NEW_STORE)):
            if d.startswith("_"):  # _archive*, _shared
                continue
            if os.path.exists(os.path.join(NEW_STORE, d, "SKILL.md")):
                out.append(d)
    return out

def _registry_tasks():
    """All tasks across BOTH live registries (dual-fleet doctrine 2026-06-10), or
    None when no registry could be discovered/read. Each entry: id, enabled,
    recurring (5-field cron), exists (SKILL.md filePath resolves), fleet."""
    if _sd is None:
        return None
    out, found = [], False
    for label, store in (("cc", "claude-code-sessions"),
                         ("lams", "local-agent-mode-sessions")):
        p = _sd.discover_store(store)
        if not p:
            continue
        try:
            d = json.load(open(p, encoding="utf-8"))
        except Exception:
            continue
        found = True
        for t in d.get("scheduledTasks", []) or []:
            fp = t.get("filePath") or ""
            expr = t.get("cronExpression")
            out.append({"id": t.get("id") or "?",
                        "enabled": bool(t.get("enabled")),
                        "recurring": isinstance(expr, str) and len(expr.split()) == 5,
                        "exists": bool(fp) and os.path.isfile(fp),
                        "fleet": label})
    return out if found else None

def classify_fleet(registry_tasks, disk_folders):
    """Pure. registry_tasks spans BOTH fleets. Returns (broken, orphans):
    broken  = ENABLED registered tasks whose SKILL.md filePath does not resolve;
    orphans = live-store folders registered in NEITHER fleet (union semantics --
    a task correctly living on the other fleet is not an orphan)."""
    ids = {t.get("id") for t in registry_tasks}
    broken = sorted(t.get("id") or "?" for t in registry_tasks
                    if t.get("enabled") and not t.get("exists"))
    orphans = sorted(d for d in disk_folders if d not in ids)
    return broken, orphans

def check_fleet():
    try:
        regs = _registry_tasks()
        if regs is None:
            add("fleet", "SKIP", "no scheduler registry discovered (helper missing or both "
                "stores unreadable) -- registry-membership-probe owns store-absence escalation")
            return
        disk = _live_tasks()
        broken, orphans = classify_fleet(regs, disk)
        n_en = sum(1 for r in regs if r["enabled"])
        base = (f"{len(regs)} registered ({n_en} enabled) across both fleets; "
                f"{len(disk)} folder(s) in the live store")
        if broken:
            add("fleet", "CRIT", f"{base}; ENABLED task(s) whose SKILL.md filePath does "
                f"NOT resolve: {', '.join(broken)}", broken)
        elif orphans:
            add("fleet", "WARN", f"{base}; folder(s) registered in NEITHER fleet (dark "
                f"task or leftover -- register via the supervised MCP flow or archive): "
                f"{', '.join(orphans)}", orphans)
        else:
            add("fleet", "OK", f"{base}; every enabled filePath resolves; no unregistered folders")
    except Exception as e:
        add("fleet", "SKIP", f"error: {e}")

# ---- Check 2: SKILL FRONTMATTER ----
# Collapsed-onto-a-markdown-heading regression (`## name: X description: Y`) -- the real
# failure class this check exists for (7 Cowork skills, fixed 2026-06-07). Anchored to the
# start of a line: a bare `"## name:" in text` substring test false-positives on body prose
# that merely QUOTES the pattern (proven: sched-lams/ora-skill-text-audit documents
# `## name:` inside backticks at line 41 and was scored malformed).
# `##`+ only, never a single `#`: `# name: ...` is a legal YAML comment, not the regression.
COLLAPSED_FM_RE = re.compile(r"^\s{0,3}#{2,6}\s*name\s*:", re.M)

def _frontmatter_ok(path):
    """STRUCTURAL frontmatter check -- deliberately NOT `yaml.safe_load`.

    Verifies only what the harness itself needs to route a skill: an opening `---`
    fence, a closing fence, and `name:` / `description:` keys inside it -- plus the
    absence of the collapsed-heading regression. It does NOT validate YAML.

    This is intentional. The Claude Code frontmatter reader is line-wise/lenient
    ("first colon splits key from value"), so descriptions containing `": "` -- e.g.
    the trailing `[MODEL: <id> | checked YYYY-MM-DD]` convention carried by 44 fleet
    SKILL.md files, and ordinary `Use when the user mentions: ...` trigger lists --
    load correctly here while failing a strict YAML parse (`ScannerError: mapping
    values are not allowed here`). Enforcing strict YAML would flag ~82/110 files that
    the harness reads fine, and would pressure edits to load-bearing routing text.
    Escalate that only if the harness's own reader ever becomes strict.
    """
    # Read enough lines that a long multi-line description's closing fence is in range
    # (avoids false-positiving well-formed skills with verbose trigger descriptions).
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            head = [next(f, "") for _ in range(80)]
    except Exception:
        return None  # unreadable -> skip
    if not head or head[0].strip() != "---":      # must open with a YAML fence
        return False
    # closing fence: the first line that is exactly '---' after line 0
    close = next((i for i, l in enumerate(head[1:], 1) if l.strip() == "---"), None)
    if close is None:
        return False
    block = head[1:close]                         # frontmatter only -- never body prose
    if COLLAPSED_FM_RE.search("".join(block)):
        return False
    has_name = any(re.match(r"\s*name\s*:", l) for l in block)
    has_desc = any(re.match(r"\s*description\s*:", l) for l in block)
    return has_name and has_desc

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
        # Both scheduled-task fleet roots (2026-07-24): 53 fleet SKILL.md files were outside
        # the scan set entirely, so the old "all 57 SKILL.md" line silently excluded them.
        # Fleet tasks launch by registry filePath, not by description-routing, but a collapsed
        # frontmatter there is still the corruption signal the 2026-07-08 deletion incident hit.
        sched_hits = set()
        if _sd is not None:
            for label in ("cc", "lams"):
                try:
                    root = _sd.skill_folder_root(label)
                except Exception:
                    continue
                if root:
                    sched_hits |= set(glob.glob(os.path.join(root, "*", "SKILL.md")))
        paths = cli_hits | mirror_hits | sched_hits
        if not paths:
            add("skill-frontmatter", "SKIP", "no SKILL.md found")
            return
        bad = sorted({os.path.basename(os.path.dirname(p)) for p in paths if _frontmatter_ok(p) is False})
        census = (f"{len(mirror_hits)} Cowork + {len(cli_hits)} local + {len(sched_hits)} fleet"
                  + ("" if _sd is not None else "; fleet roots UNSCANNED -- store_discovery unavailable"))
        if bad:
            add("skill-frontmatter", "CRIT", f"{len(bad)} skill(s) with malformed frontmatter (won't trigger reliably)", bad)
        else:
            # Say what was actually verified. This is a structural check, not a YAML parse --
            # see _frontmatter_ok. Do NOT restore the old "parse cleanly" wording.
            add("skill-frontmatter", "OK",
                f"{len(paths)} SKILL.md structurally sound -- fence + name/description present, "
                f"no collapsed-heading regression ({census}); not a strict YAML parse")
    except Exception as e:
        add("skill-frontmatter", "SKIP", f"error: {e}")

# ---- Check 2b: SKILL MIRROR CONTENT DRIFT (2026-08-15, Automation Audit R10-1) ----
# check_skills() above validates frontmatter STRUCTURE across every mirror; it never
# compares CONTENT between the canonical ~/ora-skills copy and the local
# ~/.claude/skills copy of the SAME skill. R10-1: a scheduled ora-setup-audit run
# resolved to a stale local mirror (v1.2) instead of the canonical repo (v1.3) --
# the mirror was simply never re-synced after the repo moved on. Only a handful of
# skills are locally mirrored at all (most live in ~/ora-skills only, or the store
# only); this flags exactly the case where a skill exists in BOTH places and they
# have gone out of sync, which is the one shape that can silently execute stale logic.
def _skill_md5(path):
    try:
        with open(path, "rb") as f:
            return hashlib.md5(f.read()).hexdigest()
    except Exception:
        return None


def find_skill_mirror_drift(repo_skills_dir, local_skills_dir):
    """Pure filesystem read, no module globals: skill names whose SKILL.md exists
    under BOTH repo_skills_dir and local_skills_dir with DIFFERENT byte content.
    A skill present in only one location is not drift -- that is the normal case
    for the vast majority of skills and carries no divergence risk."""
    try:
        repo_names = set(os.listdir(repo_skills_dir)) if os.path.isdir(repo_skills_dir) else set()
    except Exception:
        repo_names = set()
    try:
        local_names = set(os.listdir(local_skills_dir)) if os.path.isdir(local_skills_dir) else set()
    except Exception:
        local_names = set()
    drift = []
    for name in sorted(repo_names & local_names):
        rp = os.path.join(repo_skills_dir, name, "SKILL.md")
        lp = os.path.join(local_skills_dir, name, "SKILL.md")
        if not (os.path.isfile(rp) and os.path.isfile(lp)):
            continue
        rh, lh = _skill_md5(rp), _skill_md5(lp)
        if rh is not None and lh is not None and rh != lh:
            drift.append(name)
    return drift


def check_skill_mirror_drift():
    try:
        repo_skills = ORA_SKILLS_DIR
        local_skills = os.path.join(CLAUDE, "skills")
        if not os.path.isdir(repo_skills):
            add("skill-mirror-drift", "SKIP", f"ora-skills repo not found at {repo_skills}")
            return
        if not os.path.isdir(local_skills):
            add("skill-mirror-drift", "SKIP", "no local ~/.claude/skills dir")
            return
        drift = find_skill_mirror_drift(repo_skills, local_skills)
        if drift:
            add("skill-mirror-drift", "WARN",
                f"{len(drift)} skill(s) mirrored in BOTH ~/ora-skills and ~/.claude/skills "
                f"have DIVERGED content -- a scheduled run can resolve to the stale local "
                f"copy (Automation Audit R10-1 defect class, 2026-08-14/15): "
                f"{', '.join(drift)}", drift)
        else:
            add("skill-mirror-drift", "OK",
                "no repo<->local ~/.claude/skills mirror content divergence")
    except Exception as e:
        add("skill-mirror-drift", "SKIP", f"error: {e}")

# ---- Check 3: SECRET SCAN ----
# Patterns now come from hooks/lib/secret_patterns.py -- ONE source shared with the pre-push
# gate and scrub-before-optin (Gabriel ruling 2026-07-24). The 5 patterns previously inlined
# here and the 8 in scrub-before-optin had already diverged, with NEITHER a superset of the
# other; the shared module is their union. Fail-open (this probe is advisory, unlike the
# pre-push gate which fails closed): if the module is unreachable the check reports SKIP.
# Resolved from THIS file's location, not from CLAUDE: the probe must scan with the pattern
# set from its own checkout. A worktree copy importing the live tree's module would test
# something other than what it is about to land.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO_ROOT, "hooks", "lib"))
try:
    import secret_patterns as _secrets
except Exception:
    _secrets = None

SECRET_TARGETS = [
    os.path.join(HOME, ".claude.json"),
    os.path.join(ROAMING, "claude_desktop_config.json"),
    os.path.join(CLAUDE, "settings.json"),
    os.path.join(CLAUDE, "backups"),
    os.path.join(CLAUDE, "mcp-servers"),
    os.path.join(ROAMING, "logs"),
]
# `_archive` REMOVED from the exclusions 2026-07-24 (Gabriel ruling). A credential does not
# become safe by being archived, and archives are exactly where a rotated-away key lingers.
# The other entries stay: they are transient/regenerable app state (session transcripts,
# tool results), not a place a durable credential lives.
EXCLUDE_DIR_PARTS = ("subagents", "node_modules", "file-history", "tool-results", os.sep + "tasks" + os.sep)


def _tracked_files():
    """Every git-tracked file under ~/.claude -- i.e. exactly what gets PUSHED to
    ZeOoba/ora-claude-config.

    Added 2026-07-24 to fix an inversion: the scan's original six targets were almost
    entirely artifacts that never leave the machine (backups/ has 0 tracked files, logs/
    is local), while the 292+ tracked files that ARE pushed -- memory/, scheduled-tasks/,
    workflows/, prompts/ -- had no scheduled credential scan at all. Derived from
    `git ls-files` rather than a hardcoded directory list so it cannot drift as dirs are
    opted into tracking. Fail-open: no git, no repo, or any error -> empty list.
    """
    try:
        p = subprocess.run(["git", "-C", _REPO_ROOT, "ls-files"],
                           capture_output=True, text=True, timeout=30)
        if p.returncode != 0:
            return []
        return [os.path.join(_REPO_ROOT, rel.replace("/", os.sep))
                for rel in p.stdout.splitlines() if rel.strip()]
    except Exception:
        return []

def _iter_files(target):
    if os.path.isfile(target):
        yield target
    elif os.path.isdir(target):
        for root, dirs, files in os.walk(target):
            if any(x in root for x in EXCLUDE_DIR_PARTS):
                continue
            for fn in files:
                yield os.path.join(root, fn)


def _iter_targets():
    for tgt in SECRET_TARGETS:
        for fp in _iter_files(tgt):
            yield fp

# claude_desktop_config.json / .claude.json are the LEGITIMATE homes for an MCP key -> not a leak.
# mcp-builder reference docs carry example "x-api-key:" strings -> documentation, not real keys.
LEGIT_KEY_HOMES = {"claude_desktop_config.json", ".claude.json"}
DOC_FALSE_POSITIVE_PARTS = ("mcp-builder", "/reference/", "evaluation.md")

def check_secrets():
    try:
        if _secrets is None:
            add("secret-scan", "SKIP",
                "hooks/lib/secret_patterns.py unreachable -- no patterns to scan with")
            return
        crit, applog = {}, {}
        scanned = 0
        seen = set()
        # Local artifacts (never pushed) + the git-tracked set (what IS pushed).
        for fp in list(_iter_targets()) + _tracked_files():
            key = os.path.normcase(os.path.abspath(fp))
            if key in seen:
                continue                               # tracked set overlaps mcp-servers/
            seen.add(key)
            low = fp.replace("\\", "/").lower()
            if any(x in low for x in DOC_FALSE_POSITIVE_PARTS) or _secrets.is_exempt_path(fp):
                continue  # documentation examples and test fixtures, not real credentials
            try:
                if os.path.getsize(fp) > 3_000_000:
                    continue
                with open(fp, encoding="utf-8", errors="ignore") as f:
                    data = f.read()
            except Exception:
                continue
            scanned += 1
            if _secrets.scan_text(data):
                base = os.path.basename(fp)
                if base in _secrets.LEGIT_KEY_HOMES:
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

# ---- Check 5: MEMORY <-> FLEET DRIFT (registry-derived, SoR-section-7-scoped 2026-07-09) ----
# Fleet counts in SoR prose were the recurring drift class (three stale "14-task
# baseline" copies found 2026-07-09). Section 7 should carry NO hardcoded count --
# the roster is GENERATED into session-context.md daily. This check guards that a
# hardcoded count does not creep back in; historical sections elsewhere in the SoR
# legitimately state old counts and are ignored.
def fleet_count_claims(txt):
    """Task-count claims scoped to the SoR '## 7.' HEADLINE area (pure): stops at
    the first subsection ('###') or next section -- dated historical subsections
    inside section 7 legitimately state old counts. Catches plural, singular, and
    hyphenated forms ('19 live tasks', '14-task baseline' -- the original drift
    phrasing). Sorted ints."""
    m = re.search(r"^## 7\..*?(?=^###? |\Z)", txt, re.M | re.S)
    if not m:
        return []
    return sorted(set(int(x) for x in
                      re.findall(r"(\d{1,3})[\s-]+(?:live[\s-]+)?tasks?\b", m.group(0))))

def check_drift():
    try:
        regs = _registry_tasks()
        if regs is None:
            add("memory-fleet-drift", "SKIP", "no scheduler registry discovered")
            return
        sor = os.path.join(CLAUDE, "projects",
                           "C--Users-Owner-OneDrive---Oxford-Capital-Partners", "memory",
                           "00_system_of_record.md")
        if not os.path.exists(sor):
            add("memory-fleet-drift", "SKIP", "SoR unavailable")
            return
        txt = open(sor, encoding="utf-8", errors="replace").read()
        claimed = fleet_count_claims(txt)
        by = {}
        for r in regs:
            f = by.setdefault(r["fleet"], {"enabled": 0, "recurring": 0})
            if r["enabled"]:
                f["enabled"] += 1
                if r["recurring"]:
                    f["recurring"] += 1
        cc, lams = by.get("cc", {}), by.get("lams", {})
        acceptable = {v for f in (cc, lams) for v in f.values()} | \
                     {cc.get(k, 0) + lams.get(k, 0) for k in ("enabled", "recurring")}
        stale = [c for c in claimed if c not in acceptable]
        live = (f"cc={cc.get('enabled', 0)} enabled ({cc.get('recurring', 0)} recurring), "
                f"lams={lams.get('enabled', 0)} enabled ({lams.get('recurring', 0)} recurring)")
        if stale:
            add("memory-fleet-drift", "WARN",
                f"SoR section 7 hardcodes task count(s) {stale} but live registries have {live} "
                "-- de-hardcode section 7 (counts belong to the generated roster in session-context.md)",
                [f"stale={stale}", f"live: {live}"])
        else:
            add("memory-fleet-drift", "OK",
                f"SoR section 7 carries no stale fleet count (live: {live})")
    except Exception as e:
        add("memory-fleet-drift", "SKIP", f"error: {e}")

# ---- Check 6: PRE-PUSH SHIM PRESENCE (2026-07-29, Phase-5 blueprint) ----
# ~/.claude/.git/hooks/pre-push is deliberately NOT version-controlled (git drops it on
# a fresh clone), yet it is the ONLY thing that chains all three push gates (doctrine
# drift, hook-test suite, fail-closed confidential scan). A missing/gutted shim means
# every push silently skips all three -- the audit's #1 single-point-of-failure finding.
def check_prepush_shim():
    shim = os.path.join(CLAUDE, ".git", "hooks", "pre-push")
    if not os.path.isfile(shim):
        add("prepush-shim", "CRIT",
            "pre-push shim MISSING -- all 3 push gates (doctrine/tests/confidential) are "
            "silently OFF; reinstall per docs/MIGRATION_RUNBOOK.md")
        return
    try:
        txt = open(shim, encoding="utf-8", errors="replace").read()
    except Exception as e:
        add("prepush-shim", "WARN", "shim unreadable: %s" % e)
        return
    missing = [g for g in ("git-prepush-doctrine-gate.py", "git-prepush-hook-tests-gate.py",
                           "git-prepush-confidential-scan.py") if g not in txt]
    if missing:
        add("prepush-shim", "CRIT", "shim present but does NOT chain: %s" % ", ".join(missing))
    else:
        add("prepush-shim", "OK", "shim chains all 3 gates")

# ---- Check 7: WINDOWS-TASK BACKBONE (2026-07-29; ROSTER-DRIVEN since 2026-09-03) ----
# The app-independent automation layer. The expected set is no longer a hardcoded dict:
# it is the <!--BEGIN/END-WINDOWS-TASK-ROSTER--> block in memory/tech.md section 3h,
# shared with the automation-health-monitor skill so the two readers cannot disagree.
# Grammar: - <TaskName> | state=active|retired | crit=yes|no | exit1-ok=yes|no [| since= | superseded-by= | note=]
#   active  -> MISSING or Disabled is a finding (CRIT when crit=yes, else WARN); bad last result WARN.
#   retired -> Disabled/MISSING is EXPECTED (never a finding); Ready/Running is a WARN
#              (documented-retired-but-alive). Automation Audit Rev 21 (2026-09-02) mis-read
#              `ORA PM Crons` Disabled/0x8007042B as a 17-day-dead scheduling path because the
#              old dict here said CRIT and knew nothing about deliberate retirement.
#   exit1-ok=yes -> the task's own script exits 1 BY DESIGN ("alert posted"); not a WARN.
# Any live ORA* task with no roster line is WARN (untracked). The roster is a baseline, never a
# filter: the live query always enumerates ORA* in full, plus rostered non-ORA* names by name.
WINDOWS_ROSTER = os.path.join(CLAUDE, "projects", "C--Users-Owner-OneDrive---Oxford-Capital-Partners",
                              "memory", "tech.md")
WINDOWS_ROSTER_BEGIN = "<!--BEGIN-WINDOWS-TASK-ROSTER-->"
WINDOWS_ROSTER_END = "<!--END-WINDOWS-TASK-ROSTER-->"
WINDOWS_RESULT_OK = ("0", "267009", "267011", "")   # success / SCHED_S_TASK_RUNNING / never ran
WINDOWS_RESULT_DECODE = {
    "2147943467": "0x8007042B stopped by a Task Scheduler stop-condition",
    "2147946720": "0x800710E0 operator/administrator refused the request (a task condition -- AC/idle/StartWhenAvailable -- was unmet)",
    "3221225786": "0xC000013A STATUS_CONTROL_C_EXIT (killed mid-run, e.g. shutdown)",
    "267014": "0x41306 terminated by the user",
}

def parse_windows_roster(text):
    """[(name, fields)] from the marker block. Raises ValueError on a malformed block/line."""
    b = text.find(WINDOWS_ROSTER_BEGIN)
    e = text.find(WINDOWS_ROSTER_END, b + 1) if b != -1 else -1
    if b == -1 or e == -1:
        raise ValueError("WINDOWS-TASK-ROSTER markers not found")
    block = re.sub(r"<!--.*?-->", "", text[b + len(WINDOWS_ROSTER_BEGIN):e], flags=re.S)  # comments are prose, never tasks
    entries = []
    for raw in block.splitlines():
        line = raw.strip()
        if not line.startswith("- "):
            continue
        parts = [x.strip() for x in line[2:].split("|")]
        name, fields = parts[0], {}
        for part in parts[1:]:
            if "=" not in part:
                raise ValueError("roster line malformed (field without '='): %r" % line)
            k, v = part.split("=", 1)
            fields[k.strip().lower()] = v.strip()
        if not name or fields.get("state") not in ("active", "retired"):
            raise ValueError("roster line malformed (need name and state=active|retired): %r" % line)
        entries.append((name, fields))
    if not entries:
        raise ValueError("roster block has no task lines")
    return entries

def _decode_windows_result(code):
    if code in WINDOWS_RESULT_DECODE:
        return WINDOWS_RESULT_DECODE[code]
    return ("0x%X" % int(code)) if code.isdigit() else code

def classify_windows_tasks(entries, live):
    """Pure. entries = parse_windows_roster() output; live = {name: (state, last_result)} for
    every task the live query returned (a name absent from `live` == task not present).
    Returns (status, detail, items)."""
    crit, warn, ok = [], [], []
    rostered = set()
    for name, f in entries:
        rostered.add(name)
        is_crit = f.get("crit", "no") == "yes"
        exit1_ok = f.get("exit1-ok", "no") == "yes"
        row = live.get(name)
        state = row[0] if row else None
        result = (row[1] if row else "").strip()
        if f["state"] == "retired":
            tag = "retired since %s, superseded by %s" % (f.get("since", "?"), f.get("superseded-by", "?"))
            if row is None or state == "Disabled":
                ok.append("%s (%s -- %s as expected)" % (name, tag, "absent" if row is None else "Disabled"))
            else:
                warn.append("%s is %s but rostered RETIRED (%s) -- documented-retired-but-alive; "
                            "disable it or update the roster" % (name, state, tag))
            continue
        if row is None:
            (crit if is_crit else warn).append("%s MISSING (re-register per its script header)" % name)
        elif state == "Disabled":
            (crit if is_crit else warn).append("%s is Disabled but rostered active (mark it retired in the roster if deliberate)" % name)
        elif result not in WINDOWS_RESULT_OK and not (exit1_ok and result == "1"):
            warn.append("%s last result %s" % (name, _decode_windows_result(result)))
        else:
            ok.append(name)
    for name in sorted(live):
        if name not in rostered:
            warn.append("%s is live but has no line in the tech.md 3h WINDOWS-TASK-ROSTER -- "
                        "untracked off-fleet automation; add a roster line" % name)
    n_active = sum(1 for _, f in entries if f["state"] == "active")
    n_retired = len(entries) - n_active
    if crit:
        return "CRIT", "; ".join(crit + warn), []
    if warn:
        return "WARN", "; ".join(warn), []
    return ("OK", "all %d active backbone tasks present/enabled with clean results; "
                  "%d retired task(s) in expected state" % (n_active, n_retired), [])

def check_windows_tasks():
    try:
        entries = parse_windows_roster(open(WINDOWS_ROSTER, encoding="utf-8", errors="replace").read())
    except Exception as e:
        add("windows-tasks", "SKIP", "roster unreadable (%s) -- could NOT look, not 'clean': %s" % (WINDOWS_ROSTER, e))
        return
    extra = [n for n, _ in entries if not n.upper().startswith("ORA")]
    ps_names = ",".join("'%s'" % n.replace("'", "''") for n in extra)
    ps = ("$ErrorActionPreference='SilentlyContinue'; $seen=@{}; "
          "foreach($t in @(Get-ScheduledTask -TaskName 'ORA*')){ if($t){ $i=$t|Get-ScheduledTaskInfo; "
          "Write-Output ($t.TaskName+'|'+$t.State+'|'+$i.LastTaskResult); $seen[$t.TaskName]=1 } }; "
          "foreach($n in @(%s)){ if(-not $seen[$n]){ $t=Get-ScheduledTask -TaskName $n; if($t){ $i=$t|Get-ScheduledTaskInfo; "
          "Write-Output ($t.TaskName+'|'+$t.State+'|'+$i.LastTaskResult) } } }" % ps_names)
    try:
        r = subprocess.run(["powershell.exe", "-NoProfile", "-Command", ps],
                           capture_output=True, text=True, timeout=90,
                           encoding="utf-8", errors="replace")
        live = {}
        for ln in (r.stdout or "").splitlines():
            parts = ln.strip().split("|")
            if len(parts) == 3 and parts[0]:
                live[parts[0]] = (parts[1].strip(), parts[2].strip())
    except Exception as e:
        add("windows-tasks", "SKIP", "query failed: %s" % e)
        return
    if not live:
        add("windows-tasks", "SKIP", "live query returned no tasks at all -- could NOT look "
                                     "(Get-ScheduledTask unavailable?), not 'all missing'")
        return
    status, detail, items = classify_windows_tasks(entries, live)
    add("windows-tasks", status, detail, items)

# ---- Check 8: SKILL-OVERRIDE EFFICACY (2026-08-05) ----
# Root cause: the harness short-circuits `if (e.type!=="prompt" || e.source==="plugin")
# return "on";` BEFORE consulting skillOverrides, so an override on a plugin-sourced
# skill is silently ignored -- the skill stays fully listed and model-invocable. Live
# 2026-08-05: 38 of 55 override entries were plugin-namespaced and doing nothing; the
# skills they named were all still in the session listing. Two prior setup audits missed
# it because nothing ever compared the override keys against a live skill listing.
# Verdict logic + the failure-class notes live in skill-override-efficacy-probe.py
# (its own unit tests: test-skill-override-efficacy-probe.py) -- ONE home, not two.
def check_skill_overrides():
    try:
        import importlib.util
        p = os.path.join(CLAUDE, "maintenance", "skill-override-efficacy-probe.py")
        if not os.path.exists(p):
            add("skill-override-efficacy", "SKIP", "probe not found: %s" % p)
            return
        spec = importlib.util.spec_from_file_location("_soep", p)
        soep = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(soep)
        s = soep.summarize(soep.load_overrides(), soep.load_user_skills())
        items = ["%s = %s  [%s]" % (f["key"], f["value"], f["verdict"])
                 for f in s["findings"] if f["verdict"] != "EFFECTIVE"]
        add("skill-override-efficacy", s["status"], s["detail"], items)
    except Exception as e:
        add("skill-override-efficacy", "SKIP", "error: %s" % e)

def main():
    as_json = "--json" in sys.argv
    strict = "--strict" in sys.argv
    for fn in (check_fleet, check_skills, check_skill_mirror_drift, check_secrets,
               check_connectors, check_drift, check_prepush_shim, check_windows_tasks,
               check_skill_overrides):
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
