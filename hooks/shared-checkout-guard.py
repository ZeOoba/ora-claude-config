"""Shared-checkout hygiene guard -- PreToolUse hook for Edit|Write|MultiEdit.

WARNS (never blocks) when you edit a file in a shared-checkout repo's MAIN
checkout while that tree is dirty -- i.e., it holds uncommitted/untracked work
that may be another session's WIP. The nudge: claim an isolated worktree and
verify `git status` before committing, so you don't co-mingle another writer's
hunks (the contaminated-checkout hazard). Silent when you are already in a
linked worktree, when the tree is clean, or when the file is outside the shared
repos. Re-arms per repo whenever the repo-wide dirty-file set CHANGES (a
fingerprint of `git status --porcelain`, not just once-ever per session) --
so a second collision after the first warning is no longer silently swallowed.
When another Claude Code session is currently open (per
hooks/lib/session_liveness.py, itself a fail-open enrichment signal), the
warning names it specifically.

PATH-SCOPED (2026-09-10, Gabriel-reported friction). The hygiene nudge used to
report REPO-WIDE dirt regardless of the file being edited -- "the .claude MAIN
checkout has 97 uncommitted change(s) that may be another session's WIP" -- which
in a checkout that is essentially always dirty is a constant, un-actionable
alarm, and which read IDENTICALLY whether or not the file under the cursor was
one of those 97. It now splits on that question, which is the only one that
changes what the reader should do:
  * the edited file IS in the dirty set -> a real co-mingling hazard, said so,
    with attribution narrowed to sessions that touched THAT file;
  * it is NOT -> labelled repo background explicitly, keeping only the commit-
    hygiene half (`git add <path>`, never `git add -A`) that genuinely applies.
Costs no extra git call -- _status_paths() parses the `git status` output the
hook already has. The dedupe fingerprint carries the in/out bit, so moving from a
clean file to a dirty one inside one unchanged dirty set still re-arms.

Membership goes through _dirty_set_covers(), not a bare `in` test against
_status_paths()'s set (independent-review finding, same day): `git status
--porcelain` collapses a whole untracked DIRECTORY into one `?? dir/` line, never
one line per file beneath it, so a file living under such a directory is not
itself a member of that set and a naive test asserted "is NOT among them" for a
file that plainly was uncommitted -- a false assertion in exactly the direction
this change was meant to fix. _dirty_set_covers() additionally matches a target
against any dirty entry that IS a directory on disk.

DELIVERY (fixed 2026-07-16 -- this hook was silently useless to the agent for 7
days). v1 emitted ONLY `systemMessage` + stderr. Per the PreToolUse contract,
`systemMessage` is "shown to the USER" and is NEVER injected into the model's
context; and stderr is fed to Claude ONLY on exit 2 (a block), while this hook
exits 0 by design. Net: from 2026-07-09 it fired correctly ~168 times across
sessions while the agent it exists to steer received nothing. Found 2026-07-16
when a session hit two shared-file collisions in one hour, caught BOTH by manual
mtime inspection, and got no hook warning -- then reproduced it directly (marker
written 20:08:43, zero warning surfaced). Fix: also emit
`hookSpecificOutput.additionalContext`, the only PreToolUse field that is both
model-visible and non-blocking. Verified end-to-end: the warning landed in the
agent's context on the very Edit that applied this fix. Do NOT "simplify" this
back to systemMessage-only.

Why `permissionDecision: "allow"` is SAFE here and does NOT weaken anything
(verified 2026-07-16 against the docs AND empirically -- do not "harden" it away):
  * It cannot grant permission. Per permissions.md: "Hook decisions don't bypass
    permission rules. Claude Code evaluates deny and ask rules regardless of what
    a PreToolUse hook returns: a matching deny rule blocks the call, and a
    matching ask rule still prompts even when the hook returned 'allow'."
  * It does not short-circuit later hooks. All matching PreToolUse hooks run and
    deny wins. Proven live: with this hook (#6 in settings.json) returning "allow",
    registry-write-guard (#7) still blocked a registry write.
  * `permissionDecision` is REQUIRED in hookSpecificOutput -- it cannot be omitted.
    "defer" would be the semantic no-op, but whether additionalContext is still
    delivered under "defer" is UNDOCUMENTED, so "allow" is the supported shape.

SAFETY INVARIANT: warn-only. It NEVER denies a tool call (permissionDecision is
always "allow" -- never "deny"/"ask"), and the whole body is wrapped in
try/except -- on ANY error it prints nothing and exits 0 (ALLOW). A bug here must
never block or slow an edit.

Stdlib only. ASCII-only. Windows (`python`).
"""

