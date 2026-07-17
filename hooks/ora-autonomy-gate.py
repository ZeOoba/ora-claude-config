#!/usr/bin/env python3
r"""ORA autonomy gate (PreToolUse) — preserves the human gates under defaultMode=bypassPermissions.

With bypassPermissions, permission prompts never fire, so invariants 1 and 2 are enforced
here instead (hooks run in every mode, including scheduled/headless sessions):

  GATE 1 — external email: any send-via-outlook.ps1 invocation naming a recipient outside
           @oxfordra.net anywhere in the command is blocked, regardless of which flag (or
           flag alias/prefix) introduces it. Internal fleet sends (ggoldberg/egoldberg) pass
           untouched.
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

MATCHER HARDENING (2026-07-17, Gabriel-ratified — five detection gaps, independent of any
override token)
-------------------------------------------------------------------------------------------
Adversarial review of the token hardening above (four parallel lenses + personal spot-checks)
found that the underlying DETECTION matchers -- not the token layer -- had five real,
reproducible bypasses. Each let a real malicious command evade detection so completely that
no override was ever even needed: exit 0, no block, nothing to log.
  1. EMAIL_RE required a dot in the domain (`+` on the trailing group) -- `attacker@evilhost`
     (no TLD) was invisible to it. Fixed: `*` (zero-or-more), so a dotless recipient is still
     email-shaped and still caught.
  2. RECIPIENT_FLAGS gated Gate 1 on the literal substrings -to/-cc/-bcc. send-via-outlook.ps1
     has exactly one parameter starting with T ($To), so PowerShell's unambiguous-prefix
     binder resolved a bare `-T` to `-To` while never containing "-to". Fixed by DROPPING the
     flag precondition entirely: if send-via-outlook.ps1 appears in the command, scan for an
     external-shaped recipient anywhere in it, full stop -- closes this AND every other
     possible flag alias at once, and is strictly no looser (a command with no recipient text
     still finds nothing).
  3/4. NETLIFY_INVOKE_RE anchored "netlify" to a command-boundary position (start, after
     ;/&/|/$() ) specifically so quoting/echoing wouldn't trip it -- but `cmd /c netlify
     deploy --prod` and `powershell -Command "netlify deploy --prod"` both precede "netlify"
     with a space or a quote, never the anchor set, and both reached exit 0. Fixed by
     de-anchoring to a bare word-boundary match, same breadth-over-precision tradeoff Gate 2b's
     site marker already makes deliberately (see check_bash's comment there): closes both
     indirection forms and any future wrapper (bash -c, Invoke-Expression, a doskey macro) at
     once, at the cost of also tripping on a commit message that merely mentions the phrase --
     a false positive costs a retry; a false negative publishes to the live site.
  5. check_file_write matched only the LITERAL file_path substring -- a directory
     junction/symlink pointing INTO the site tree from an innocuous-looking name (whose own
     path text names no site marker) evaded it entirely. Fixed: also check os.path.realpath()
     (follows junctions/symlinks to their real target; works even for a not-yet-existing file,
     the ordinary Write-a-new-file case). Residual, accepted gap: cannot help a relative
     file_path evaluated against a different effective cwd than this hook process's -- but
     Claude Code's Write/Edit/NotebookEdit tools are documented to always pass an absolute
     path, so that shape is a tool-contract violation, not something this gate can close.

All five were personally reproduced against the live gate with a passing control before the
fix (the equivalent already-blocked form) and locked in as regression tests in
hooks/tests/test-ora-autonomy-gate.py. Survived a 3-round independent adversarial gauntlet
(each round explicitly tasked with trying to break the PRIOR round's fix) before landing --

HONEST LIMIT (found by Round 1 of that gauntlet, Gabriel-acknowledged, follow-up scoped
separately -- NOT fixed by the five patches above, and cannot be by better regexes on one
command's text): a recipient or executable reference built via VALUE INDIRECTION --
a PowerShell variable, string concatenation, `Get-Content` on a file, an environment
variable set in an EARLIER Bash call -- is invisible to a detector that only scans the
literal text of the CURRENT command. Proven live: `$to = $a + '@' + $b + '.' + $c; ...
-To $to` reaches Gate 1 unblocked; splitting `$env:D = 'net'+'lify'` into one Bash call and
`& $env:D deploy --prod` into a second reaches Gate 2a unblocked -- neither call's text ever
contains all the required literal substrings together, though the two together perform a
real deploy. This is NOT new: the ORIGINAL anchored NETLIFY_INVOKE_RE and the ORIGINAL
flag-gated EMAIL_RE were equally blind to it before 2026-07-17 -- it is a structural ceiling
of "detect by parsing shell text", not a regression these fixes caused or could have
prevented. Closing it for real means enforcing at the actual outbound action (wrapping the
netlify CLI/API call or the Outlook send itself) rather than the invoking shell command --
a different architecture, scoped as separate follow-up work, not a patch to this file. See
hooks/tests/ for the accumulated regression coverage from all three rounds.

ALSO DEFERRED to the same follow-up (Round 2 of the gauntlet, same category: referring to a
sensitive target via an alternate reference rather than its literal canonical form, not
fixable by better regexes on literal text):
  - Hardlinking (or an already-defined shell alias/function/profile wrapper for) another name
    to send-via-outlook.ps1's content, then invoking THAT name -- the substring
    "send-via-outlook.ps1" never appears in the command at all.
  - Single-command string-BUILDING of "netlify" via concatenation evaluated by PowerShell
    within one `-Command "..."` argument (e.g. `& ('net'+'lify') deploy --prod`) -- the literal
    contiguous word never appears in the raw text for the word-boundary regex to match, even
    though it is one Bash tool call, not two.
  - A file-level HARDLINK from an innocuous-looking outside path to an existing file inside the
    site tree: os.path.realpath() (fix #5) resolves symlinks/junctions by following a stored
    target, but a hardlink has no target to resolve -- both names are equally "real" paths to
    the same inode, and check_file_write only ever sees the outside one. Closing this would need
    inode/`st_ino` comparison against the live site tree, not path resolution -- a different,
    heavier mechanism, not a quick patch.

ROUND 3 FIXES (final gauntlet round, 2026-07-17):
  6b. NFKC (fix 6) folds compatibility forms (fullwidth, mathematical-alphanumeric) but does
      NOT strip zero-width/format characters (Cf: ZWSP U+200B, RTL override U+202E, ...) or
      combining marks (Mn: e.g. combining low line U+0332) inserted MID-WORD -- these break
      the contiguous `\bnetlify\b` / EMAIL_RE match without being visible. Proven live: a ZWSP
      inside "netlify" or inside "send-via-outlook.ps1" (breaking the trigger phrase itself)
      or inside a recipient's local-part all reached exit 0. Fixed: strip Cf/Mn category
      characters (after NFKC) before any matching -- legitimate infra command/path text has
      no legitimate reason to contain them.
  7b. check_mcp gated only tools ending in "-updater" (an allow-by-default deny-list of one
      suffix) -- a hypothetical netlify MCP tool with any other mutating-shaped name would
      evade it entirely (not proven against a currently-registered tool, but the matcher
      itself is provably narrow). Fixed: invert to deny-by-default -- gate anything
      containing "netlify" that does NOT end in "-reader", rather than allow anything that
      doesn't end in "-updater". Every real reader tool in the current connector (deploy/
      extension/project/team/user-services-reader) still passes; every current and any
      future mutating tool is now gated regardless of its exact suffix.
  8. FOUNDATIONAL, found while verifying fix 6b: main()'s `json.load(sys.stdin)` decoded
     using sys.stdin's PLATFORM-DEFAULT encoding (cp1252 on this machine), not UTF-8. A real
     multi-byte UTF-8 payload byte does not reliably raise under that decoder -- it SILENTLY
     MOJIBAKES. Proven live: a UTF-8-encoded soft hyphen (2 bytes: 0xC2 0xAD) decoded as
     cp1252 became TWO wrong characters, one of them a spurious VISIBLE character that broke
     a `\bnetlify\b` match which should have blocked -- undermining every Unicode fix in this
     file (6, 6b, 7b) for any invocation whose payload contains literal, non-\uXXXX-escaped
     non-ASCII bytes. Every OTHER test in this suite is blind to this because Python's own
     json.dumps(ensure_ascii=True) default already escapes non-ASCII to plain ASCII \uXXXX --
     but a serializer that does NOT ascii-escape (e.g. JavaScript's JSON.stringify, plausibly
     what the real harness uses) would not. Fixed: `sys.stdin.reconfigure(encoding="utf-8",
     errors="strict")` before reading, same pattern as git-prepush-doctrine-gate.py's
     stdout/stderr reconfigure. `errors="strict"` deliberately, not "replace" -- a genuinely
     malformed (non-UTF-8) byte sequence should raise and hit the existing, already-documented
     fail-open-on-unparseable-input path, not get silently replaced with U+FFFD (which could
     reintroduce the same class of spurious-character corruption this fix closes).

STILL NOT IN SCOPE (deliberately): Gate 2b's BREADTH itself -- SITE_PATH_MARKERS and
SITE_WRITE_INDICATORS matching ANYWHERE in a command, unrelated occurrences included. See
memory/feedback_autonomy_gate_matcher_cannot_be_safely_narrowed.md — three adversarial review
rounds each found a real bypass in one 2026-07-16 attempt to NARROW that specific matcher
(make it require the marker and indicator to be related); the broad match there is correct
and stays untouched. Today's fixes are the opposite direction (WIDENING detection to close
false negatives elsewhere), which is a different risk profile, not a re-litigation of that
finding.
"""
import json
import os
import re
import sys
import unicodedata

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
    # EXTERNAL_SEND is SHARED with check_external_send.py (send-via-outlook.ps1's own
    # outbound-action check, 2026-07-17 -- see email_send_tier.py's module docstring for
    # why: the two enforcement points must never diverge on what "authorized" means).
    # Imported in the SAME try so a broken email_send_tier.py degrades exactly as fail-
    # closed as a broken override_tokens.py -- see the fallback block below.
    from email_send_tier import EXTERNAL_SEND, INTERNAL_DOMAIN, is_external, \
        recipients_authorized as _recipients_authorized  # noqa: E402
    # WEBSITE_DEPLOY is SHARED with check_website_deploy.py (the netlify CLI wrapper's own
    # outbound-action check, website-canonical/scripts/netlify-guard.js, 2026-07-17 -- same
    # rationale as EXTERNAL_SEND/email_send_tier.py above: the two enforcement points must
    # never diverge on what "authorized" means). Imported in the SAME try so a broken
    # website_deploy_tier.py degrades exactly as fail-closed as a broken override_tokens.py.
    from website_deploy_tier import WEBSITE_DEPLOY  # noqa: E402
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
    EXTERNAL_SEND = Tier("allow-external-send", "external-send", 300, single_use=True,
                         requires_extra_check=True)
    WEBSITE_DEPLOY = Tier("allow-website-deploy", "website-deploy", 300, single_use=True)

    def is_external(address):
        return not address.lower().endswith(INTERNAL_DOMAIN)

    def _recipients_authorized(fields, external):
        return False  # no validator -> no grant, ever (mirrors token_grants above)

