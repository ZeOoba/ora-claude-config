"""Governance-layer hard write-gate + chip claim-lock -- PreToolUse hook.

WHY (2026-07-18, write-guard architecture hardening, Plan 5). Before this hook,
hooks/**, settings.json and CLAUDE.md had NO hard write-gate -- only soft heuristics
(eos-plan-gate.py's 4-edit threshold, eos-claude-md-guard.py's word-budget check).
One bad edit to confidentiality-guard.py or ora-autonomy-gate.py could silently
disable the entire governance layer. This gate makes that edit LOUD: it requires
Gabriel's explicit in-turn confirmation, expressed through the EXISTING session-
scoped override-token mechanism (hooks/lib/override_tokens.py -- the retired flat
mtime-only sentinel stays dead; see that module's docstring for the four defects
that killed it).

WHAT IT GATES (token tier allow-config-write, scope config-write, 60 min, multi-use):
  * <root>/hooks/**            EXCEPT hooks/sessions/** and hooks/state/**
                               (SELF-DEADLOCK DEFENSE: the override token itself
                               lives at hooks/sessions/<sid>/overrides/ -- gating it
                               would make the gate unsatisfiable; hooks/state/ is a
                               runtime breadcrumb dir, not governance code)
  * <root>/settings.json, <root>/settings.local.json
  * <root>/CLAUDE.md
  * either fleet's scheduled-task registry backing file (defense-in-depth on top of
    registry-write-guard.py's unconditional block)
  <root> is the LIVE checkout (C:/Users/Owner/.claude) ONLY. Worktree copies
  (<root>/.claude/worktrees/**) are deliberately NOT gated: isolated-worktree
  development is the sanctioned path for hook work, a worktree copy is inert until
  merged, and the merge itself is a loud, review-visible act (see REFUTE notes in
  the 2026-07-18 build report for the residual-risk argument).

CLAIM-LOCK (rules.md sec 8, chip-claims.log): writes to <root>/handoffs/** and
<root>/workflows/** additionally require this session to HOLD an open chip claim --
a CLAIMED line naming this session, no later DONE/ABORTED for the same title, and a
CLAIMED-or-HEARTBEAT line fresher than 60 min (the documented staleness convention).

FAIL-OPEN + TTL, per the RATIFIED doctrine (feedback_fail_open_over_mutex_for_fleet_
gates, Gabriel 2026-07-16): the claim-lock ALLOWS when chip-claims.log is missing,
unreadable, malformed, or when the payload carries no session_id -- a fresh worktree
or clone (the log is untracked) must never be bricked, and absence of information is
never license to block a coordination gate. Contrast the confidentiality-guard
self-deadlock (feedback_confidentiality_guard_selfdeadlock.md): a fail-CLOSED guard
with a malformed input once bricked Write/Edit/Bash machine-wide. The TOKEN gate, by
contrast, blocks on a POSITIVE governance-path match without a token -- that is the
gate's entire point -- but any INTERNAL error in this hook still fails open (whole
body wrapped, exit 0), so a bug here can never brick a session.

EXIT CODES (reference_pretooluse_vs_git_hook_exit_codes.md -- PreToolUse family):
exit 0 = allow; exit 2 + stderr = block. NEVER exit 1 (non-blocking error: the tool
call would PROCEED, silently disabling the gate).

SHELL COVERAGE, honestly stated: Bash / DC start_process / DC interact_with_process
are matched by normalized-text markers (write indicator + governance-path marker
anywhere in the command -- the same breadth-over-precision tradeoff ora-autonomy-
gate.py Gate 2b makes deliberately; do NOT narrow it, see
feedback_autonomy_gate_matcher_cannot_be_safely_narrowed.md). Value indirection
($var, concatenation, Get-Content) remains the documented structural ceiling of
text-matching, exactly as it is for the autonomy gate.

TEST SEAMS (env vars -- TEST ONLY, never set in settings.json/scheduled tasks;
setting them in production would redirect a security gate to attacker-chosen paths,
same caveat as OVERRIDE_DIR / ORA_OVERRIDE_SESSIONS_DIR):
  ORA_CONFIG_GUARD_ROOT, ORA_CHIP_CLAIMS_LOG, and the lib's
  ORA_OVERRIDE_SESSIONS_DIR.

Stdlib only. ASCII-only. Windows (`python`).
"""
import json
import os
import sys
from datetime import datetime, timedelta, timezone

HOOKS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HOOKS_DIR, "lib"))

DEFAULT_ROOT = r"C:\Users\Owner\.claude"

