#!/usr/bin/env python3
"""ORA confidentiality EGRESS guard (PreToolUse). FAIL-CLOSED.

Blocks confidential deal identifiers (every active deal defined in
confidential-terms.json) from crossing any EXTERNAL egress boundary:

  * public website repo writes        (oxford-site / oxfordra.net / website-canonical)
  * mirror / build output             (.../dist/, paths containing 'mirror')
  * /outputs/ artifacts               (.pptx .docx .pdf .html .htm .csv)
  * Notion create/update tool calls   (mcp__*notion-(create|update|append|duplicate|move|comment)*)
  * Outlook send/draft/forward calls  (mcp__*OUTLOOK_(SEND|CREATE_DRAFT|SEND_DRAFT|FORWARD|REPLY)*)
  * egress shell commands             (git push / curl / wget / scp / rsync-remote / Invoke-WebRequest)

The deal legitimately exists INSIDE the brain, so INTERNAL reads/writes/commands are
allowed -- only egress is blocked. This is the whole point: confidentiality is an
egress property, not a content property.

FAIL-CLOSED (inverts the prior fail-open guard, for egress only): if the tool call is an
egress surface (or an egress-capable tool we cannot parse), and we cannot prove it is
clean, we BLOCK. Terms-file unreadable -> BLOCK. Payload unparseable -> BLOCK.

Coverage note (I5 -- no silent half-coverage): a `git push` payload does not contain the
repo contents, so this hook scans only the command text. Deep confidential-content
checking of what a push would publish is enforced by the build-time grep gate on the
mirror/site `dist/` (Phase 2/6), not here.

Roster-freshness tripwire (2026-07-08 audit finding): FAIL-CLOSED covers the roster being
ABSENT/unreadable, but NOT the roster being STALE-BUT-PRESENT -- the file parses fine, yet nobody
has re-confirmed the active-deal list lately (a closed deal never retired, or a NEW confidential
deal not yet added). The second case is INVISIBLE to fail-closed: there are no terms to match, so
the deal leaks. A stale `_meta.roster_last_verified` (> STALENESS_THRESHOLD_DAYS old) therefore
makes the guard surface a loud, one-time-per-session ADVISORY (plus a durable state breadcrumb)
instead of trusting the snapshot silently -- per Invariant 3 ("verify before naming any deal
externally -- if unverifiable, ask"). Staleness WARNS, it does NOT hard-block: the roster is
present, only possibly-incomplete, and freezing all egress forever would be disproportionate. Only
the no-hit clean-egress path (the exact path a missing deal would slip through) carries the advisory.

Exit 0 = allow. Exit 2 = block (PreToolUse convention). The stale-roster advisory rides on the
allow path (exit 0 + stderr) -- it never flips an allow into a block or vice-versa.

Linked worktrees: hooks/confidential-terms.json is gitignored, so `git worktree add` never
checks it out into a fresh linked worktree. load_terms() falls back to the MAIN worktree's
copy (resolved via `git rev-parse --git-common-dir`, shared by every worktree of the same
repo) when this checkout's own copy is missing or unreadable and no explicit
CONFIDENTIAL_TERMS_FILE_OVERRIDE is set. Still fail-closed if the file is unreadable in BOTH
places (2026-07-12, mirrors the same fix in git-prepush-confidential-scan.py).
"""
import sys, os, json, re, datetime, subprocess

HOOK_DIR = os.path.dirname(os.path.abspath(__file__))
LIB_DIR = os.path.join(HOOK_DIR, "lib")
sys.path.insert(0, LIB_DIR)
try:
    from site_markers import SITE_PATH_MARKERS, SITE_DOMAIN_MARKERS  # noqa: E402
    SITE_MARKERS = SITE_PATH_MARKERS + SITE_DOMAIN_MARKERS
