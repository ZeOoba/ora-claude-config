#!/usr/bin/env python3
"""ORA autonomy gate (PreToolUse) — preserves the human gates under defaultMode=bypassPermissions.

With bypassPermissions, permission prompts never fire, so invariants 1 and 2 are enforced
here instead (hooks run in every mode, including scheduled/headless sessions):

  GATE 1 — external email: any send-via-outlook.ps1 invocation carrying a -To/-Cc/-Bcc
           flag with a recipient outside @oxfordra.net is blocked. Internal fleet sends
           (ggoldberg/egoldberg) pass untouched.
           Override: allow-external-send  (scope external-send, 5 min, SINGLE-USE,
           and it must NAME every external recipient of the send)
  GATE 2 — website (oxfordra.net): blocked across every reachable path —
             (a) `netlify deploy ... --prod` via the CLI,
             (b) a raw-shell write (cp/mv/redirect/...) into the site tree,
             (c) Edit/Write into a website-canonical or oxford-site tree, and
             (d) any Netlify MCP *-updater tool (prod deploy / project / CSP+headers).
           Reads and preview deploys pass untouched.
           Overrides: allow-website-write   (scope website-write,  60 min, multi-use) -> b, c
                      allow-website-deploy  (scope website-deploy,  5 min, SINGLE-USE) -> a, d

Exit 2 = block (stderr is shown to the model). Unparseable input fails open so a hook
malfunction never bricks every tool call.

OVERRIDE TOKENS (hardened 2026-07-16, Gabriel-ratified)
-------------------------------------------------------
A token lives at:  hooks/sessions/<session_id>/overrides/<name>

and its content must be:

    scope: website-deploy
    session: <the session_id it was minted in>
    recipients: a@x.com, b@y.com     # external-send ONLY; every external recipient
    reason: <free text — for the human audit trail, not enforced>

It may be created ONLY after Gabriel's explicit in-turn confirmation in a live session.

The previous scheme was a flat `hooks/overrides/<name>` sentinel checked by mtime alone.
Four defects compounded, all confirmed empirically before this rewrite:
  1. Content-blind — a token reading "banana. Not a deploy. DO NOT DEPLOY ANYTHING."
     authorized `netlify deploy --prod`. Justification text was pure theatre.
  2. One name (`allow-website-change`) keyed all four gates, so approving a one-line CSS
     edit silently also opened a production publish for an hour.
  3. Session-blind and global — any concurrent session inherited any live token. Observed
     live: 4 sessions running, one token's scope rewritten from "Not a deploy" to a prod
     deploy mid-flight.
  4. GIT-TRACKED. Because git sets mtime to checkout time and the gate trusted mtime alone,
     a plain `git clone` of ~/.claude materialized the token with age ~0 and SELF-GRANTED a
     live production-deploy window with no human involved. Proven: a fresh clone made this
     gate return exit 0 for `netlify deploy --prod`, against an empty-dir control at exit 2.

Fixes, in the order they matter:
  - Session-scoping (the eos-plan-gate.py pattern, same PreToolUse payload field) kills the
    cross-session leak AND defect 4 for free: hooks/sessions/ is already gitignored, so a
    token is now structurally impossible to commit. There is no ignore rule to forget.
  - Severity split: a write grant cannot open a deploy, and vice versa.
  - Content is load-bearing: scope and session must match, or the token is inert. NOTE the
    honest limit — this cannot defend against the session that WRITES the token (it could
    write any scope). It defends against mis-scoped reuse and makes the audit trail real.
  - Deploy/send tier: 5-minute TTL, consumed at gate-pass. "Gabriel just said yes" is short.

Everything fails CLOSED. No session_id, no token, wrong scope, wrong session, unparseable,
oversized, duplicate keys, future-dated, or un-consumable -> block. A false positive costs a
retry; a false negative publishes to the live site.

Consequence of the split, by design: a command that trips BOTH a deploy gate and a site-write
gate (e.g. `netlify deploy --prod --dir=oxford-site/dist > deploy.log`) needs BOTH tokens. That
is fail-closed and rare — the ordinary `netlify deploy --build --prod` run from inside the repo
names no site marker and needs only allow-website-deploy.

NOT IN SCOPE (deliberately): what the gate MATCHES. See
memory/feedback_autonomy_gate_matcher_cannot_be_safely_narrowed.md — three adversarial review
rounds each found a real bypass in one attempt to narrow Gate 2b's matcher; the broad match is
correct and stays. This file changes only WHO a granted override authorizes, for WHAT, and for
how long.
"""
import json
import os
import re
import sys
import time