import hashlib
import json
import os
import subprocess
import sys
import time

LIB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib")
sys.path.insert(0, LIB_DIR)
# Guarded import (adversarial review, 2026-07-17). This hook is warn-only -- it never
# blocks either way, so an unguarded import crashing here is not a security regression the
# way it was for ora-autonomy-gate.py. But it IS a reliability one: the crash happens at
# MODULE LOAD, before main()'s own try/except (below) or any Edit/Write-specific logic runs,
# so a broken session_liveness.py would traceback on EVERY Edit/Write/MultiEdit/Desktop
# Commander write across every session, not just ones this hook actually has something to
# say about. Same bug class, same fix, applied for reliability rather than security here.
try:
    from session_liveness import other_active_sessions  # noqa: E402,F401
except Exception:
    def other_active_sessions(_session_id):
        return []

# Provenance is what turns "a session is open" into "a session touched THESE files".
# Same guarded-import posture and same reason as above (warn-only hook: a missing
# module must degrade, never traceback on every write). Degrading here costs only
# attribution PRECISION -- _attribute_wip() then reports the WIP as unattributed,
# which is the honest answer when there is no evidence to attribute it with.
try:
    from commit_provenance import TOUCHED_BASENAME, read_touched  # noqa: E402,F401
    from commit_provenance import norm as prov_norm  # noqa: E402,F401
    PROVENANCE_LOADED = True
except Exception:
    PROVENANCE_LOADED = False
    TOUCHED_BASENAME = "touched-files.txt"

    def prov_norm(p):
        return _norm(p)  # resolved at call time; _norm is defined below

    def read_touched(_fh):
        return {}

DEFAULT_REPOS = [
    "C:/Users/Owner/oxford-command-center",
    "C:/Users/Owner/ora-skills",
    "C:/Users/Owner/.claude",
]
DEFAULT_SESSIONS_DIR = "C:/Users/Owner/.claude/hooks/sessions"


def _norm(p):
    return os.path.normcase(os.path.abspath(p))


def shared_repos():
    raw = os.environ.get("SHARED_CHECKOUT_REPOS")
    if raw:
        return [r for r in raw.split(os.pathsep) if r.strip()]
    return DEFAULT_REPOS


def find_repo(file_path, repos):
    fp = _norm(file_path)
    for r in repos:
        rn = _norm(r)
        if fp == rn or fp.startswith(rn + os.sep):
            return r
    return None


def is_linked_worktree(repo):
    # A linked worktree's .git is a FILE (gitdir pointer); a main checkout's is a DIR.
    return os.path.isfile(os.path.join(repo, ".git"))


def nearest_git_root(file_path):
    """The actual checkout that owns `file_path`: the nearest ancestor directory
    (walking upward from its parent) containing a `.git` entry, file or dir.

    BUG FIX (2026-07-24): find_repo() matches a file against a configured shared-repo
    ROOT by plain path-prefix, so a file living inside a LINKED WORKTREE NESTED under
    that root (e.g. a session isolation workspace at
    `<repo>/.claude/worktrees/<name>/...` -- exactly where EnterWorktree/`git worktree
    add` puts one for this very repo) still resolves `repo` to the OUTER shared root.
    The guard then asked "is the OUTER root a linked worktree?" (no -- it's the main
    checkout) and proceeded to warn about the outer checkout's dirty status, even
    though the file being edited sits in an already-isolated nested worktree. Observed
    live: every edit inside `.claude/worktrees/scg-attribution-test/` warned about
    `.claude`'s ~30 unrelated uncommitted changes -- noise at the exact moment the
    advice ("use an isolated worktree") had already been followed.

    Callers check is_linked_worktree()/is_main_checkout() against THIS return value,
    not against find_repo()'s match, so the isolation check reflects the file's real
    checkout rather than whichever configured root happened to prefix-match first.

    Returns None if no `.git` entry is found walking up to the filesystem root (should
    not happen for a path find_repo() already matched, but degrades to None -- callers
    then fall back to the outer repo match, preserving prior behavior instead of
    raising).
    """
    d = os.path.dirname(os.path.abspath(file_path))
    seen = set()
    while d and d not in seen:
        seen.add(d)
        if os.path.exists(os.path.join(d, ".git")):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    return None


def is_main_checkout(repo):
    return os.path.isdir(os.path.join(repo, ".git"))


def git_status_lines(repo):
    # Non-empty `git status --porcelain` lines for repo, or None on ANY
    # error (fail-open -> caller treats None as "nothing to warn about").
    try:
        proc = subprocess.run(
            ["git", "-C", repo, "status", "--porcelain"],
            capture_output=True, text=True, timeout=5,
        )
    except Exception:
        return None
    if proc.returncode != 0:
        return None
    return [ln for ln in proc.stdout.splitlines() if ln.strip()]