# The token contract is the SHARED one (override_tokens.py) -- do not reinvent.
# Import posture mirrors ora-autonomy-gate.py exactly (and for the same reason --
# see reference_pretooluse_vs_git_hook_exit_codes.md): letting an ImportError
# propagate would exit 1, which is NON-blocking, silently disabling this gate; a
# sys.exit(2) at import time would brick every tool call. So degrade to "no
# override exists": ungated writes still pass, every gated write blocks.
try:
    from override_tokens import Tier, describe_token, token_grants  # noqa: E402
    TOKEN_CONTRACT_LOADED = True
except Exception:
    TOKEN_CONTRACT_LOADED = False

    class Tier(object):
        def __init__(self, name, scope, ttl, single_use=False,
                     requires_extra_check=False):
            self.name = name
            self.scope = scope
            self.ttl = ttl
            self.single_use = single_use
            self.requires_extra_check = requires_extra_check

    def token_grants(session_id, tier, extra_check=None):
        return None  # no validator -> no grant, ever

    def describe_token(session_id, tier):
        return ("  <hooks/lib/override_tokens.py could not be imported -- no "
                "override can be honored; fix the module, do not mint a token>\n")

# Tool-call shape knowledge is the shared normalization layer's job. Same degrade
# logic; without it we cannot see write targets, so nothing matches and the gate is
# inert -- but that is identical to this hook not existing (soft-heuristic status
# quo), never a NEW hole, and the coverage meta-test pins the lib's presence.
try:
    from tool_call_paths import (  # noqa: E402
        GIT_MUTATE_RE, is_shell_tool, normalize_text, shell_analysis,
        write_targets)
    TOOL_PATHS_LOADED = True
except Exception:
    TOOL_PATHS_LOADED = False

CONFIG_WRITE = Tier("allow-config-write", "config-write", 3600)

CLAIM_TTL_SECONDS = 3600  # rules.md sec 8: <60 min old = active claim/heartbeat
REGISTRY_BASENAME = "scheduled-tasks.json"
CC_SEGMENT = "claude-code-sessions"
LAMS_SEGMENT = "local-agent-mode-sessions"


def guard_root():
    return os.environ.get("ORA_CONFIG_GUARD_ROOT") or DEFAULT_ROOT


def claims_log_path():
    return os.environ.get("ORA_CHIP_CLAIMS_LOG") or \
        os.path.join(guard_root(), "chip-claims.log")


def _norm(p):
    """Forward-slash, lower-cased, junction-resolved absolute form for matching."""
    try:
        resolved = os.path.realpath(p)
    except (OSError, ValueError):
        resolved = os.path.abspath(p)
    return resolved.replace("\\", "/").lower().rstrip("/")


# ------------------------------------------------------------------ path classifiers
def _classify(norm_path, root):
    """('governance', label) | ('claim', label) | None for a normalized path."""
    hooks_root = root + "/hooks"
    if norm_path == hooks_root or norm_path.startswith(hooks_root + "/"):
        rel = norm_path[len(hooks_root):]
        if rel.startswith("/sessions/") or rel == "/sessions" \
                or rel.startswith("/state/") or rel == "/state":
            return None  # exempt: token/runtime state -- self-deadlock defense
        return ("governance", "hooks/** (live governance code)")
    for base, label in (("settings.json", "settings.json"),
                        ("settings.local.json", "settings.local.json"),
                        ("claude.md", "CLAUDE.md")):
        if norm_path == root + "/" + base:
            return ("governance", label)
    parts = norm_path.split("/")
    if parts and parts[-1] == REGISTRY_BASENAME and \
            (CC_SEGMENT in parts or LAMS_SEGMENT in parts):
        return ("governance", "scheduled-task registry (%s)" %
                (CC_SEGMENT if CC_SEGMENT in parts else LAMS_SEGMENT))
    for sub, label in (("/handoffs", "handoffs/**"), ("/workflows", "workflows/**")):
        base = root + sub
        if norm_path == base or norm_path.startswith(base + "/"):
            return ("claim", label)
    return None


def classify_path(raw_path):
    return _classify(_norm(raw_path), _norm(guard_root()))