LIB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib")
sys.path.insert(0, LIB_DIR)
try:
    from site_markers import SITE_PATH_MARKERS  # noqa: E402
except Exception:
    # Fallback matches site_markers.py's current value. This hook's own stated
    # philosophy is fail-open-on-malfunction, so a missing/broken shared module
    # should not crash it -- but a hardcoded fallback keeps Gate 2 functional
    # rather than silently disabling it entirely.
    SITE_PATH_MARKERS = ("website-canonical", "oxford-site")

# ORA_OVERRIDE_SESSIONS_DIR is a TEST SEAM ONLY -- it must never be set in settings.json's
# env block or any production scheduled-task context. Setting it there would let a process
# redirect this security gate's override lookup to an attacker-writable directory. It exists
# purely so test-ora-autonomy-gate.py can isolate itself from whatever is live in the real
# sessions folder (the 2026-07-12 OVERRIDE_DIR seam, re-pointed at the session-scoped path).
DEFAULT_SESSIONS_DIR = r"C:\Users\Owner\.claude\hooks\sessions"
OVERRIDE_SUBDIR = "overrides"

# A token may not be older than its tier's TTL. Small negative ages (filesystem timestamp
# granularity / clock skew) are tolerated; a genuinely future-dated token is refused, since
# a naive `age < ttl` check would otherwise honor it forever.
CLOCK_SKEW_TOLERANCE_SECONDS = 5
MAX_TOKEN_BYTES = 8192
# Only a filename-safe, traversal-free session_id may address a token directory. Rejects
# "..", "../overrides", "a/../../overrides", "\\..\\overrides" -- anything that could escape
# the sessions root and reach the retired flat overrides dir (or anywhere else).
SESSION_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")

INTERNAL_DOMAIN = "@oxfordra.net"
RECIPIENT_FLAGS = ("-to", "-cc", "-bcc")  # any one means the send has external reach


class Tier(object):
    """One override name == one severity tier. No name keys two tiers."""

    def __init__(self, name, scope, ttl, single_use=False, needs_recipients=False):
        self.name = name
        self.scope = scope
        self.ttl = ttl
        self.single_use = single_use
        self.needs_recipients = needs_recipients


WEBSITE_WRITE = Tier("allow-website-write", "website-write", 3600)
WEBSITE_DEPLOY = Tier("allow-website-deploy", "website-deploy", 300, single_use=True)
EXTERNAL_SEND = Tier("allow-external-send", "external-send", 300, single_use=True,
                     needs_recipients=True)

# Mutating shell ops; if one of these co-occurs with a site-path marker in a Bash
# command, treat it as a write into the oxfordra.net tree (Gate 2). Read-only verbs
# (cat/type/get-content/grep) without a redirect do not appear here -> they pass.
SITE_WRITE_INDICATORS = (
    ">", "cp ", "copy ", "mv ", "move ", "rm ", "del ", "remove-item",
    "set-content", "add-content", "out-file", "tee ", "new-item",
)
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", re.IGNORECASE)
# Matches fd-duplication redirects (2>&1, >&2, &>, &>>) so they don't get mistaken for a
# write redirect by the bare ">" in SITE_WRITE_INDICATORS (2026-07-09 — false-blocked a
# plain `ls ... 2>&1` read-only existence check).
FD_DUP_RE = re.compile(r"\d*>&\d*|&>{1,2}")
# Matches redirects to the null device (2>/dev/null, 2>nul, >/dev/null) — same rationale
# as FD_DUP_RE: discarding stderr/stdout into the void writes nothing, so it must not
# trip the bare ">" write indicator. Anchored immediately after ">" (only whitespace
# allowed between) so a real write whose PATH merely contains "/dev/null" as a substring
# (e.g. `> ".../dev/null.html"`) is not exempted (2026-07-10 — false-blocked a read-only
# grep with `2>/dev/null` against an oxford-site path).
NULL_REDIRECT_RE = re.compile(r"\d*>\s*(?:/dev/null|nul)\b", re.IGNORECASE)
# Matches netlify only as the leading token of a command segment (start, after ; & | or $( ),
# optionally via npx — so quoting/echoing/logging the phrase does not trip the gate.
NETLIFY_INVOKE_RE = re.compile(
    r"(?:^|[;&|]|\$\()\s*(?:npx\s+(?:--yes\s+)?)?netlify(?:-cli)?(?:\.cmd|\.exe)?\s", re.IGNORECASE
)