WEBSITE_WRITE = Tier("allow-website-write", "website-write", 3600)

# Mutating shell ops; if one of these co-occurs with a site-path marker in a Bash
# command, treat it as a write into the oxfordra.net tree (Gate 2). Read-only verbs
# (cat/type/get-content/grep) without a redirect do not appear here -> they pass.
SITE_WRITE_INDICATORS = (
    ">", "cp ", "copy ", "mv ", "move ", "rm ", "del ", "remove-item",
    "set-content", "add-content", "out-file", "tee ", "new-item",
)
# Domain group is `*` (zero-or-more dot segments), not `+`: a `+` required at least one
# dot, so a dotless recipient like `attacker@evilhost` was INVISIBLE to this regex --
# findall() returned nothing, `external` was empty, and Gate 1 never fired at all: exit 0,
# zero override needed. Proven live 2026-07-17 (adversarial review): attacker@evilhost ->
# exit 0 unblocked; attacker@evilhost.com -> exit 2 blocked, as a control. `*` matches both.
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)*", re.IGNORECASE)
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
# Matches "netlify" (or netlify-cli/.cmd/.exe) as a whole word ANYWHERE in the command --
# no command-boundary anchor. The prior version anchored to a leading-token position
# (start, after ;/&/|/$() ) specifically so quoting/echoing/logging the phrase wouldn't
# trip the gate -- but that same anchor let `cmd /c netlify deploy --prod` and
# `powershell -Command "netlify deploy --prod"` through completely unblocked (netlify is
# preceded by a space or a quote in both, never by the anchor set). Proven live
# 2026-07-17: both indirection forms reached exit 0 before this fix, against a plain
# `netlify deploy --prod` control at exit 2. De-anchoring closes both AND any future
# subshell/wrapper form (bash -c, sh -c, Invoke-Expression, a doskey macro, ...) without
# having to enumerate each one -- the same breadth-over-precision tradeoff Gate 2b's site
# marker already makes deliberately (see check_bash's own comment on that gate): a false
# positive (a commit message or echo that merely mentions the phrase) costs a retry; a
# false negative here publishes to the live site. Combined, as before, with `deploy` and
# `--prod` also required anywhere in the command.
NETLIFY_INVOKE_RE = re.compile(r"\bnetlify(?:-cli)?(?:\.cmd|\.exe)?\b", re.IGNORECASE)
# Windows auto-generates an 8.3 short name for every long filename on an 8.3-enabled NTFS
# volume (this one is) with ZERO setup -- confirmed live: send-via-outlook.ps1 -> SEND-V~1.PS1
# (`dir /x`). Referencing the script by that alias reached exit 0 (Round 2 adversarial review,
# 2026-07-17): the "send-via-outlook.ps1" substring check never saw it. Unlike a deliberately
# hardlinked alias (deferred -- see the docstring's "ALSO DEFERRED" section), this is a
# passive, standing alternate name for this ONE known, fixed script, worth naming directly.
# Matches the known short-name family (~1, ~2, ... if a future colliding file bumps the digit).
SEND_SHORTNAME_RE = re.compile(r"\bsend-v~\d\.ps1\b", re.IGNORECASE)
# Unicode categories stripped by _normalize_for_matching, ON TOP OF NFKC: Cf (format --
# zero-width space U+200B, RTL/LTR override U+202E/U+202D, soft hyphen, ...) and Mn
# (nonspacing combining marks -- e.g. combining low line U+0332). NFKC folds COMPATIBILITY
# forms (fullwidth, mathematical-alphanumeric) to ASCII but does NOT remove these -- a ZWSP
# inserted mid-word (`net<ZWSP>lify`, or inside `send-via-outlook.ps1` itself, breaking the
# Gate 1 trigger phrase) breaks a `\bword\b` match invisibly. Proven live 2026-07-17 (Round 3
# adversarial review): both reached exit 0. Legitimate infra command/path text has no
# legitimate reason to contain either category, so stripping them is a safe, targeted
# hardening, not a breadth tradeoff like the site-marker/netlify de-anchoring above.
_STRIP_CATEGORIES = ("Cf", "Mn")