def status_fingerprint(lines):
    # Stable hash of the repo-wide dirty-file set, used to re-arm the
    # per-session warning when the dirty set changes (not just once-ever).
    joined = "\n".join(sorted(lines))
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()[:16]


def _status_paths(repo, lines):
    """Absolute, provenance-normalized paths named by `git status --porcelain`.

    Porcelain v1 shape: 2 status chars + space + path. A rename/copy is
    `R  old -> new`; attribute the NEW path, since that is what exists on disk
    now. core.quotePath double-quotes non-ASCII paths, so unquote best-effort.
    Any unparseable line is skipped -- attribution is enrichment and is never
    worth raising inside a warn-only hook.
    """
    out = set()
    for ln in lines:
        if len(ln) < 4:
            continue
        rest = ln[3:].strip()
        if " -> " in rest:
            rest = rest.split(" -> ", 1)[1].strip()
        if len(rest) >= 2 and rest.startswith('"') and rest.endswith('"'):
            try:
                rest = json.loads(rest)
            except Exception:
                rest = rest[1:-1]
        if rest:
            out.add(prov_norm(os.path.join(repo, rest)))
    return out


def _dirty_set_covers(dirty_paths, target):
    """Is `target` (already prov_norm'd) inside `dirty_paths`, INCLUDING when it
    lives under an untracked DIRECTORY that git status collapsed to one entry?

    FIX (2026-09-10, independent review finding on the path-scoping change below):
    `git status --porcelain` reports a whole untracked directory as ONE line --
    `?? newdir/` -- never one line per file beneath it. `_status_paths()` above (and
    prov_norm, which is `normcase(abspath(...))` and does not preserve a trailing
    separator) turns that into a single path indistinguishable from a same-named
    FILE entry. A plain `target in dirty_paths` membership test, reproduced live in
    review, therefore MISSES every file under such a directory and asserts "is NOT
    among them" for a file that plainly is -- a false assertion introduced by this
    same change, in the exact direction it was meant to fix.

    Exact membership first (the common case: file-level porcelain entries), then a
    prefix check ONLY against entries that are actually directories on disk -- so a
    file entry that merely happens to prefix-match another path's name (e.g.
    `a.py` vs `a.py.bak`) is never wrongly treated as a container."""
    if target in dirty_paths:
        return True
    for p in dirty_paths:
        try:
            if os.path.isdir(p) and (target == p or
                                     target.startswith(p + os.sep)):
                return True
        except Exception:
            continue  # a stat failure here is enrichment, not correctness
    return False


def _recent_window_s():
    """How recently another session must have touched a file for it to count as
    'currently working on it'. Default 90 min; env-overridable for tests.

    WHY (2026-07-26, review finding #4): the touched-set is append-only and lives as
    long as the session does (hours), so an unbounded intersection claims a session
    is "already working on" a file it edited and COMMITTED at 09:00 and abandoned.
    _attribute_wip never needed a window because it only ever consulted paths that
    were CURRENTLY DIRTY in git status -- the WIP demonstrably still existed. The
    same-file check deliberately runs on clean repos, which removes that implicit
    bound, so the bound has to become explicit. Same lesson commit-provenance-guard.py
    already recorded when it false-positived on already-committed content."""
    try:
        return float(os.environ.get("SHARED_CHECKOUT_RECENT_WINDOW_S") or 5400.0)
    except Exception:
        return 5400.0


def _sessions_touching(paths, others, sessions_dir, max_age_s=None):
    """[(sid, status)] for live sessions whose RECORDED touched-set intersects
    `paths`. Returns [] when provenance is unavailable or unreadable -- absence
    of evidence, which the caller reports as unattributed rather than guessing.

    `max_age_s` (opt-in) additionally requires the touch to be recent. Callers that
    already have an independent freshness signal -- _attribute_wip, whose paths come
    from live `git status` output -- deliberately pass None and keep the original
    behavior unchanged.
    """
    if not PROVENANCE_LOADED or not paths:
        return []
    now = time.time()
    found = []
    for entry in others:
        sid = (entry or {}).get("sid")
        if not sid:
            continue
        tf = os.path.join(sessions_dir, sid, TOUCHED_BASENAME)
        try:
            if not os.path.isfile(tf):
                continue
            with open(tf, encoding="utf-8") as fh:
                touched = read_touched(fh)
        except Exception:
            continue  # unreadable -> no evidence from this session
        hit = paths & set(touched)
        if not hit:
            continue
        if max_age_s is not None:
            # read_touched maps a path to its latest touch ts, or None when any
            # occurrence lacked a timestamp (old/hand-written format). None means
            # "touch time unknown" -- treat as recent rather than silently dropping
            # a real collision on a formatting technicality.
            try:
                fresh = any((touched.get(p) is None) or (now - touched[p] <= max_age_s)
                            for p in hit)
            except Exception:
                fresh = True
            if not fresh:
                continue
        found.append((sid, entry.get("status") or ""))
    return found