except Exception:
    # This hook is FAIL-CLOSED (see module docstring) -- an import failure must
    # never silently degrade it to fail-open. Fallback matches site_markers.py's
    # current combined value, so a missing/broken shared module keeps this guard
    # functioning at its last-known-good marker set instead of crashing past the
    # module-level import (which would exit 1 = non-blocking = a leak).
    SITE_MARKERS = ("oxford-site", "oxfordra.net", "oxfordra_net", "website-canonical")
# Test-only override (2026-07-09), same pattern as shared-checkout-guard.py's
# SHARED_CHECKOUT_REPOS env var: unset in every real session, so production behavior is
# byte-identical. Lets test-confidentiality-guard.py point this subprocess at a synthetic
# terms file when the live roster has zero active deals, without touching the real one.
TERMS_FILE_OVERRIDE = os.environ.get("CONFIDENTIAL_TERMS_FILE_OVERRIDE")
TERMS_FILE = TERMS_FILE_OVERRIDE or os.path.join(HOOK_DIR, "confidential-terms.json")

ARTIFACT_EXT = (".pptx", ".docx", ".pdf", ".html", ".htm", ".csv")
BUILD_MARKERS = ("/dist/", "\\dist\\", "/outputs/", "\\outputs\\", "mirror")

NOTION_WRITE = re.compile(r"notion[-_]?(create|update|append|duplicate|move|comment)", re.I)
OUTLOOK_SEND = re.compile(r"outlook_(send|create_draft|send_draft|forward|reply)", re.I)
EGRESS_BASH = re.compile(
    r"\bgit\s+push\b|\bcurl\b|\bwget\b|\bscp\b|\brsync\b\s+\S+::|"
    r"invoke-webrequest|invoke-restmethod|\bnetlify\b.*\bdeploy\b|\bwrangler\b.*\b(deploy|publish)\b|"
    r"send-via-outlook\.ps1",  # the SOLE live COM send path IS egress (review finding 2026-06-11)
    re.I,
)


# --- Roster-freshness tripwire ------------------------------------------------------------------
# WHY (2026-07-08 audit finding): Invariant 3's self-heal ("if confidential-deal state is
# unavailable ... verify ... if unverifiable, ask") fires ONLY on the roster being ABSENT/unreadable
# -- the load_terms() except-branch in main(). It is BLIND to the roster being STALE-BUT-PRESENT:
# the file parses fine, but nobody has re-confirmed the deal LIST lately. Two drift shapes:
#   * a deal quietly closed and was never retired  -> the guard over-blocks (annoying, but SAFE); OR
#   * a NEW confidential deal should have been added and wasn't -> the guard UNDER-blocks: the deal
#     leaks because there are no terms to match it. This second shape is the dangerous one, and it
#     is EXACTLY what fail-closed cannot catch (fail-closed needs terms present; here there are none).
# So we anchor freshness on `_meta.roster_last_verified` (ISO date) and trip when it ages out.
#
# ROSTER-LEVEL (in `_meta`), NOT per-deal, BY DESIGN: a per-deal "verified" date can only attest to
# deals ALREADY in the file -- it structurally cannot flag a deal that SHOULD exist but is missing
# (the dangerous under-block case). Only a whole-roster "the list was confirmed current on <date>"
# field catches that, so the anchor is roster-wide -- matching how the list is actually reviewed
# (see `_meta.review_cadence`).
#
# THRESHOLD 30 days: the file's own `_meta.review_cadence` ("quarterly", ~90d) is the FORMAL deep
# review; this is a lighter "is the list still current?" tripwire that catches quiet drift ~2 months
# before the quarterly review would. Deliberately tighter than the formal cadence: a leaked
# confidential deal is unrecoverable, a re-verify prompt is cheap -- asymmetric cost, so err early.
STALENESS_THRESHOLD_DAYS = 30
STATE_DIR = os.path.join(HOOK_DIR, "state")            # gitignored transient runtime state (.gitignore §3)
STALE_STATE_FILE = os.path.join(STATE_DIR, "roster-staleness.json")