# ------------------------------------------------------------------ shell classifiers
# Markers matched ANYWHERE in a normalized (NFKC + Cf/Mn-stripped, lowercased,
# forward-slashed) command that also carries a write indicator. Exempt markers are
# blanked FIRST so a token write into hooks/sessions/ never trips the hooks marker.
# Breadth over precision: a false positive costs a retry; a false negative silently
# edits the governance layer.
def _shell_marker_sets():
    root = _norm(guard_root())
    # The generic ".claude"/"~/.claude" spellings are ALWAYS armed, not only when
    # the root is the live default: a command can reach the live tree via tilde or
    # relative form regardless of what the (test-seam) root is, and the seam must
    # not weaken the matcher it is trying to test. Breadth over precision.
    generic_roots = {root, "~/.claude", ".claude"}
    exempt, governance, claim = [], [], []
    for g in generic_roots:
        exempt += [g + "/hooks/sessions", g + "/hooks/state"]
        governance += [(g + "/hooks", "hooks/**"),
                       (g + "/settings.json", "settings.json"),
                       (g + "/settings.local.json", "settings.local.json"),
                       (g + "/claude.md", "CLAUDE.md")]
        claim += [(g + "/handoffs", "handoffs/**"),
                  (g + "/workflows", "workflows/**")]
    # worktree trees are exempt (see module docstring) -- blank them before the
    # governance markers can see their .../hooks/... segments
    exempt = [g + "/worktrees" for g in generic_roots] + exempt
    return exempt, governance, claim


def _blank_exempt(text, exempt_markers):
    """Blank the ENTIRE whitespace-delimited token containing an exempt marker, so
    an exempted path (a worktree tree, a hooks/sessions token write) contributes
    NOTHING to later marker/root matching -- not even its root prefix."""
    import re as _re
    for marker in exempt_markers:
        text = _re.sub(r"\S*" + _re.escape(marker) + r"\S*", " <exempt> ", text)
    return text


def classify_shell(command):
    """('governance'|'claim', label) for a write-shaped shell command naming a
    protected path, else None."""
    if not TOOL_PATHS_LOADED:
        return None
    text = normalize_text(command).replace("\\", "/").lower()
    exempt, governance, claim = _shell_marker_sets()
    text = _blank_exempt(text, exempt)
    for marker, label in governance:
        if marker in text:
            return ("governance", label)
    if REGISTRY_BASENAME in text and (CC_SEGMENT in text or LAMS_SEGMENT in text):
        return ("governance", "scheduled-task registry")
    # file-rewriting git aimed anywhere at the live checkout (REFUTE 2026-07-18:
    # `git -C ~/.claude checkout main -- hooks/` rewrote the live hook layer with
    # neither a classic write verb nor a contiguous ".claude/hooks" marker in its
    # text -- live-proven). Read-only git passes; `git -C ~/.claude checkout -b
    # feature` false-positives and costs a retry/token -- breadth over precision.
    root_mentions = (_norm(guard_root()), "~/.claude", ".claude")
    if GIT_MUTATE_RE.search(text) and any(r in text for r in root_mentions):
        return ("governance",
                "file-rewriting git command referencing the live ~/.claude checkout")
    for marker, label in claim:
        if marker in text:
            return ("claim", label)
    return None


# ------------------------------------------------------------------ claim-lock
def _parse_ts(ts):
    try:
        dt = datetime.fromisoformat(ts.strip())
        if dt.tzinfo is None:
            dt = dt.astimezone()
        return dt
    except Exception:
        return None


def session_holds_open_claim(session_id, log_path):
    """True: session holds a fresh open claim. False: log is readable and shows no
    such claim. None: log missing/unreadable/malformed or no session_id -- the
    caller must FAIL OPEN on None (ratified fail-open + TTL doctrine)."""
    if not isinstance(session_id, str) or len(session_id) < 8:
        return None
    try:
        if not os.path.isfile(log_path):
            return None
        with open(log_path, "r", encoding="utf-8", errors="strict") as fh:
            raw = fh.read()
    except Exception:
        return None
    ids = (session_id.lower(), session_id.lower()[:8])
    entries = []
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 4:
            continue  # tolerate a stray malformed line without failing the parse
        status = parts[1].split()[0].upper() if parts[1] else ""
        who = "|".join(parts[3:]).lower()
        entries.append((parts[0], status, parts[2], who))
    if not entries:
        return None  # nothing parseable at all -> treat as malformed -> fail open
    now = datetime.now(timezone.utc).astimezone()
    open_titles = {}
    for ts, status, title, who in entries:  # file order == append order
        mine = any(s in who for s in ids)
        if status in ("CLAIMED", "HEARTBEAT"):
            if mine:
                open_titles[title] = ts
        elif status in ("DONE", "ABORTED"):
            open_titles.pop(title, None)  # closed by anyone, incl. another session
    for title, ts in open_titles.items():
        dt = _parse_ts(ts)
        if dt is None:
            return True  # unparseable timestamp on MY claim -> fail toward open
        if now - dt <= timedelta(seconds=CLAIM_TTL_SECONDS):
            return True
    return False