def _claim_renew_after_minutes():
    """How stale (age_minutes) the CALLING session's own claim must be before an
    edit in a claim-relevant repo bumps it. Default 20 -- comfortably under
    claim_work.DEFAULT_TTL_MINUTES (120), so an actively-editing session's claims
    stay well clear of expiry, while still being long enough that this hook (which
    fires on EVERY Edit/Write/MultiEdit) does not rewrite the claim file on nearly
    every call. Env-overridable for tests, same convention as
    SHARED_CHECKOUT_RECENT_WINDOW_S above."""
    try:
        return float(os.environ.get("CLAIM_RENEW_AFTER_MINUTES") or 20.0)
    except Exception:
        return 20.0


def _self_renew_claims(session_id):
    """Bump claimed_at on every LIVE claim `session_id` already holds, as a side
    effect of that session continuing to edit inside a claim-relevant repo.

    WHY (2026-08-04): claim_work.py's `renew` CLI subcommand only helps a claim
    stay accurate if the session remembers to call it -- and the incident that
    motivated building `renew` in the first place was exactly a session NOT
    remembering (see reference_concurrent_session_duplicate_hardening_work.md's
    2026-08-04 entry). This closes that gap without relying on memory: renewing an
    ALREADY-OWNED claim needs no judgment call about whether new work is
    claim-worthy -- the session already made that call once, at initial `claim` --
    which is exactly why this is safe to automate where auto-CLAIMING was not (see
    claim_work.py's own module docstring: "classifying 'non-trivial hook work'
    from a single tool call has too high a false positive/negative rate").

    Rate-limited for free by the claim's own age: only claims already older than
    _claim_renew_after_minutes() get rewritten, and a renewal resets age to ~0 --
    so the age gate itself blocks further writes until the threshold elapses
    again, no separate throttle state needed. This is also why it is correct (not
    merely convenient) to call this unconditionally on every eligible edit rather
    than sampling or debouncing: the vast majority of calls do zero writes.

    Self-contained try/except (unlike the rest of this file's reliance on
    __main__'s single outer wrapper): a bug here must never suppress the
    collision-warning logic that runs AFTER this in main() -- an exception
    escaping to that single outer wrapper would abort the entire hook body, not
    just this best-effort side effect.

    HONEST LIMIT (independent review finding, 2026-08-04): renewal is unconditional
    across ALL of the calling session's live claims, keyed only on session_id -- it
    does not check whether the edit is actually related to the SLUG being renewed.
    A session that claims slug-A, finishes that specific task, and spends the rest
    of a long session editing UNRELATED files elsewhere in the same repo will keep
    re-stamping slug-A's claimed_at anyway, because it is still the same session
    still editing inside a claim-relevant repo. This is a real semantic shift, not
    a bug: `claimed_at`'s age now means "this session last edited somewhere in a
    claim-relevant repo", NOT "this session last worked on THIS slug specifically"
    -- and it means claim_work.py's DEFAULT_TTL_MINUTES (2 hours) no longer reliably
    expires an abandoned-but-unreleased claim for the rest of a long session, which
    is exactly the kind of frozen-but-still-"fresh"-looking claim that misled a
    reader in the incident that motivated building `renew` in the first place (see
    the WHY paragraph above) -- just deferred from ~30 minutes to "until the session
    ends or calls `release`". `claim_work.release_claim()`'s "not required for
    correctness" framing is accordingly weaker while this hook is active: releasing
    a claim once its task is actually done now matters more, not less, than before
    self-renewal existed. Deliberately NOT fixed by scoping renewal to claims whose
    declared `paths` overlap the edited file: most claims never declare `paths` (see
    claim_work.py's own D1 note), and the "banner claim" pattern -- one slug
    covering an evolving stream of related work across a whole repo for an extended
    session -- is the PRIMARY case this feature exists to help, so path-scoping would
    defeat its own purpose for exactly the callers who need it most."""
    try:
        from claim_work import read_active_claims, renew_claim  # noqa: E402
        threshold = _claim_renew_after_minutes()
        for c in read_active_claims():
            if (c.get("session_id") == session_id and
                    c.get("age_minutes", 0.0) >= threshold):
                renew_claim(c["slug"], session_id)
    except Exception:
        pass  # best-effort: a lost renewal costs a future stale-claim misread,
              # not a broken edit -- never let this affect the rest of the hook