def block(reason):
    sys.stderr.write("BLOCKED (confidentiality, fail-closed): %s\n" % reason)
    sys.exit(2)


def _read_stdin_text():
    """Decode stdin explicitly as UTF-8, off the raw buffer -- never trust
    sys.stdin's own text-mode encoding. A hook spawned directly by the
    harness (as opposed to a POSIX-locale shell) can get sys.stdin.encoding
    resolved to the Windows ANSI codepage instead of UTF-8 -- confirmed live
    in eos-claude-md-guard.py (2026-07-17) and reproduced here via a direct
    decode unit test (a subprocess spawned from a dev shell does not reliably
    reproduce this OS/codepage quirk -- see hooks/tests/test-confidentiality-
    guard.py's _load_guard_module()). Not exploitable against
    the current roster (every active term is pure ASCII, which survives
    cp1252 corruption of other bytes in scan_text), but it silently defeats
    this fail-closed leak scanner for ANY future confidential term containing
    a non-ASCII character (an accented name, a curly quote, an em-dash) --
    exactly the dangerous under-block case this hook's own docstring already
    flags as invisible to fail-closed. Reading the raw bytes and decoding
    them ourselves makes this independent of whatever codepage the parent
    process happened to inherit."""
    return sys.stdin.buffer.read().decode("utf-8")


def _git_common_dir(start_dir):
    """Absolute path to the repo's shared .git dir (same for every worktree of
    the same repo), or None on any failure -- not a git repo, git missing, etc."""
    try:
        p = subprocess.run(
            ["git", "-C", start_dir, "rev-parse", "--git-common-dir"],
            capture_output=True, text=True, timeout=5,
        )
    except Exception:
        return None
    if p.returncode != 0:
        return None
    out = p.stdout.strip()
    if not out:
        return None
    if not os.path.isabs(out):
        out = os.path.normpath(os.path.join(start_dir, out))
    return out


def _main_worktree_terms_file():
    """confidential-terms.json in the MAIN worktree, or None if it can't be
    resolved or doesn't exist there. hooks/confidential-terms.json is gitignored
    (see .gitignore), so `git worktree add` never checks it out into a linked
    worktree -- this lets a linked worktree fall back to the main checkout's
    copy instead of failing closed on every egress call from a fresh worktree
    (2026-07-12, mirrors the same fix in git-prepush-confidential-scan.py)."""
    common_dir = _git_common_dir(HOOK_DIR)
    if common_dir is None:
        return None
    candidate = os.path.join(os.path.dirname(common_dir), "hooks", "confidential-terms.json")
    if os.path.normcase(os.path.abspath(candidate)) == os.path.normcase(os.path.abspath(TERMS_FILE)):
        return None  # already the file we just tried
    return candidate