def _sessions_root():
    return os.environ.get("ORA_OVERRIDE_SESSIONS_DIR") or DEFAULT_SESSIONS_DIR


def _token_path(session_id, name):
    """Resolve a token path, or None if the session_id cannot safely address one."""
    if not isinstance(session_id, str) or not SESSION_ID_RE.match(session_id):
        return None
    root = _sessions_root()
    path = os.path.join(root, session_id, OVERRIDE_SUBDIR, name)
    # Defense in depth: SESSION_ID_RE already forbids separators, but re-assert that the
    # resolved path really sits under the sessions root before trusting it.
    try:
        root_abs = os.path.abspath(root)
        if os.path.commonpath([os.path.abspath(path), root_abs]) != root_abs:
            return None
    except (ValueError, OSError):
        return None
    return path


def _parse_token(path):
    """Return the token's key/value fields, or None if it is unusable.

    Fails closed on: unreadable, oversized, non-UTF-8, or DUPLICATE keys (a token with two
    `scope:` lines is ambiguous, and ambiguity must never resolve in the grant's favor).
    """
    try:
        if os.path.getsize(path) > MAX_TOKEN_BYTES:
            return None
        with open(path, "r", encoding="utf-8") as fh:
            raw = fh.read()
    except (OSError, UnicodeDecodeError):
        return None
    fields = {}
    for line in raw.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip().lower()
        if not key:
            continue
        if key in fields:
            return None  # duplicate key -> ambiguous -> refuse
        fields[key] = value.strip()
    return fields


def _fresh(path, ttl):
    try:
        age = time.time() - os.path.getmtime(path)
    except OSError:
        return False
    return -CLOCK_SKEW_TOLERANCE_SECONDS <= age < ttl


def _recipients_authorized(fields, external):
    """Every external recipient of the send must be named in the token."""
    raw = fields.get("recipients")
    if not raw:
        return False
    allowed = {r.strip().lower() for r in raw.split(",") if r.strip()}
    if not allowed:
        return False
    return all(r.lower() in allowed for r in external)


def _consume(path):
    """Burn a single-use token. If it cannot be removed we cannot promise single-use,
    so the caller must treat failure as 'no override'."""
    try:
        os.remove(path)
        return True
    except OSError:
        return False


def override_active(session_id, tier, external=None):
    path = _token_path(session_id, tier.name)
    if not path or not os.path.isfile(path):
        return False
    if not _fresh(path, tier.ttl):
        return False
    fields = _parse_token(path)
    if not fields:
        return False
    if fields.get("scope") != tier.scope:
        return False
    if fields.get("session") != session_id:
        return False
    if tier.needs_recipients and not _recipients_authorized(fields, external or []):
        return False
    # Consume BEFORE granting: if we granted first and the delete then failed, the token
    # would silently become multi-use.
    if tier.single_use and not _consume(path):
        return False
    return True


def block(reason, tier, session_id, extra=""):
    token_path = _token_path(session_id, tier.name)
    if token_path is None:
        where = ("<no valid session_id in this hook payload -- an override cannot be "
                 "created or honored here>")
    else:
        where = token_path
    body = "  scope: %s\n  session: %s\n" % (tier.scope, session_id or "<none>")
    if tier.needs_recipients:
        body += "  recipients: <every external recipient, comma-separated>\n"
    body += "  reason: <why Gabriel approved this>\n"
    sys.stderr.write(
        "BLOCKED by ORA autonomy gate: %s\n"
        "This action requires Gabriel's explicit in-turn confirmation (hard invariant 1/2).\n"
        "%s"
        "If he has just given it, write this override token and retry:\n"
        "  path: %s\n"
        "  valid: %d min%s\n"
        "  content:\n%s"
        % (reason, extra, where, tier.ttl // 60,
           ", SINGLE-USE (consumed by one gate-pass)" if tier.single_use else ", multi-use",
           body)
    )
    sys.exit(2)