def _claims_on(file_path, session_id):
    """Other sessions' LIVE claims that declare `file_path`. Guarded import +
    blanket except: claim_work.py is an optional courtesy module and this guard must
    keep working (and never block an edit) if it is missing, broken, or mid-edit --
    the same fail-open posture as the commit_provenance import above."""
    try:
        from claim_work import claims_touching  # noqa: E402
        return claims_touching([file_path], exclude_session=session_id)
    except Exception:
        return []


def _sanitize_claim_text(text):
    """Collapse claim free-text to one printable line before it becomes
    additionalContext.

    Claim files are world-writable by design (claim_work.py: "NOT a security
    boundary"), and additionalContext is MODEL-visible -- so an unsanitized
    description is a prompt-injection vector. active-work-broadcast.py already
    learned this and sanitizes for the identical reason; this is the second place
    the same untrusted text reaches the model, so it needs the same treatment.
    Deliberately duplicated rather than imported: that module is a SessionStart hook,
    and importing a hook from a hook to share four lines would couple two independent
    fail-open paths."""
    s = str(text or "")
    s = "".join(c if (c.isprintable() and c not in "\r\n\t") else " " for c in s)
    s = " ".join(s.split())
    if len(s) > 200:
        s = s[:200].rstrip() + "...(truncated)"
    return s or "(no description)"


def _same_file_collision(file_path, session_id, get_others, sessions_dir):
    """The SAME-FILE signal: is another live session already working on THIS EXACT
    file? Returns a message, or "" when there is no evidence.

    WHY THIS IS SEPARATE FROM _attribute_wip (2026-07-26): that function answers
    "who else has edits somewhere in this repo's dirty set" -- commit hygiene, over
    the whole `git status` path set. It cannot answer "someone is editing the file
    under my cursor right now", and it is unreachable when the repo is otherwise
    clean because main() early-returns on an empty status. On 2026-07-26 three
    sessions edited one SKILL.md within six minutes and none was warned: two held
    honest claims under DIFFERENT work-type slugs, and the SessionStart-only claim
    broadcast could not reach sessions that were already running.

    Two independent evidence sources, deliberately OR'd:
      * provenance touched-files.txt -- automatic, no discipline required, but
        necessarily written only AFTER the other session's first edit;
      * claim-declared paths -- covers the pre-first-edit window, but only when the
        other session bothered to pass --paths.
    Neither alone closes the window; together they cover it end to end."""
    target = prov_norm(file_path)
    who = []
    # Stable identity of WHO is colliding, independent of volatile presentation
    # (liveness status, wording, ordering). This -- not the rendered message -- is
    # what the dedup marker fingerprints.
    identity = []

    # `get_others` is a thunk, not a list: the liveness read behind it costs ~24 ms
    # and is pointless when provenance never loaded (then _sessions_touching returns
    # [] regardless), so the common no-provenance path must not pay for it.
    if PROVENANCE_LOADED:
        for sid, status in _sessions_touching({target}, get_others(), sessions_dir,
                                              max_age_s=_recent_window_s()):
            # BOTH fields sanitized (2026-07-26, adversarial review finding H1).
            # `status` is verbatim free text out of the fleet-mirror session-state
            # JSON, and `sid` out of the same dict -- files with exactly the trust
            # posture claim files have (plain, user-writable, no ownership check).
            # Neither was sanitized in the first cut, and a crafted `status` landed
            # newlines and fake delimiter tags verbatim in additionalContext.
            # This is a REACHABILITY REGRESSION this change introduced, not an
            # inherited flaw: _attribute_wip has the same raw interpolation but was
            # gated behind repo-dirty AND intersect-the-dirty-set AND changed
            # fingerprint; the same-file check runs on a clean repo and on any file,
            # so it turned a corner case into every Edit in three shared repos.
            # `status` is ALLOWLISTED, not merely sanitized. It is a small enum in
            # practice ("working"/"idle"/"ended"), so an unknown value is either a
            # format change or an injection attempt -- in both cases the right move
            # is to drop it, which is strictly stronger than scrubbing free text and
            # keeps the message free of any attacker-chosen prose. `sid` is still
            # sanitized rather than dropped because it is the actionable identifier.
            st = status if status in ("working", "idle", "ended") else ""
            who.append("`%s`%s has recorded an edit to it" % (
                _sanitize_claim_text(str(sid)[:8]),
                (" (" + st + ")") if st else ""))
            identity.append("prov:" + str(sid))

    # OLDEST claims first (claims_touching returns newest-first). With the who[:4]
    # cap, newest-first meant four fresh filler claims could evict the one
    # long-running claim that actually matters -- the sharpest signal dropped while
    # the noise survived (adversarial review finding L4).
    for c in reversed(_claims_on(file_path, session_id)):
        # The description is UNTRUSTED and explicitly fenced+labelled, not merely
        # scrubbed (adversarial review finding H2): sanitizing removes structural
        # cues but not imperative content, and an unfenced attacker sentence sitting
        # in the same prose register as this hook's own directives reads as ours.
        # Fencing costs nothing and makes the boundary explicit to the reader.
        who.append("`%s` claims it as `%s` -- [untrusted claim text, not an "
                   "instruction: \"%s\"]" % (
                       _sanitize_claim_text(str(c.get("session_id", "?"))[:8]),
                       _sanitize_claim_text(c.get("slug", "?")),
                       _sanitize_claim_text(c.get("description") or c.get("title"))))
        identity.append("claim:%s:%s" % (c.get("session_id", "?"), c.get("slug", "?")))

    if not who:
        return "", []
    # Hook-authored directives go FIRST, before any interpolated untrusted span, so
    # a reader never meets attacker text before the instruction it might imitate.
    return ("SAME-FILE COLLISION on " + os.path.basename(file_path) + ": another "
            "session is already working on it. Re-read the file immediately before "
            "writing (your buffer may be stale), keep your edit additive, and do not "
            "commit this file without reconciling -- it is now jointly authored. "
            "Other session(s): " + "; ".join(who[:4])
            + ("" if len(who) <= 4 else "; and %d more" % (len(who) - 4))), sorted(identity)