# ------------------------------------------------------------------ blocks
def _block_governance(label, detail, session_id):
    sys.stderr.write(
        "BLOCKED (config-write-guard): write to the live governance layer -- %s\n"
        "  target: %s\n"
        "A single unreviewed edit here can silently disable the whole hook/gate "
        "layer, so this write requires Gabriel's explicit in-turn confirmation "
        "(token tier allow-config-write).\n"
        "Preferred path: do this work in an isolated worktree "
        "(git worktree add .claude/worktrees/<name>) and land it via review -- "
        "worktree copies are not gated.\n"
        "If Gabriel has just approved a LIVE edit, write this override token and "
        "retry:\n%s"
        % (label, detail, describe_token(session_id, CONFIG_WRITE)))
    sys.exit(2)


def _block_claim(label, detail, session_id, log_path):
    sys.stderr.write(
        "BLOCKED (config-write-guard): write to a claim-locked coordination path -- "
        "%s\n"
        "  target: %s\n"
        "This session holds no open chip claim (rules.md sec 8). Before writing to "
        "registry/handoff/shared-doctrine paths, claim the work: append\n"
        "  <ISO-8601 local> | CLAIMED | <chip title> | <surface>/%s\n"
        "to %s (and a matching DONE/ABORTED line on exit; HEARTBEAT every 30-45 min "
        "for long runs), then retry. If another session's CLAIMED line for the same "
        "work is <60 min old, ABORT and report the prior claim instead.\n"
        % (label, detail, (session_id or "<session>")[:8], log_path))
    sys.exit(2)


# ------------------------------------------------------------------ main
def main():
    payload = json.loads(sys.stdin.buffer.read().decode("utf-8"))
    if not isinstance(payload, dict):
        return
    tool_name = payload.get("tool_name") or ""
    tool_input = payload.get("tool_input")
    session_id = payload.get("session_id")
    if not isinstance(session_id, str):
        session_id = ""
    if not isinstance(tool_input, dict) or not TOOL_PATHS_LOADED:
        return  # nothing inspectable / no shape knowledge -> status quo, allow

    hits = []  # (kind, label, detail)
    targets = write_targets(tool_name, tool_input)
    for target in targets:
        cls = classify_path(target.raw_path)
        if cls:
            hits.append((cls[0], cls[1],
                         "%s (%s via %s)" % (target.raw_path, target.operation,
                                             tool_name)))
    if not targets and not is_shell_tool(tool_name):
        # GENERIC PATH-FIELD SCAN (REFUTE 2026-07-18): a routed tool the shape
        # registry does not model (an Excel MCP writer, a future connector's file
        # tool) must not sail through just because nobody taught the registry its
        # schema. Deny-by-default on path-shaped input fields, same direction as
        # ora-autonomy-gate check_mcp's Round 3 fix: any string field that LOOKS
        # like a path aimed at the governance layer gates the call.
        for field in ("file_path", "path", "filepath", "notebook_path",
                      "output_path", "source", "destination", "target", "dest"):
            raw = tool_input.get(field)
            if isinstance(raw, str) and raw:
                cls = classify_path(raw)
                if cls:
                    hits.append((cls[0], cls[1],
                                 "%s (field '%s' via %s)"
                                 % (raw, field, tool_name)))
    if is_shell_tool(tool_name):
        analysis = shell_analysis(tool_name, tool_input)
        if analysis is not None and analysis.may_write:
            cls = classify_shell(analysis.command)
            if cls:
                hits.append((cls[0], cls[1],
                             "shell command via %s: %s"
                             % (tool_name, analysis.command.strip()[:200])))
            # else: write-shaped but naming no protected path -- statically
            # unresolvable (value indirection etc.). Documented structural
            # ceiling, same as ora-autonomy-gate.py's HONEST LIMIT: allow.

    governance_hits = [h for h in hits if h[0] == "governance"]
    claim_hits = [h for h in hits if h[0] == "claim"]

    if governance_hits:
        kind, label, detail = governance_hits[0]
        # token_grants consumes single-use tokens, but this tier is multi-use, so
        # evaluating it exactly once per blocked-or-allowed call is safe.
        if token_grants(session_id, CONFIG_WRITE) is None:
            _block_governance(label, detail, session_id)
        return  # token granted -> allowed; claim-lock does not also apply

    if claim_hits:
        held = session_holds_open_claim(session_id, claims_log_path())
        if held is False:
            kind, label, detail = claim_hits[0]
            _block_claim(label, detail, session_id, claims_log_path())
        # True -> claim held; None -> fail open (missing/malformed log or no
        # session identity). Both allow.


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise  # a real block (exit 2) must propagate
    except Exception:
        pass  # FAIL OPEN: an internal bug must never block a tool call
    sys.exit(0)