def load_terms():
    """Parsed terms dict. Tries this checkout's copy first; when no explicit
    CONFIDENTIAL_TERMS_FILE_OVERRIDE is set and that copy is missing/unreadable,
    falls back to the MAIN worktree's copy (git-common-dir is shared across every
    worktree of the repo) before giving up. The override is a test-only escape
    hatch and is used EXACTLY as given, with no fallback, so a test pointed at a
    synthetic fixture never silently falls through to the real roster. Still
    raises (the caller's except in main() fails closed) if unreadable everywhere.
    """
    try:
        with open(TERMS_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        if TERMS_FILE_OVERRIDE:
            raise
        fallback = _main_worktree_terms_file()
        if fallback is None:
            raise
        with open(fallback, encoding="utf-8") as f:
            return json.load(f)


def roster_staleness(terms):
    """(is_stale, detail) for the roster freshness anchor `_meta.roster_last_verified`.

    FAIL-CAUTIOUS (mirrors this hook's fail-closed bias -- detection over silence): a MISSING or
    UNPARSEABLE anchor is treated as STALE, not fresh. An absent freshness date is itself an
    unverifiable state, and Invariant 3 says treat unverifiable as ask-first -- silently assuming
    "fresh" would reintroduce exactly the blind spot this tripwire exists to close. A parseable
    FUTURE date (clock skew / forward-dated verification) is accepted as not-stale but noted, so it
    never nags. `detail` is a short human string reused verbatim in the advisory and the breadcrumb.
    """
    meta = terms.get("_meta") if isinstance(terms, dict) else None
    raw = (meta or {}).get("roster_last_verified")
    if not raw:
        return True, "_meta.roster_last_verified is MISSING -- roster freshness cannot be proven"
    try:
        verified = datetime.date.fromisoformat(str(raw).strip())
    except Exception:
        return True, "_meta.roster_last_verified (%r) is not an ISO date -- freshness cannot be proven" % raw
    days = (datetime.date.today() - verified).days
    if days > STALENESS_THRESHOLD_DAYS:
        return True, ("_meta.roster_last_verified=%s is %d days old (> %d-day tripwire); the "
                      "active-deal list may be out of date" % (verified.isoformat(), days,
                                                               STALENESS_THRESHOLD_DAYS))
    return False, "_meta.roster_last_verified=%s (%d days old)" % (verified.isoformat(), days)


def surface_staleness(detail, session_id):
    """Surface a STALE roster WITHOUT hard-blocking (Invariant 3: warn, don't freeze legitimate work).

    Two coordinated signals, BOTH best-effort -- a state read/write failure must NEVER affect the
    egress decision (this is telemetry, not the safety gate):
      * a one-time-per-session loud stderr ADVISORY, so the operator sees it in real time at the
        moment an egress decision is being made against a possibly-incomplete roster; and
      * a durable JSON breadcrumb (hooks/state/roster-staleness.json) a periodic check (the weekly
        eos-health-report / a doctrine probe) or a human can pick up. It also stores
        `last_warned_session`, which is how the advisory is throttled to once per session.

    If the breadcrumb can't be read (so we can't prove we already warned this session), we FAIL
    CAUTIOUS and warn anyway -- a repeated advisory is a cheaper failure than a silent stale roster.
    The caller still ALLOWS the (clean) egress: present-but-stale is a WARN, not the absent-roster
    hard-block. NOTE the breadcrumb carries only dates / a session id / this module's own detail
    string -- never any deal term -- so it is safe to write and to grep.
    """
    prior = {}
    try:
        with open(STALE_STATE_FILE, encoding="utf-8") as f:
            prior = json.load(f)
    except Exception:
        prior = {}  # unreadable/absent -> cannot prove a prior warning this session -> warn (cautious)
    already_warned = bool(session_id) and prior.get("last_warned_session") == session_id

    if not already_warned:
        sys.stderr.write(
            "WARNING (confidentiality, STALE ROSTER): %s. Re-verify the active-deal list against the "
            "source of record, then set _meta.roster_last_verified in confidential-terms.json to "
            "today. Until then, do NOT name any deal on an external surface without independent "
            "confirmation -- a newly-confidential deal may not yet be on the list.\n" % detail)

    # Best-effort durable breadcrumb. Wrapped so a write failure (perms, race) can never touch the
    # egress decision: staleness telemetry is advisory, egress safety is not negotiable.
    try:
        os.makedirs(STATE_DIR, exist_ok=True)
        with open(STALE_STATE_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "stale": True,
                "detail": detail,
                "detected_at": datetime.datetime.now().isoformat(timespec="seconds"),
                "threshold_days": STALENESS_THRESHOLD_DAYS,
                # Record the current session as warned so the advisory stays 1x/session. A blank
                # session_id can't be deduped (e.g. a direct test invocation) -> keep any prior
                # marker rather than clobber it, and such calls simply warn every time (cautious).
                "last_warned_session": session_id or prior.get("last_warned_session"),
            }, f, indent=2)
    except Exception:
        pass  # telemetry only -- egress safety must never depend on this write succeeding