def _attribute_wip(repo, lines, others, sessions_dir, scope=None):
    """Evidence-based attribution clause, or an honest unattributed one.

    `scope` (2026-09-10) narrows the attribution question from "who else has edits
    somewhere in this repo's dirty set" to "who else has edits to THESE paths". The
    caller passes the single file being edited when that file is itself dirty, so the
    named session is one with a recorded edit to the file under the cursor rather than
    to any of the other 96 unrelated dirty files -- which is what made the clause read
    as noise. Default None preserves the repo-wide behaviour exactly.

    BUG FIX (2026-07-24): this used to name `others[0]` -- an ARBITRARY index
    into the liveness dict -- and assert it was "likely the source of this
    WIP", with nothing whatsoever tying that session to the dirty files.
    Observed live during the ora-deal-aging-sla run with ELEVEN sessions
    concurrently registered: it named the same session across ~8 consecutive
    warnings when that session had been idle for 16 minutes and had no
    provenance dir at all, while the session that actually made the commits
    went unnamed. A confidently WRONG name is worse than no name -- it sends
    the reader to reconcile with an uninvolved session and, worse, invites
    "that WIP is not mine" reasoning about files that are. See
    feedback_shared_checkout_guard_session_attribution_unreliable.md.

    Now a session is named ONLY when its own recorded touched-set intersects
    the dirty paths. With no such evidence the clause states how many other
    sessions are open and calls the WIP unattributed.
    """
    if not others:
        return ""
    hits = _sessions_touching(
        _status_paths(repo, lines) if scope is None else scope,
        others, sessions_dir)
    where = "in this dirty set" if scope is None else "to it"
    noun = "these files" if scope is None else "this file"
    if hits:
        who = ", ".join(
            "`%s`%s" % (sid[:8], (" (" + st + ")") if st else "")
            for sid, st in hits[:3])
        more = "" if len(hits) <= 3 else " and %d more" % (len(hits) - 3)
        verb = " has" if len(hits) == 1 else " have"
        return (" Session " + who + more + verb + " recorded edit(s) " +
                ("to file(s) " + where if scope is None else where) +
                " -- reconcile with it before committing.")
    return (" " + str(len(others)) + " other session(s) are open, but none has"
            " a recorded edit to " + noun + " -- this WIP is UNATTRIBUTED."
            " Do not assume a specific session; check `git log -1` and"
            " `git status` yourself before committing.")