def _normalize_for_matching(text):
    """NFKC-fold compatibility Unicode forms, then strip invisible format/combining
    characters, so detection matches what a human reads rather than raw codepoints."""
    folded = unicodedata.normalize("NFKC", text)
    return "".join(ch for ch in folded if unicodedata.category(ch) not in _STRIP_CATEGORIES)


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
    # Normalize before any matching: a fullwidth Unicode "@" (U+FF20) is invisible to
    # EMAIL_RE's literal ASCII "@", so `attacker＠evilhost.com` reached exit 0 (Round 2
    # adversarial review, 2026-07-17); a zero-width space or RTL override inserted mid-word
    # (`net<ZWSP>lify`, or inside the Gate 1 trigger phrase itself) breaks a `\bword\b` match
    # invisibly and NFKC alone doesn't remove it (Round 3). _normalize_for_matching does
    # both: NFKC-fold, then strip Cf/Mn characters. `command` (original, un-normalized) is
    # kept for display in block messages; all matching uses `normalized`/`lowered` from here.
    normalized = _normalize_for_matching(command)
    lowered = normalized.lower()
    # GATE 1 — any send-via-outlook.ps1 invocation naming an external recipient anywhere
    # in the command. Previously gated on a RECIPIENT_FLAGS substring check (-to/-cc/-bcc)
    # as a precondition -- but PowerShell resolves an unambiguous parameter-name PREFIX
    # (send-via-outlook.ps1's param block has exactly one parameter starting with T: $To),
    # so `-T attacker@x.com` bound to -To while never containing the substring "-to".
    # Proven live 2026-07-17: reached exit 0 (unblocked) before this fix. Dropping the flag
    # precondition entirely closes this AND every other possible flag spelling/alias at
    # once: if send-via-outlook.ps1 appears in the command, just look for any external-
    # shaped recipient anywhere in it. A command with no recipient text at all still finds
    # nothing via EMAIL_RE and passes, same as before -- this is strictly no looser.
    # ALSO checks the script's standing 8.3 short-name alias (SEND-V~1.PS1) -- see
    # SEND_SHORTNAME_RE's own comment.
    if "send-via-outlook.ps1" in lowered or SEND_SHORTNAME_RE.search(lowered):
        recipients = EMAIL_RE.findall(normalized)
        external = sorted({r for r in recipients if is_external(r)})
        if external and not override_active(session_id, EXTERNAL_SEND, external):
            block("external email recipient(s): %s" % ", ".join(external), EXTERNAL_SEND,
                  session_id,
                  extra="The token must NAME each external recipient: a token approving a\n"
                        "send to one counterparty does not authorize a send to another.\n")
    # GATE 2a — production deploy via the netlify CLI.
    if NETLIFY_INVOKE_RE.search(normalized) and "deploy" in lowered and "--prod" in lowered:
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
    # Check both the literal path text AND its OS-resolved real path. A directory
    # junction/symlink pointing INTO the site tree from an innocuous-looking name (whose
    # own path text names no site marker) previously evaded this entirely -- the check was
    # pure substring matching on file_path as given. realpath() follows junctions/symlinks
    # to their real target even when the final path component doesn't exist yet (the
    # ordinary case for Write creating a new file), so a junction is now caught via its
    # resolved destination. Proven live 2026-07-17 (adversarial review): a write through a
    # junction into a site-tree target reached exit 0 (unblocked) before this fix.
    # Residual, accepted gap: this cannot help if file_path itself is relative AND the
    # underlying tool's actual cwd differs from this hook process's cwd -- but Claude
    # Code's Write/Edit/NotebookEdit tools are documented to always supply an absolute
    # path, so that shape is a tool-contract violation, not a gap this gate can close.
    # Normalize before matching too, for consistency with check_bash (a fullwidth/
    # compatibility form or an invisible Cf/Mn character in a path component would otherwise
    # evade the plain marker substring check the same way it did for EMAIL_RE/NETLIFY_INVOKE_RE
    # -- not proven exploitable here, but cheap and closes the same class of gap defensively).
    normalized_path = _normalize_for_matching(file_path)
    normalized = normalized_path.replace("\\", "/").lower()
    try:
        resolved = os.path.realpath(normalized_path).replace("\\", "/").lower()
    except OSError:
        resolved = normalized
    if any(marker in normalized for marker in SITE_PATH_MARKERS) or \
            any(marker in resolved for marker in SITE_PATH_MARKERS):
        if not override_active(session_id, WEBSITE_WRITE):
            block("write to oxfordra.net site tree: %s" % file_path, WEBSITE_WRITE, session_id)