def check_bash(command, session_id):
    lowered = command.lower()
    # GATE 1 — any send-via-outlook.ps1 with a recipient flag (To, Cc, OR Bcc).
    # Keying only on -To let a Bcc/Cc-only external send slip through (2026-06-13).
    if "send-via-outlook.ps1" in lowered and any(f in lowered for f in RECIPIENT_FLAGS):
        recipients = EMAIL_RE.findall(command)
        external = sorted({r for r in recipients if not r.lower().endswith(INTERNAL_DOMAIN)})
        if external and not override_active(session_id, EXTERNAL_SEND, external):
            block("external email recipient(s): %s" % ", ".join(external), EXTERNAL_SEND,
                  session_id,
                  extra="The token must NAME each external recipient: a token approving a\n"
                        "send to one counterparty does not authorize a send to another.\n")
    # GATE 2a — production deploy via the netlify CLI.
    if NETLIFY_INVOKE_RE.search(command) and "deploy" in lowered and "--prod" in lowered:
        if not override_active(session_id, WEBSITE_DEPLOY):
            block("production deploy to oxfordra.net (netlify --prod)", WEBSITE_DEPLOY,
                  session_id)
    # GATE 2b — writing into the site tree via a raw shell op (cp/mv/redirect/etc).
    # The Edit/Write tool path is covered by check_file_write; Bash bypassed it (2026-06-13).
    # Strip fd-duplication redirects (2>&1, &>) before checking the bare ">" write indicator,
    # so a routine read-only command like `ls ... 2>&1` doesn't false-block (2026-07-09).
    write_check_target = FD_DUP_RE.sub(" ", lowered)
    write_check_target = NULL_REDIRECT_RE.sub(" ", write_check_target)
    markers = [m for m in SITE_PATH_MARKERS if m in lowered]
    indicators = [w for w in SITE_WRITE_INDICATORS if w in write_check_target]
    if markers and indicators:
        if not override_active(session_id, WEBSITE_WRITE):
            # Say WHICH marker and WHICH indicator matched. This gate matches both
            # anywhere in the command, with no requirement that they be related -- so a
            # command that merely QUOTES a site path (writing site prose into a memory
            # file, committing a message that names the repo) trips it. That breadth is
            # deliberate and stays: the gate cannot parse shell semantics, so a
            # target-based rule would miss `cd website-canonical; echo x > f.html`, and a
            # false negative here publishes to the live site while a false positive only
            # costs a retry. What was missing was the diagnosis -- the operator had to
            # read this file to find out what matched (2026-07-14).
            block(
                "shell write into oxfordra.net site tree\n"
                "  matched site marker : %s\n"
                "  matched write verb  : %s\n"
                "  command             : %s"
                % (", ".join(markers), ", ".join(repr(i) for i in indicators), command.strip()),
                WEBSITE_WRITE, session_id,
                extra="  NOTE: both are matched ANYWHERE in the command, related or not. If this\n"
                      "  command does not actually write to the site tree (e.g. it only quotes a\n"
                      "  site path inside a string, heredoc, or commit message), do NOT create the\n"
                      "  override -- re-run it via the Edit/Write tool, or drop the marker text from\n"
                      "  the command. The override is for real site changes Gabriel just approved.\n")


def check_file_write(file_path, session_id):
    normalized = file_path.replace("\\", "/").lower()
    if any(marker in normalized for marker in SITE_PATH_MARKERS):
        if not override_active(session_id, WEBSITE_WRITE):
            block("write to oxfordra.net site tree: %s" % file_path, WEBSITE_WRITE, session_id)


def check_mcp(tool_name, session_id):
    """GATE 2c — Netlify MCP mutating tools. The deploy/project/extension *-updater
    tools push to prod / change live project config + CSP/headers with no Bash and no
    prompt; under bypassPermissions nothing else stops them. This gate stands in for
    the permission prompt they would otherwise raise (2026-06-13). Reader tools pass."""
    lowered = tool_name.lower()
    if "netlify" in lowered and lowered.endswith("-updater"):
        if not override_active(session_id, WEBSITE_DEPLOY):
            block("Netlify MCP mutating call (%s)" % tool_name, WEBSITE_DEPLOY, session_id)


def main():
    try:
        payload = json.load(sys.stdin)
        tool_name = payload.get("tool_name", "")
        tool_input = payload.get("tool_input", {}) or {}
        session_id = payload.get("session_id", "")
    except Exception:
        return  # fail open on malformed input

    # A missing/invalid session_id is NOT fatal here: it simply means _token_path() can
    # never resolve, so no override is reachable and every gated action blocks. Fail-closed
    # by construction -- including in scheduled/headless contexts, where a prod deploy or an
    # external send should never be self-authorizing anyway.
    if not isinstance(session_id, str):
        session_id = ""

    if tool_name == "Bash":
        check_bash(tool_input.get("command", "") or "", session_id)
    elif tool_name in ("Edit", "Write", "MultiEdit", "NotebookEdit"):
        check_file_write(tool_input.get("file_path", "") or "", session_id)
    elif tool_name.startswith("mcp__"):
        check_mcp(tool_name, session_id)


if __name__ == "__main__":
    main()
    sys.exit(0)