def _str_terms(deal, field):
    """The string entries of a roster list. A malformed entry (a number, a nested list) is skipped
    rather than allowed to raise: an uncaught exception here exits 1, which is NON-BLOCKING."""
    value = deal.get(field) or []
    return [t for t in value if isinstance(t, str) and t] if isinstance(value, list) else []


def find_hit(text, terms, context_text=None):
    """Return (deal_label, term) on first confidential hit in `text`, else None. A context term
    counts when its trigger (context_requires_any) appears in `context_text`, which defaults to
    `text`; seam windows pass the whole post-edit file so a trigger elsewhere on the page counts."""
    if not text:
        return None
    low = text.lower()
    ctx_low = low if context_text is None else context_text.lower()
    for key, deal in terms.items():
        if key.startswith("_") or not isinstance(deal, dict) or not deal.get("active", True):
            continue
        for t in _str_terms(deal, "always"):
            if t.lower() in low:
                return (deal.get("label", key), t)
        reqs = [r.lower() for r in _str_terms(deal, "context_requires_any")]
        if reqs and any(r in ctx_low for r in reqs):
            for t in _str_terms(deal, "context"):
                if t.lower() in low:
                    return (deal.get("label", key), t)
    return None


def collect_text(obj):
    """Flatten any nested tool_input into one scannable string."""
    parts = []
    if isinstance(obj, str):
        parts.append(obj)
    elif isinstance(obj, dict):
        for v in obj.values():
            parts.append(collect_text(v))
    elif isinstance(obj, list):
        for v in obj:
            parts.append(collect_text(v))
    elif obj is not None:
        parts.append(str(obj))
    return " ".join(p for p in parts if p)


# --- Edit seams (2026-09-24) ---------------------------------------------------------------------
# An Edit's new_string is not the whole story: the text it lands between is already on disk, so a
# term can be CREATED at the seam -- "Zephyr C|QQ|orp Portfolio" with QQ -> "" (or with QQ -> "o",
# which alone contains no term) becomes a confidential name that new_string never carried. Before
# this, that shape passed unscanned; and a delete-only Edit (new_string "") had nothing to scan at
# all, so it fail-closed on every public-site edit that only removed text. Both close the same way:
# apply the edit(s) to the file's current text in memory and scan a window around every seam, at
# least as wide as the longest term on each side. Context triggers are looked up in the WHOLE
# post-edit file, since a trigger elsewhere on the page makes a context term at the seam a hit.
#
# Fail closed when the edit cannot be simulated against a file that EXISTS: the real Edit tool
# matches more leniently than `old in text` (curly/straight quote folding, \uXXXX decoding,
# UTF-16 files by BOM, files far past our size cap), so "old_string not found here" does not mean
# "the tool will refuse". Only a target that does not exist yet keeps the pre-2026-09-24 behavior
# (scan new_string; nothing to scan -> block).
#
# Known limit: the decision is taken on a snapshot. A writer that changes the file between this hook
# and the Edit's apply (seconds, measured) is not seen; nothing re-scans after the write. The
# pre-2026-09-24 guard had the same gap for any non-empty edit (a seam it never looked at).
#
# Why the windows cover every new occurrence (MultiEdit applies edits in order): take a term present
# after the last edit that was not there before. Let k be the last edit whose replaced span or
# insertion point falls inside the term. No later edit changes the term's characters, so the term is
# already present, intact, in the text right after edit k -- and it contains or straddles k's seam.
# The window taken from that intermediate text, [seam - W, seam + len(new) + W] with W >= the term's
# length, contains it.
SEAM_MAX_FILE_BYTES = 20 * 1024 * 1024