def check_mcp(tool_name, session_id):
    """GATE 2c — Netlify MCP mutating tools. The deploy/project/extension *-updater
    tools push to prod / change live project config + CSP/headers with no Bash and no
    prompt; under bypassPermissions nothing else stops them. This gate stands in for
    the permission prompt they would otherwise raise (2026-06-13). Reader tools pass.

    Deny-by-default, not allow-by-default: gate anything containing "netlify" that does
    NOT end in "-reader", rather than gating only tools that DO end in "-updater". The
    prior form was an allow-by-default deny-list of one exact suffix -- a mutating tool
    with any other name (a future connector, or a differently-spelled write tool) would
    have evaded it silently (Round 3 adversarial review, 2026-07-17). Every real reader
    tool in the current connector (deploy/extension/project/team/user-services-reader)
    still passes; every current AND any future mutating tool is now gated regardless of
    its exact suffix."""
    lowered = tool_name.lower()
    if "netlify" in lowered and not lowered.endswith("-reader"):
        if not override_active(session_id, WEBSITE_DEPLOY):
            block("Netlify MCP mutating call (%s)" % tool_name, WEBSITE_DEPLOY, session_id)


FILE_TOOLS = ("Edit", "Write", "MultiEdit", "NotebookEdit")


def main():
    # sys.stdin.encoding defaults to the PLATFORM codepage (cp1252 on this Windows machine),
    # not UTF-8. Reading a real multi-byte UTF-8 payload byte through that decoder does NOT
    # reliably raise -- it SILENTLY MOJIBAKES: proven live 2026-07-17, a UTF-8-encoded soft
    # hyphen (2 bytes: 0xC2 0xAD) decoded under cp1252 became TWO wrong characters (an
    # injected 'Â' plus the soft hyphen), inserting a spurious VISIBLE character that broke a
    # `\bnetlify\b` match which should have blocked. This silently undermines every Unicode
    # fix in this file for any REAL invocation whose payload contains literal (non-\uXXXX-
    # escaped) non-ASCII bytes -- which Python's own json.dumps(ensure_ascii=True) avoids
    # (why the test suite's fullwidth-@/ZWSP/RTL/combining-mark tests all passed despite this
    # bug), but a JSON serializer that does NOT ascii-escape (e.g. JavaScript's
    # JSON.stringify, plausibly what the real harness uses) would not. Reconfigure BEFORE
    # reading, same pattern as git-prepush-doctrine-gate.py's stdout/stderr reconfigure.
    try:
        sys.stdin.reconfigure(encoding="utf-8", errors="strict")  # type: ignore[attr-defined]
    except Exception:
        pass
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