def main():
    payload = json.loads(sys.stdin.read())
    if not isinstance(payload, dict):
        return

    tool_input = payload.get("tool_input") or {}
    file_path = tool_input.get("file_path")
    if not isinstance(file_path, str) or not file_path:
        return
    session_id = payload.get("session_id")
    if not isinstance(session_id, str) or not session_id:
        session_id = "nosession"

    repo = find_repo(file_path, shared_repos())
    if repo is None:
        return  # fast path: not a shared-checkout repo -> no git call at all

    # Runs BEFORE the worktree-isolation early-return just below, deliberately: an
    # already-isolated linked worktree is the CORRECT, mandated way to do hooks/**
    # work in this codebase, so if self-renewal only ran on the warn path it would
    # almost never fire for a well-behaved session -- precisely backwards. No git
    # call of its own (claim_work.py is plain JSON file I/O), so this does not
    # reintroduce the git-subprocess cost the fast-path return above avoids.
    _self_renew_claims(session_id)

    # Check isolation against the file's OWN checkout, not the matched shared-repo
    # root -- see nearest_git_root()'s docstring. Falls back to `repo` if no `.git`
    # entry is found at all (preserves prior behavior instead of raising).
    own_root = nearest_git_root(file_path) or repo
    if is_linked_worktree(own_root):
        return  # already isolated -- good, stay silent (nested or top-level worktree)
    if not is_main_checkout(repo):
        return  # not a git checkout we recognize -- fail-open

    sessions_dir = os.environ.get("SHARED_CHECKOUT_SESSIONS_DIR") or DEFAULT_SESSIONS_DIR
    sess_dir = os.path.join(sessions_dir, session_id)

    # Memoized + lazy: other_active_sessions() costs ~24 ms (measured 2026-07-26) and
    # this hook is on the Edit/Write hot path. Before the same-file check existed it
    # was reached only on the warn path; computing it eagerly would have made every
    # edit pay for it, including the overwhelmingly common no-collision case.
    _others_cache = []

    def get_others():
        if not _others_cache:
            _others_cache.append(other_active_sessions(session_id))
        return _others_cache[0]

    # ---- SAME-FILE check (2026-07-26) -------------------------------------------
    # Runs BEFORE the clean-status early-return below on purpose: two sessions can
    # collide on one file in a repo whose `git status` is otherwise clean (e.g. both
    # editing a committed spec), and the old ordering made that case structurally
    # unreachable. Its own dedup marker, keyed on the file AND the set of other
    # sessions involved, so it is neither masked by the dirty-set fingerprint marker
    # nor repeated on every keystroke-level edit to the same file.
    same_file, sf_identity = _same_file_collision(
        file_path, session_id, get_others, sessions_dir)
    sf_marker = sf_fp = None
    if same_file:
        sf_key = hashlib.sha256(prov_norm(file_path).encode("utf-8", "replace")).hexdigest()[:16]
        sf_marker = os.path.join(sess_dir, "same-file-warned-" + sf_key)
        # Fingerprint the IDENTITY SET (sorted session ids + claim slugs), NOT the
        # rendered message (review finding #1). The message embeds each other
        # session's liveness `status`, which fleet-session-hook.py flips between
        # "working" and "idle" on every tool use -- so a message fingerprint
        # oscillated and the marker never matched, re-firing the same 400-char
        # warning on nearly every edit. Worst against an ACTIVELY colliding session,
        # i.e. exactly when the reader most needs to still be listening.
        sf_fp = hashlib.sha256(
            "\x1f".join(sf_identity).encode("utf-8", "replace")).hexdigest()[:16]
        prev_sf = None
        try:
            with open(sf_marker, "r", encoding="ascii") as fh:
                prev_sf = fh.read().strip()
        except Exception:
            prev_sf = None
        if prev_sf == sf_fp:
            same_file = ""  # already warned about this exact set of other sessions

    lines = git_status_lines(repo)
    if not lines:
        # Clean repo: nothing to say about co-mingling WIP, but a same-file collision
        # is still worth reporting on its own.
        if same_file:
            _emit(same_file)
            _commit_marker(sess_dir, sf_marker, sf_fp)
        return

    # PATH SCOPING (2026-09-10, Gabriel-reported friction). The nudge below used to
    # report REPO-WIDE dirt on every Edit -- "the .claude MAIN checkout has 97
    # uncommitted change(s) that may be another session's WIP" -- with no regard for
    # whether the file under the cursor was one of them. In a checkout that is
    # essentially always dirty, that is a constant, un-actionable alarm, and it fired
    # identically for the one case that genuinely matters (your file IS someone's
    # uncommitted WIP) and the 99% case that does not. Same git output, no extra
    # subprocess: _status_paths() is pure parsing of `lines`, already in hand.
    target_dirty = _dirty_set_covers(_status_paths(repo, lines), prov_norm(file_path))
    # The dedupe fingerprint has to carry this bit too. Keyed on the dirty SET alone,
    # editing a dirty file right after a clean one -- the transition from background
    # noise to a real collision -- would be suppressed as "already warned", losing the
    # sharper warning to a marker written for the weaker one.
    fp = status_fingerprint(lines) + (":in" if target_dirty else ":out")
    repo_key = os.path.basename(repo.rstrip("/\\")) or "repo"
    marker = os.path.join(sess_dir, "shared-checkout-warned-" + repo_key)

    prev_fp = None
    if os.path.exists(marker):
        try:
            with open(marker, "r", encoding="ascii") as fh:
                prev_fp = fh.read().strip()
        except Exception:
            prev_fp = None
    if prev_fp == fp:
        # Dirty-set unchanged, so the hygiene nudge is redundant -- but a NEW
        # same-file collision must still get through. Before 2026-07-26 there was
        # only one message and one marker, so this early return silently swallowed
        # any newly-detected collision for the rest of the session.
        if same_file:
            _emit(same_file)
            _commit_marker(sess_dir, sf_marker, sf_fp)
        return

    n = len(lines)
    base = os.path.basename(file_path)
    if target_dirty:
        # The file under the cursor IS part of the uncommitted set. Attribution is
        # scoped to that one file, so a named session is one that touched THIS file.
        collision_note = _attribute_wip(repo, lines, get_others(), sessions_dir,
                                        scope={prov_norm(file_path)})
        msg = (
            "Shared-checkout hygiene: " + base + " is ITSELF one of the " + str(n) +
            " uncommitted change(s) in the " + repo_key + " MAIN checkout -- your edit "
            "lands on top of work that is already uncommitted." + collision_note +
            " Re-read the file immediately before writing, keep your edit additive, and "
            "stage only your own hunks (`git add -p`, never `git add -A`). An isolated "
            "worktree (npm run worktree / EnterWorktree) avoids the co-mingling entirely."
        )
    else:
        # Repo background, explicitly labelled as such. Saying so is the point: the
        # previous wording asserted a co-mingling risk this case does not carry, and
        # a warning that cries wolf on every edit stops being read on the edit that
        # matters. The commit-hygiene half is still real -- a blanket `git add -A`
        # here WOULD sweep up the other N files -- so that, and only that, stays.
        collision_note = _attribute_wip(repo, lines, get_others(), sessions_dir)
        msg = (
            "Shared-checkout hygiene: the " + repo_key + " MAIN checkout has " + str(n) +
            " uncommitted change(s), but " + base + " is NOT among them -- this is repo "
            "background, not a collision on your file." + collision_note +
            " Commit only your own paths (`git add <path>`, never `git add -A`); an "
            "isolated worktree (npm run worktree / EnterWorktree) avoids the question."
        )
    # Same-file first: it is the sharper, more actionable signal (a named session on
    # THIS file) and must not be buried under the generic dirty-set nudge.
    if same_file:
        msg = same_file + "\n\n" + msg
    _emit(msg)
    # Both markers committed only after delivery succeeded (see _commit_marker).
    _commit_marker(sess_dir, marker, fp)
    _commit_marker(sess_dir, sf_marker, sf_fp)