def _seam_width(terms):
    """Window margin on each side of a seam: twice the longest active term (lower() can lengthen
    some non-ASCII characters) plus slack. 0 when no deal is active -- nothing to find. None on a
    roster shape it cannot read, which disables seam simulation (the caller then fails closed on
    an empty scan, as before)."""
    try:
        longest = 0
        for key, deal in terms.items():
            if key.startswith("_") or not isinstance(deal, dict) or not deal.get("active", True):
                continue
            for field in ("always", "context", "context_requires_any"):
                for t in deal.get(field, []) or []:
                    if isinstance(t, str):
                        longest = max(longest, len(t))
        return 2 * longest + 8 if longest else 0
    except Exception:
        return None


def _edit_seams(path, edits, width):
    """(windows, post_edit_text) for the edit(s), or None when they cannot be simulated (unreadable,
    non-UTF-8 or oversized file, a non-dict edit, missing or empty old_string, old_string not in the
    text). Never raises: an uncaught exception exits 1, which is NON-BLOCKING, i.e. fail-open.

    Mirrors the Edit tool where it matters: universal newlines (it matches LF old_strings against
    CRLF files), and a delete (new_string "") of text followed by a newline also removes that
    newline. Windows only feed the term scan, so none of this changes what is written."""
    try:
        if not path or os.path.getsize(path) > SEAM_MAX_FILE_BYTES:
            return None
        with open(path, encoding="utf-8", errors="strict", newline=None) as f:
            text = f.read()
        windows = []
        for ed in edits:
            if not isinstance(ed, dict):
                return None
            old, new = ed.get("old_string"), ed.get("new_string")
            if not isinstance(old, str) or not isinstance(new, str) or not old:
                return None
            old, new = old.replace("\r\n", "\n"), new.replace("\r\n", "\n")
            if old not in text:
                return None
            if new == "" and not old.endswith("\n") and old + "\n" in text:
                old += "\n"
            if ed.get("replace_all"):
                parts = text.split(old)
                text = new.join(parts)
                at = 0
                for part in parts[:-1]:
                    at += len(part)
                    windows.append(text[max(0, at - width):at + len(new) + width])
                    at += len(new)
            else:
                at = text.index(old)
                text = text[:at] + new + text[at + len(old):]
                windows.append(text[max(0, at - width):at + len(new) + width])
        return windows, text
    except Exception:
        return None


def _exists(path):
    """True when something is at `path` (file, directory, anything). Never raises."""
    try:
        return bool(path) and isinstance(path, str) and os.path.lexists(path)
    except Exception:
        return False


def path_egress_surface(path):
    pl = (path or "").lower()
    if any(m in pl for m in SITE_MARKERS):
        return "public website repo"
    if pl.endswith(ARTIFACT_EXT):
        return "output artifact (%s)" % os.path.splitext(pl)[1]
    if any(m in pl for m in BUILD_MARKERS):
        return "mirror/build output"
    return None


