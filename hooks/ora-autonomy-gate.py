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

OVERRIDE TOKENS (hardened 2026-07-16, Gabriel-ratified; shared contract since 2026-07-17)
-----------------------------------------------------------------------------------------
A token lives at:  hooks/sessions/<session_id>/overrides/<name>

and its content must be:

    scope: website-deploy
    session: <the session_id it was minted in>
    recipients: a@x.com, b@y.com     # external-send ONLY; every external recipient
    reason: <free text — for the human audit trail>

It may be created ONLY after Gabriel's explicit in-turn confirmation in a live session.

The contract itself -- path resolution and traversal defense, size cap, duplicate-key
refusal, TTL/clock-skew/future-dating, single-use consumption -- lives in
hooks/lib/override_tokens.py, SHARED with git-prepush-doctrine-gate.py. Read that module
for WHY the token has this shape (the four defects of the retired flat mtime-only sentinel,
each confirmed empirically) and for its HONEST LIMITS -- notably that session-scoping is
scoping, NOT authentication. It was inline here until 2026-07-17; two gates enforcing the
same security-critical rules from two copies is a drift hazard.

What stays THIS gate's own, because the shared contract cannot know it:
  - Severity split: a write grant cannot open a deploy, and vice versa (defect 2).
  - The recipient binding: an allow-external-send token must NAME every external recipient,
    so a token approving one counterparty cannot reach another. Rides into token_grants as
    its extra_check, and is evaluated BEFORE a single-use token is consumed.
  - Deploy/send tier: 5-minute TTL, consumed at gate-pass. "Gabriel just said yes" is short.

Everything fails CLOSED. No session_id, no token, wrong scope, wrong session, unparseable,
oversized, duplicate keys, future-dated, un-consumable, or an unnamed recipient -> block. A
false positive costs a retry; a false negative publishes to the live site.

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

# The token contract is SHARED with git-prepush-doctrine-gate.py (hooks/lib/override_tokens.py):
# path resolution + traversal defense, size cap, UTF-8, duplicate-key refusal, TTL with
# clock-skew tolerance and future-dating refusal, single-use consumption, and the
# ORA_OVERRIDE_SESSIONS_DIR test seam. It lived here inline until 2026-07-17; two gates
# enforcing the same security-critical rules from two copies is a drift hazard, and the
# copies had already begun to diverge (this one returned a bool, that one returns the parsed
# fields so `reason:` reaches the audit trail).
#
# The fallback below is NOT a looser local check -- it is the STRICTEST possible one: if the
# validator cannot be loaded, no override is reachable at all, so every gated action blocks.
#
# Getting here wrong is subtle, and an earlier version of this refactor did (adversarial
# review, 2026-07-17). Letting the ImportError propagate looks fail-closed and is NOT: a
# PreToolUse hook that exits 1 is treated as a NON-BLOCKING error and the tool call PROCEEDS
# -- so a broken shared module would have silently disabled Gates 1 and 2 and let a prod
# deploy through, leaving only a traceback the model never sees. Nor can we sys.exit(2) at
# import time: this hook runs on EVERY PreToolUse call, so that bricks the whole session
# (cf. the confidentiality-guard self-deadlock).
#
# So: degrade to "no override exists". Ungated calls still pass (availability preserved);
# every gated call finds no token, falls through to block(), and exits 2. Fail-closed exactly
# where it matters. This coupling is new -- the doctrine gate shares this module, so an edit
# made for its benefit can break this gate -- which is precisely why it must degrade safely.
try:
    from override_tokens import Tier, token_grants, token_path  # noqa: E402
    TOKEN_CONTRACT_LOADED = True
except Exception:
    TOKEN_CONTRACT_LOADED = False

    class Tier(object):
        """Inert stand-in so the tier table below still builds and block() can still render
        a message. Carries no validation logic -- token_grants is what refuses. If the real
        Tier gains a field this drifts, but only on a path where everything already blocks."""

        def __init__(self, name, scope, ttl, single_use=False, requires_extra_check=False):
            self.name = name
            self.scope = scope
            self.ttl = ttl
            self.single_use = single_use
            self.requires_extra_check = requires_extra_check

    def token_grants(session_id, tier, extra_check=None):
        return None  # no validator -> no grant, ever

    def token_path(session_id, name):
        return None

INTERNAL_DOMAIN = "@oxfordra.net"
RECIPIENT_FLAGS = ("-to", "-cc", "-bcc")  # any one means the send has external reach

WEBSITE_WRITE = Tier("allow-website-write", "website-write", 3600)
WEBSITE_DEPLOY = Tier("allow-website-deploy", "website-deploy", 300, single_use=True)
# requires_extra_check: an external-send token must NAME every external recipient. That
# binding is email domain logic (see _recipients_authorized), so the shared contract cannot
# evaluate it -- the flag makes token_grants refuse rather than skip it if a caller forgets.
EXTERNAL_SEND = Tier("allow-external-send", "external-send", 300, single_use=True,
                     requires_extra_check=True)

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