def _commit_marker(sess_dir, marker, value):
    """Record 'already warned' -- called ONLY AFTER _emit() has returned.

    Ordering matters (review finding: marker committed before delivery). Writing it
    first made the marker authoritative and the warning best-effort: anything
    between the write and _emit() that raised was swallowed by the top-level
    except, and the collision was then deduped away forever. Demonstrated by
    closing the hook's stdout -- exit 120, marker persisted, warning never
    delivered and never retried. Now 'warned' means 'delivered'."""
    if not marker:
        return
    try:
        os.makedirs(sess_dir, exist_ok=True)
        with open(marker, "w", encoding="ascii") as fh:
            fh.write(value)
    except Exception:
        pass  # best-effort: a lost marker costs a duplicate warning, not a lost one


def _emit(msg):
    # Delivery (fixed 2026-07-16 -- see DELIVERY note in the module docstring):
    #   systemMessage     -> the USER (transcript warning). Never reaches the model.
    #   additionalContext -> CLAUDE. The ONLY PreToolUse field that is both
    #                        model-visible AND decoupled from blocking.
    #   permissionDecision "allow" -> explicit non-block, preserving the warn-only
    #                        SAFETY INVARIANT above (never deny, never ask).
    #   stderr            -> debug log only on exit 0 (PreToolUse feeds stderr to
    #                        Claude ONLY on exit 2, which would block). Kept as a
    #                        breadcrumb, NOT relied on as the delivery channel.
    sys.stdout.write(json.dumps({
        "systemMessage": msg,
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
            "additionalContext": msg,
        },
    }))
    sys.stderr.write(msg + "\n")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass  # fail open: warn-only must never block a tool call
    sys.exit(0)