def main():
    # 1) If we cannot load the term list, we cannot evaluate confidentiality -> fail closed.
    try:
        terms = load_terms()
    except Exception as e:
        block("confidential-terms.json unreadable (%s); cannot verify egress safety." % e)

    # _read_stdin_text() must be INSIDE the try: unlike the old sys.stdin.read()
    # (which -- decoding via whatever the platform resolves, e.g. cp1252 --
    # effectively never raises), an explicit .decode("utf-8") CAN raise
    # UnicodeDecodeError on genuinely malformed input. This hook is
    # FAIL-CLOSED: a read/decode failure must BLOCK via the same path as an
    # unparseable payload, not propagate as an uncaught exception (which
    # would exit 1 -- non-blocking, i.e. a silent fail-OPEN on this
    # fail-closed gate).
    try:
        raw = _read_stdin_text()
        data = json.loads(raw) if raw.strip() else {}
    except Exception:
        block("tool-call payload could not be parsed; cannot verify egress safety.")

    tool = (data.get("tool_name") or data.get("tool") or "")
    ti = data.get("tool_input") or {}
    if not isinstance(ti, dict):
        ti = {"_": ti}

    # --- Determine egress surface + scan text -----------------------------------------
    surface = None
    scan_text = None

    # File-writing tools: only egress when the target path is an external surface.
    if tool in ("Write", "Edit", "MultiEdit", "NotebookEdit"):
        path = ti.get("file_path") or ti.get("notebook_path") or ""
        if not isinstance(path, str):
            block("file path is not a string; cannot classify the write target.")
        surface = path_egress_surface(path)
        if surface:
            # scan the content being written/inserted (not old_string)
            pieces = [ti.get("content", ""), ti.get("new_string", ""), ti.get("new_source", "")]
            raw_edits = ti.get("edits")
            for ed in raw_edits if isinstance(raw_edits, list) else ([raw_edits] if raw_edits else []):
                pieces.append(ed.get("new_string", "") if isinstance(ed, dict) else ed)
            scan_text = " ".join(str(p) for p in pieces if p)
            # An explicit empty Write writes nothing that could leak.
            extracted = tool == "Write" and isinstance(ti.get("content"), str)
            if tool in ("Edit", "MultiEdit"):
                edits = [ti] if tool == "Edit" else ti.get("edits")
                width = _seam_width(terms)
                seams = None
                if isinstance(edits, list) and edits and width is not None:
                    seams = _edit_seams(path, edits, width)
                if seams is None:
                    if _exists(path):
                        block("edit to %s could not be simulated against the file on disk, so the "
                              "text at its seams cannot be checked." % surface)
                else:
                    windows, post_edit = seams
                    for w in windows:
                        hit = find_hit(w, terms, context_text=post_edit)
                        if hit:
                            block("'%s' identifier ('%s') would be formed where this edit joins the "
                                  "existing text of %s. This deal must not reach any external surface "
                                  "until closing." % (hit[0], hit[1], surface))
                    extracted = True
            if not scan_text and not extracted:
                # egress write we cannot read -> fail closed
                block("write to %s but content could not be extracted." % surface)

    # Notion writes: the whole payload is bound for Notion.
    elif NOTION_WRITE.search(tool):
        surface = "Notion write (%s)" % tool
        scan_text = collect_text(ti)

    # Outlook send/draft/forward/reply: the whole payload is bound for email.
    elif OUTLOOK_SEND.search(tool):
        surface = "Outlook send/draft (%s)" % tool
        scan_text = collect_text(ti)

    # Shell: only egress commands are scanned (internal commands may reference the deal).
    elif tool == "Bash":
        cmd = ti.get("command", "") or ""
        if EGRESS_BASH.search(cmd):
            surface = "egress shell command"
            scan_text = cmd

    # Not an egress surface -> allow.
    if surface is None:
        sys.exit(0)

    # --- Enforce -----------------------------------------------------------------------
    hit = find_hit(scan_text, terms)
    if hit:
        label, term = hit
        block("'%s' identifier ('%s') would cross egress surface [%s]. "
              "This deal must not reach any external surface until closing. "
              "Keep it on internal/local paths only." % (label, term, surface))

    # Clean egress. Before allowing, check roster FRESHNESS -- this no-hit path is the exact failure
    # mode a stale roster hides: a NEW confidential deal that should be on the list but isn't produces
    # ZERO hits and would sail through silently. A present-but-stale roster is a WARN (surface the
    # advisory + allow), NOT the absent-roster hard-block; staleness makes the hook speak up, it does
    # not freeze all legitimate egress forever. Evaluated only here (egress surface, no hit) so the
    # cost/noise lands only where a missing-deal leak could actually occur.
    stale, detail = roster_staleness(terms)
    if stale:
        surface_staleness(detail, data.get("session_id") or "")

    sys.exit(0)


if __name__ == "__main__":
    main()