def _recipients_authorized(fields, external):
    """Every external recipient of the send must be named in the token.

    Gate 1's own binding, kept here rather than in the shared contract: override_tokens.py
    validates a token generically and knows nothing about email. Passed to token_grants as
    its extra_check, so it runs before a single-use token is consumed -- a token that fails
    it is refused WITHOUT being burned.
    """
    raw = fields.get("recipients")
    if not raw:
        return False
    allowed = {r.strip().lower() for r in raw.split(",") if r.strip()}
    if not allowed:
        return False
    return all(r.lower() in allowed for r in external)


def override_active(session_id, tier, external=None):
    """True iff a valid token authorizes `tier` for `session_id`. The generic contract
    (path, freshness, parse, scope, session, single-use consumption) is the shared module's;
    the recipient binding is this gate's and rides along as extra_check."""
    extra_check = None
    if tier.requires_extra_check:
        extra_check = lambda fields: _recipients_authorized(fields, external or [])  # noqa: E731
    return token_grants(session_id, tier, extra_check=extra_check) is not None


def block(reason, tier, session_id, extra=""):
    where = token_path(session_id, tier.name)
    if not TOKEN_CONTRACT_LOADED:
        # Say so explicitly: otherwise this looks like an ordinary block and someone burns
        # ten minutes writing a token that can never be honored.
        where = ("<hooks/lib/override_tokens.py could not be imported -- the token validator "
                 "is unavailable, so NO override can be honored. This gate is failing closed. "
                 "Fix the module; do not try to mint a token.>")
    elif where is None:
        where = ("<no valid session_id in this hook payload -- an override cannot be "
                 "created or honored here>")
    body = "  scope: %s\n  session: %s\n" % (tier.scope, session_id or "<none>")
    if tier.requires_extra_check:
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


def block_shape(tool_name, session_id):
    """Fail-closed exit for a gated tool whose input shape we cannot inspect. This is
    NOT an override-gated block (no token could make a malformed payload safe) -- it is a
    refusal to let an un-evaluable gated action proceed."""
    sys.stderr.write(
        "BLOCKED by ORA autonomy gate: %s call with an uninspectable input shape "
        "(tool_input not a dict, or the gated field not a string).\n"
        "This is a gated tool (hard invariant 1/2); its input could not be evaluated, so it "
        "fails closed. Re-issue the call with a well-formed tool_input.\n" % tool_name
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


FILE_TOOLS = ("Edit", "Write", "MultiEdit", "NotebookEdit")


def main():
    # ONLY an unparseable hook payload fails open -- blocking every tool call system-wide
    # when we cannot even read the hook input would brick the session; that availability
    # tradeoff is deliberate. Once we HAVE a parsed payload naming a gated tool, any
    # anomaly in it fails CLOSED (below): a false positive costs a retry, a false negative
    # publishes to the live site.
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return
    if not isinstance(payload, dict):
        return  # a non-object payload names no tool we can evaluate -> fail open

    tool_name = payload.get("tool_name", "")
    tool_input = payload.get("tool_input", {})
    session_id = payload.get("session_id", "")

    # A missing/invalid session_id is NOT fatal: it simply means token_path() can never
    # resolve, so no override is reachable and every gated action blocks. Fail-closed by
    # construction -- including in scheduled/headless contexts, where a prod deploy or an
    # external send should never be self-authorizing anyway.
    if not isinstance(session_id, str):
        session_id = ""

    if tool_name == "Bash":
        # A gated action whose input we cannot inspect must fail CLOSED, not error through
        # to exit 1 (which a PreToolUse hook treats as non-blocking). A real Bash call
        # always carries a dict tool_input with a string command, so this never over-blocks
        # a legitimate call (adversarial review, 2026-07-16).
        if not isinstance(tool_input, dict):
            block_shape("Bash", session_id)
        command = tool_input.get("command", "")
        if not isinstance(command, str):
            block_shape("Bash", session_id)
        check_bash(command, session_id)
    elif tool_name in FILE_TOOLS:
        if not isinstance(tool_input, dict):
            block_shape(tool_name, session_id)
        # NotebookEdit's tool param is `notebook_path`, not `file_path`; every other file
        # tool uses `file_path`. Read both so an enrolled tool is actually gated (a
        # notebook write into the site tree was a live invariant-2 bypass before this).
        file_path = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
        if not isinstance(file_path, str):
            block_shape(tool_name, session_id)
        check_file_write(file_path, session_id)
    elif isinstance(tool_name, str) and tool_name.startswith("mcp__"):
        # check_mcp reads only tool_name, so a malformed tool_input cannot affect it.
        check_mcp(tool_name, session_id)


if __name__ == "__main__":
    main()
    sys.exit(0)
