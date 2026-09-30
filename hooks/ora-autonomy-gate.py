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
  GATE 1b — ms365 MCP email sends (outlook_send_mail / outlook_forward_mail /
           outlook_send_draft): blocked unless EVERY recipient is strictly @oxfordra.net
           (full-string match: lookalike domains, display-name forms, and a list smuggled into
           one string all count as external). outlook_send_draft carries no recipients, so it
           always needs a token, and the token must name `draft:<messageId>`.
           Override: allow-external-send (same tier and binding as GATE 1).
  GATE 1c — Teams MCP sends (teams_send_chat_message / teams_send_channel_message /
           teams_reply_channel_message): always blocked without a token naming the destination
           (`teams:<chatId>` or `teams:<teamId>/<channelId>`).
           Override: allow-external-send (same tier and binding as GATE 1).
  GATE 3 — HubSpot CMS MCP writes (manage_blog_post / manage_landing_page /
           manage_website_page): an exact-case ALLOWLIST of read actions passes; every other
           action, an unknown action, BATCH, or a malformed input is a write and blocks. A
           website-page PUBLISH/REMOVE/RESTORE/NAV_* with an explicit mode="PREVIEW" writes
           nothing and passes. Override: allow-hubspot-cms-write (scope hubspot-cms-write,
           10 min, multi-use: a page edit is several calls ending in a publish).
  Gates 1b/1c/3 match on the tool-name SUFFIX after the last "__", so a reinstalled
  connector with a new id stays gated. They fail CLOSED on any anomaly once a gated tool is
  named, including a payload too malformed to parse. This gate covers Claude Code sessions
  and the CC/MCP scheduled fleet only; hooks do not run inside Cowork (LAMS) sessions.

  KNOWN RESIDUALS (adversarial review, 2026-09-30 -- accepted, not silently ignored):
   * A draft-send token names the DRAFT, not its contents. outlook_update_draft /
     outlook_create_draft are deliberately ungated (drafting is the normal Outlook-pane
     workflow), so a draft can be re-pointed at a new recipient after Gabriel approves its id.
     The window is the token TTL (5 min, single-use). Approve a draft only after reading its
     final recipients.
   * NOT covered: outlook_create_event / update_event / delete_event / respond_to_event (they
     email invitees or cancel with a comment) and outlook_set_vacation (free-text auto-replies
     to outside senders), plus outlook_create_filter. Follow-up.
   * The confidentiality-guard matcher in settings.json names the retired Composio tools
     (OUTLOOK_SEND...), so ms365 sends get no confidential-term scan. Separate fix.
   * Tool names that change (e.g. a renamed "..._v2") are not matched; the tests pin the
     current connector's names.

Exit 2 = block (stderr is shown to the model). Unparseable input fails open so a hook
malfunction never bricks every tool call -- EXCEPT an unparseable payload that still names a
gated MCP tool (a send, a CMS write, a Netlify write), which fails closed (see GATE 1b/1c/3).

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

2026-09-18 -- check_file_write ONLY: Claude-managed slug-directory exemption.
  Claude Code derives a directory name from the project path -- `~/.claude/projects/
  C--Users-Owner-website-canonical/` and `%TEMP%/claude/C--Users-Owner-website-canonical/
  <session>/scratchpad/`. Those SLUGS embed a site marker, so check_file_write blocked
  every Write to this session's own memory directory and to the harness-mandated
  scratchpad -- neither of which is the site tree at all. Confirmed live 2026-09-18:
  exit 2 on both, with the site-tree controls blocking correctly alongside. A session in
  this project therefore could not save a memory without minting a live-site write
  override, which is strictly worse than the write it actually wanted.
  This is NOT a re-litigation of the paragraph below. That paragraph is about Gate 2b's
  BASH matcher, where the undecidable question is "which command consumes this quoted
  token, and does that command write" -- four attempts, four confirmed bypasses (see
  memory/feedback_autonomy_gate_matcher_cannot_be_safely_narrowed.md, incl. the Round 4
  real-tokenizer attempt). Here there is no shell, no quoting and no argv: one absolute
  path, and realpath() answers the only question asked -- where do the bytes land.
  The exemption is keyed on the RESOLVED real path, deliberately not on the literal path
  text: the resolved path is where the write truly goes, so a junction/symlink named to
  look like a memory or scratchpad directory while pointing into the site tree resolves
  back OUT of the exemption and still blocks. Fail-closed on every uncertainty -- if
  realpath() raises, or the path is not a normalization fixed point, or an anchor root
  cannot be resolved, or an anchor root itself sits inside the site tree, no exemption
  exists and the block stands. See _SLUG_DIR_EXEMPTIONS and check_file_write.
  The first draft of this got the central claim WRONG and an adversarial pass caught it:
  it resolved the NORMALIZED path while the tool opens the LITERAL one, so "realpath()
  answers where the bytes land" was false for every path the two disagree on -- three
  proven exit-0 writes into a site checkout. Fixed in check_file_write; the same pass also
  found that this predates the exemption (a junction whose name carries an invisible
  character bypassed the plain marker match on main too, no slug involved), so the raw
  path's realpath is now marker-matched unconditionally, exemption or not.
  ACCEPTED RESIDUAL (TOCTOU, new with this exemption, cannot be closed here): between this
  hook's realpath() and the tool's open(), a concurrent process from the same session could
  swap an exempt directory for a junction into the site tree. Pre-exemption, slug-named
  paths blocked on literal text regardless of filesystem state, so the race had no window;
  now the window is hook-exit to tool-open. A PreToolUse hook structurally cannot close it
  -- only a PostToolUse verifier that re-resolves the path AFTER the write can see that
  state. Logged as a follow-up, not a blocker: winning the race requires an already-
  compromised session, which has cheaper paths to the same outcome.

STILL NOT IN SCOPE (deliberately): Gate 2b's BREADTH itself -- SITE_PATH_MARKERS and
SITE_WRITE_INDICATORS matching ANYWHERE in a command, unrelated occurrences included. See
memory/feedback_autonomy_gate_matcher_cannot_be_safely_narrowed.md — three adversarial review
rounds each found a real bypass in one 2026-07-16 attempt to NARROW that specific matcher
(make it require the marker and indicator to be related); the broad match there is correct
and stays untouched. Today's fixes are the opposite direction (WIDENING detection to close
false negatives elsewhere), which is a different risk profile, not a re-litigation of that
finding.
"""
import inspect
import json
import os
import re
import sys
import tempfile
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

try:
    from text_normalization import STRIP_CATEGORIES  # noqa: E402
    # Shape-validate the shared value before trusting it -- the same defensive move the
    # override_tokens `consume`-signature check below makes for the same reason. A module
    # that imports cleanly but exports the wrong TYPE (None, an int, a list of ints) does
    # not fail here; it raises inside _normalize_for_matching on EVERY call, and an
    # uncaught exception exits 1 -- non-blocking, i.e. BOTH gates silently off on every
    # tool call in the session. Confirmed 2026-09-18: `STRIP_CATEGORIES = None` produced
    # exit 1 even for a benign `git status`. Wrong shape routes to the fallback instead.
    if (not isinstance(STRIP_CATEGORIES, tuple) or not STRIP_CATEGORIES
            or not all(isinstance(c, str) for c in STRIP_CATEGORIES)):
        raise TypeError("STRIP_CATEGORIES must be a non-empty tuple of str")
except BaseException:
    # Fallback matches text_normalization.py's current value, and exists for exactly the
    # reason the SITE_PATH_MARKERS one does: an uncaught ImportError here exits 1, which
    # PreToolUse treats as a NON-BLOCKING error -- the tool call PROCEEDS and BOTH gates
    # are silently off. A stale-but-present tuple is strictly better than no gate.
    #
    # BaseException, deliberately wider than the SITE_PATH_MARKERS block above it: a
    # shared module that called sys.exit() at import time raises SystemExit, which
    # `except Exception` does NOT catch -- and sys.exit(0) in particular would take this
    # hook to exit 0, disarming every gate with no error at all. Contrived for a constants
    # module, but the cost of the wider catch is nil and the failure is silent.
    #
    # This copy is pinned to the canonical tuple by
    # test-ora-autonomy-gate.py::test_strip_categories_fallback_matches_shared_module,
    # which reads this literal out of the source and compares it to the shared module.
    # A fallback nothing pins is just the pre-2026-09-18 duplicate under another name.
    STRIP_CATEGORIES = ("Cf", "Mn")

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
    # SIGNATURE GUARD (2026-08-24, adversarial review of the consume-param fix below): a
    # plain `from ... import token_grants` succeeds even against an OLDER override_tokens.py
    # that predates the `consume` keyword this file now always passes -- the import itself
    # cannot fail on a missing parameter, only a call can. Left unchecked, that call raises
    # TypeError at every gated action, which the PreToolUse dispatcher (pretooluse-
    # dispatcher.py) does NOT treat as a block (only an explicit sys.exit(2) blocks) -- so a
    # version-skewed shared module (this environment routinely runs several concurrent
    # sessions and worktrees against a shared ~/.claude checkout; override_tokens.py is
    # edited for the doctrine gate too) would silently fail OPEN instead of closed, defeating
    # the entire point of the except-Exception fallback below. Forcing the check here, before
    # TOKEN_CONTRACT_LOADED is set True, routes an incompatible module through that same
    # fallback -- every gated action blocks, exactly like any other broken-module case.
    if "consume" not in inspect.signature(token_grants).parameters:
        raise ImportError(
            "override_tokens.token_grants() is missing the 'consume' parameter -- "
            "stale/skewed shared module; degrading to the fail-closed stub"
        )
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

    def token_grants(session_id, tier, extra_check=None, consume=True):
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
# HubSpot CMS pages/posts are public-facing content (CLAUDE.md: publishing or modifying public
# content needs explicit permission). Multi-use on purpose: a page edit is several calls that
# end in a publish, and each call would otherwise need its own approval.
HUBSPOT_CMS_WRITE = Tier("allow-hubspot-cms-write", "hubspot-cms-write", 600)

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
# The stripped-category set (Cf format characters, Mn combining marks) is SHARED with
# tool_call_paths.py via hooks/lib/text_normalization.py (2026-09-18) -- imported at the top
# of this file with a pinned fallback. It was an independent copy of the same tuple here
# until then, and nothing kept the two in sync; read that module for the Round 3 (2026-07-17)
# rationale, for why the two consumers share the CONSTANT but deliberately NOT the matcher,
# and for the path-ordering rule.


def _normalize_for_matching(text):
    """NFKC-fold compatibility Unicode forms, then strip invisible format/combining
    characters, so detection matches what a human reads rather than raw codepoints.

    str-ONLY, deliberately -- see text_normalization.py. main() has already rejected a
    non-str command/file_path with block_shape() (exit 2, fail CLOSED) before any caller
    reaches here, so a "return '' on non-str" guard would not add safety: it would replace
    that fail-closed refusal with an empty string that matches no marker."""
    folded = unicodedata.normalize("NFKC", text)
    return "".join(ch for ch in folded if unicodedata.category(ch) not in STRIP_CATEGORIES)


def override_active(session_id, tier, external=None, consume=True):
    """True iff a valid token authorizes `tier` for `session_id`. The generic contract
    (path, freshness, parse, scope, session, single-use consumption) is the shared module's;
    the recipient binding is this gate's and rides along as extra_check.

    consume=False for a PEEK (2026-08-24 dual-layer-consumption fix -- full rationale in
    override_tokens.token_grants' own docstring): pass it at any PreToolUse call site whose
    gated action has its OWN downstream internal check (send-via-outlook.ps1's
    check_external_send.py, netlify-guard.js's check_website_deploy.py) -- that internal
    check is the sole intended consumer for single-use tiers on those paths. A call site
    with no such downstream check (e.g. the Netlify MCP mutating-tool gate below, which has
    no wrapped-binary layer to defer to) must keep the default consume=True: it is the only
    enforcement point for that action, so it must be the one that spends the grant."""
    extra_check = None
    if tier.requires_extra_check:
        extra_check = lambda fields: _recipients_authorized(fields, external or [])  # noqa: E731
    return token_grants(session_id, tier, extra_check=extra_check, consume=consume) is not None


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
        # consume=False (2026-08-24): this is the fast, indirection-blind pre-check (see the
        # module docstring's ALSO DEFERRED section); check_external_send.py inside
        # send-via-outlook.ps1 itself is the indirection-proof backstop and the documented
        # sole consumer of a single-use allow-external-send token. Consuming here as well
        # left that backstop denying an already-authorized send with no token left to find --
        # proven live on the WEBSITE_DEPLOY sibling of this exact pattern, same root cause.
        if external and not override_active(session_id, EXTERNAL_SEND, external, consume=False):
            block("external email recipient(s): %s" % ", ".join(external), EXTERNAL_SEND,
                  session_id,
                  extra="The token must NAME each external recipient: a token approving a\n"
                        "send to one counterparty does not authorize a send to another.\n")
    # GATE 2a — production deploy via the netlify CLI.
    # consume=False (2026-08-24): this text-scan is explicitly documented above as
    # structurally blind to value indirection -- netlify-guard.js's check_website_deploy.py
    # is the indirection-proof backstop and the documented sole consumer of a single-use
    # allow-website-deploy token here. Consuming at this layer too meant a single, correctly
    # authorized `netlify deploy --build --prod` could never pass both layers: this gate
    # burned the token to let the Bash command run, then netlify-guard.js's own check found
    # nothing left and denied it. Proven live 2026-08-24 (the incident that prompted this
    # fix). Gate 2c below (Netlify MCP mutating tools) has no such downstream layer to defer
    # to, so it deliberately keeps the default consume=True -- it is the only checker there.
    if NETLIFY_INVOKE_RE.search(normalized) and "deploy" in lowered and "--prod" in lowered:
        if not override_active(session_id, WEBSITE_DEPLOY, consume=False):
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
                      "  override -- the override grants live write access to oxfordra.net and is\n"
                      "  strictly worse than the read you wanted.\n"
                      "  IF THIS WAS A READ (2026-08-05, 3 same-session false positives on grep/ls/\n"
                      "  heredocs over the same day): use the Read/Grep/Glob tools instead -- never\n"
                      "  gated by this check -- or drop the site marker text from the shell command\n"
                      "  (e.g. avoid naming 'website-canonical' or 'oxford-site' in the cwd/args).\n"
                      "  IF THIS WAS A GENUINE EDIT (Edit/Write/MultiEdit to a site file): use those\n"
                      "  tools directly rather than a shell redirect -- they carry their own gate.\n")


def _exemption_anchor(path):
    """Resolve one Claude-managed root to a lowercased, slash-normalized prefix.

    Returns None -- meaning "no exemption is reachable through this root" -- if the root
    cannot be resolved, or if the root ITSELF sits inside the site tree. That second
    guard is what keeps the exemption from ever widening into a site-write hole: if this
    whole hook layer were somehow relocated under a site checkout (a `.claude/` inside
    the site repo, or `~/.claude` junctioned into one), the anchor is discarded and
    check_file_write falls back to its pre-2026-09-18 unconditional block.
    """
    try:
        resolved = os.path.realpath(path).replace("\\", "/").lower().rstrip("/")
    except (OSError, ValueError):
        return None
    if not resolved or any(marker in resolved for marker in SITE_PATH_MARKERS):
        return None
    return resolved + "/"


# Anchors are resolved ONCE at import: a per-call realpath() of a fixed root buys nothing
# and this hook runs on every file write.
#   - _CLAUDE_HOME is derived from THIS file's own location (hooks/ -> .claude/), never a
#     hardcoded user path, so the exemption follows the installation rather than assuming
#     one. Deliberately no test seam: the anchor must describe the real tree a write lands
#     in, and an env-overridable anchor would itself be the bypass.
#   - The temp roots are EVERY value of TEMP/TMP/TMPDIR (see _temp_dir_names), because the
#     harness and Python disagree about which one wins and a wrong pick fails silently. A
#     root that matches nothing simply never satisfies a prefix, so the write blocks --
#     fail-closed, not open.
# Each shape is matched against the remainder AFTER the anchor prefix, and each requires a
# non-empty final component so a bare directory path cannot satisfy it.
def _temp_dir_names():
    """EVERY plausible temp ROOT name, for prefix comparison only.

    Returns all of them rather than picking one by precedence, because the two ends
    disagree on precedence and a wrong pick fails silently (adversarial review,
    2026-09-18). Node's os.tmpdir() -- which is what the harness derives the scratchpad
    path from -- reads TEMP then TMP and IGNORES TMPDIR; Python's tempfile.gettempdir()
    reads TMPDIR first. So an environment setting TMPDIR to anything other than TEMP would
    make this hook anchor on a directory the scratchpad never lives in: fail-closed, but
    the friction this whole change exists to remove would quietly come back. Accepting
    every candidate costs one extra prefix comparison and removes the ordering question.
    Each candidate still has to clear _exemption_anchor and a full shape match, so a
    hostile TEMP buys nothing.

    Deliberately NOT a bare tempfile.gettempdir() call (adversarial review, 2026-09-18,
    two findings). First: gettempdir() raises FileNotFoundError when no candidate temp dir
    is writable, and at module scope that traceback exits the process 1 -- which this
    harness treats as NON-BLOCKING, so an environment with no writable temp would not just
    lose the exemption, it would silently disable Gates 1/2a/2b/2c entirely. Second:
    gettempdir() probes for writability by CREATING AND DELETING a file, and this hook is a
    fresh process on EVERY PreToolUse call, so that probe would run on every tool use. We
    only need the directory's NAME, never a writable handle, so read the environment
    variables directly and keep the probing call as a guarded last resort. The sequence
    below is a DEDUP order, not a precedence: every value is returned, so which variable
    comes first does not affect the outcome."""
    names = []
    for var in ("TEMP", "TMP", "TMPDIR"):
        value = os.environ.get(var)
        if value and value not in names:
            names.append(value)
    if not names:
        try:
            names.append(tempfile.gettempdir())
        except Exception:
            pass
    return names


try:
    _HOOK_PARENT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
except Exception:
    # abspath() can raise on a deleted/unreachable cwd. No anchor simply means no
    # exemption; it must never mean no gate.
    _HOOK_PARENT = None
_CLAUDE_HOME = _exemption_anchor(_HOOK_PARENT) if _HOOK_PARENT else None
_TEMP_ROOTS = tuple(_exemption_anchor(name) for name in _temp_dir_names())
# ~/.claude/projects/<project-slug>/memory/<file>
_PROJECT_MEMORY_SHAPE = re.compile(r"^projects/[^/]+/memory/[^/].*$")
# %TEMP%/claude/<project-slug>/<session-id>/scratchpad/<file>
_SCRATCHPAD_SHAPE = re.compile(r"^claude/[^/]+/[^/]+/scratchpad/[^/].*$")
_SLUG_DIR_EXEMPTIONS = tuple(
    [(_CLAUDE_HOME, _PROJECT_MEMORY_SHAPE)]
    + [(root, _SCRATCHPAD_SHAPE) for root in _TEMP_ROOTS]
)


def _is_multiply_linked(path):
    """True when the write target ALREADY EXISTS with more than one directory entry.

    A hardlink is a second name for the same inode, so a file created inside an exempt
    directory and hardlinked to a site file would be written through the exempt name --
    realpath() cannot see it, because a hardlink is not a reparse point and has no target
    to resolve. This does NOT close the hardlink class generally (that is documented as
    deferred above, and is reachable today through any marker-free path with no exemption
    involved); it only stops the exemption from becoming a second, more convenient spelling
    of it. Adversarial review, 2026-09-18.

    Fail-closed: the ordinary case is creating a NEW file, which does not exist and is not
    multiply linked; any OTHER stat failure counts as multiply linked and forfeits the
    exemption."""
    try:
        stat_result = os.stat(path)
    except FileNotFoundError:
        return False
    except (OSError, ValueError):
        # ValueError, not just OSError: on Windows os.stat() raises ValueError("stat: path
        # too long for Windows") at >= 32768 characters, while os.path.realpath() at that
        # length does NOT raise -- so resolve_ok stays True, the four prior conditions pass,
        # and an uncaught throw here would escape check_file_write entirely. This hook
        # exiting 1 is NON-BLOCKING, so that would disable Gates 1/2a/2b/2c for the call --
        # the one outcome the doctrine above says must never happen. Same pair the realpath
        # guard already catches; missed here in the first draft (adversarial re-review,
        # 2026-09-18).
        return True
    return getattr(stat_result, "st_nlink", 1) > 1


def _is_claude_slug_dir(resolved):
    """True only for a RESOLVED real path inside a Claude-managed directory whose name
    embeds the project slug. Callers must pass the realpath(), never the literal path --
    see the 2026-09-18 note in the module docstring."""
    for root, shape in _SLUG_DIR_EXEMPTIONS:
        if root and resolved.startswith(root) and shape.match(resolved[len(root):]):
            return True
    return False


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
    # THE LITERAL PATH IS WHAT THE TOOL OPENS -- resolve THAT (2026-09-18 adversarial
    # review, CRITICAL). Resolving only normalized_path, as this did until that review,
    # asks the filesystem about a string the tool never passes to open(): any component
    # differing from a real directory only by a character normalization folds or deletes
    # is a DIFFERENT object to Windows and the SAME object to this hook. Proven live: a
    # junction named `scratchpad​` (zero-width space, category Cf) reached exit 0
    # while the bytes landed in a site checkout -- and the junction itself is created by
    # `mklink`, which is not a write indicator, so Gate 2b never saw it either. The
    # fullwidth (NFKC) and combining-mark (Mn) forms are the same bug. resolve the raw
    # path, THEN normalize the result for marker matching.
    resolve_ok = "\x00" not in file_path  # realpath() swallows an embedded NUL silently
    try:
        resolved = os.path.realpath(normalized_path).replace("\\", "/").lower()
        resolved_literal = _normalize_for_matching(
            os.path.realpath(file_path)).replace("\\", "/").lower()
    except (OSError, ValueError):
        # No real path means no trustworthy answer to "where do the bytes land", so the
        # slug-dir exemption below is unavailable and the marker match stands unmodified.
        resolved = normalized
        resolved_literal = normalized
        resolve_ok = False
    if any(marker in normalized for marker in SITE_PATH_MARKERS) or \
            any(marker in resolved for marker in SITE_PATH_MARKERS) or \
            any(marker in resolved_literal for marker in SITE_PATH_MARKERS):
        # The marker may be nothing but a Claude-derived project SLUG -- a memory or
        # scratchpad directory NAMED after this project, not a path into the site tree
        # (2026-09-18; see the module docstring).
        #
        # Three conditions, each load-bearing, all fail-closed:
        #   resolve_ok                      -- we got a real answer from the filesystem.
        #   normalized_path == file_path    -- normalization changed NOTHING, so the path
        #                                      this hook reasoned about and the path the
        #                                      tool opens are the same string. Any
        #                                      normalization-visible character anywhere in
        #                                      the path forfeits the exemption outright,
        #                                      which is the general form of the CRITICAL
        #                                      above rather than a patch of its three
        #                                      known spellings.
        #   both resolved forms exempt      -- redundant while the equality holds (they are
        #                                      then the same string), and deliberately kept
        #                                      so a future refactor that weakens the
        #                                      equality guard cannot silently re-open it.
        #   not multiply linked          -- an existing hardlink is a second name for a
        #                                   file that may live in the site tree, and
        #                                   realpath() cannot see it (see
        #                                   _is_multiply_linked).
        if (resolve_ok
                and normalized_path == file_path
                and _is_claude_slug_dir(resolved_literal)
                and _is_claude_slug_dir(resolved)
                and not _is_multiply_linked(file_path)):
            return
        if not override_active(session_id, WEBSITE_WRITE):
            block("write to oxfordra.net site tree: %s" % file_path, WEBSITE_WRITE, session_id)


def check_mcp(tool_name, session_id, tool_input=None):
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
    # Gates 1b/1c/3. Once a payload names one of these tools, ANY anomaly fails closed, same
    # as Bash/file tools: an exception here would exit 1, which PreToolUse treats as
    # non-blocking, i.e. the send or publish would proceed.
    short = lowered.rsplit("__", 1)[-1]
    if short in _MS365_EMAIL_SENDS or short in _MS365_TEAMS_SENDS or short in _HUBSPOT_CMS_READS:
        try:
            _check_send_and_cms(short, tool_name, tool_input, session_id)
        except SystemExit:
            raise
        except Exception:
            block_shape(tool_name, session_id)


_MS365_EMAIL_SENDS = frozenset(("outlook_send_mail", "outlook_forward_mail", "outlook_send_draft"))
_MS365_TEAMS_SENDS = frozenset(("teams_send_chat_message", "teams_send_channel_message",
                                "teams_reply_channel_message"))
# Full-string match. Anything that is not exactly one plain address at the internal domain
# is external: "a@oxfordra.net.evil.com", "Name <x@evil.com>", "evil@x.com,ceo@oxfordra.net",
# a trailing space/newline/zero-width character, a non-ASCII homoglyph in the domain.
_INTERNAL_ADDRESS = re.compile(r"[A-Za-z0-9._+\-]+@oxfordra\.net", re.IGNORECASE | re.ASCII)
# The only parameters the ms365 send tools document. A recipient-bearing key this gate does not
# know about (replyTo, a differently-cased "To", a field added later) fails closed instead of
# being silently ignored.
_EMAIL_SEND_KEYS = frozenset(("to", "cc", "bcc", "subject", "body", "bodyType", "comment", "messageId"))
_DRAFT_SEND_KEYS = frozenset(("messageId",))

_HUBSPOT_PAGE_READS = frozenset(("MODULES", "MODULE_TYPES", "MODULE_DEF", "MODULE_STYLES",
                                 "MODULE_GUIDE", "REVISIONS", "TEMPLATES", "FORMS", "BRAND_KIT"))
# tool suffix -> (input field holding the action, exact-case set of READ actions). Allowlist
# by design: an action added to the connector later is a write until someone reads it.
_HUBSPOT_CMS_READS = {
    "manage_blog_post": ("action", frozenset(("GET_POST", "GET_AUTHOR", "LIST_BLOGS",
                                              "LIST_BLOG_POSTS", "LIST_TAGS", "GET_BRAND_KIT"))),
    "manage_landing_page": ("action", _HUBSPOT_PAGE_READS),
    "manage_website_page": ("operation", _HUBSPOT_PAGE_READS | frozenset(("NAV_GET_MENU",))),
}
# Operations that take mode="PREVIEW", which the connector documents as writing nothing.
_HUBSPOT_PREVIEWABLE = frozenset(("PUBLISH", "REMOVE", "REMOVE_SECTION", "RESTORE_REVISION",
                                  "NAV_SET_ITEM", "NAV_REPLACE_MENU", "NAV_REMOVE_ITEM"))
# Used ONLY when the hook payload cannot be parsed (see main()). json.loads raises
# RecursionError on deeply nested input, which a caller can induce by padding an unknown extra
# key; failing open there let a live send or publish through with no token (review finding C8).
# Anything unparseable that still names a gated tool is refused. Built from the same sets the
# gate uses so the list cannot drift.
_GATED_NAME_MARKER = re.compile(
    "|".join(sorted(re.escape(n) for n in (_MS365_EMAIL_SENDS | _MS365_TEAMS_SENDS
                                             | frozenset(_HUBSPOT_CMS_READS))))
    + r"|mcp__[\w\-]*netlify", re.IGNORECASE)


def _nonblank(value):
    return isinstance(value, str) and value.strip() != ""


def _email_recipients(tool_input):
    """Every to/cc/bcc entry, UNSTRIPPED (a padded address is not provably internal). None
    when the shape is unusable or there is no recipient at all."""
    if not isinstance(tool_input, dict):
        return None
    found = []
    for key in ("to", "cc", "bcc"):
        value = tool_input.get(key)
        if value is None:
            continue
        if isinstance(value, str):
            value = [value]
        if not isinstance(value, list):
            return None
        for address in value:
            if not isinstance(address, str):
                return None
            found.append(address)
    return found or None


def _teams_destination(short, tool_input):
    if not isinstance(tool_input, dict):
        return None
    if short == "teams_send_chat_message":
        chat = tool_input.get("chatId")
        return "teams:" + chat.strip() if _nonblank(chat) else None
    team, channel = tool_input.get("teamId"), tool_input.get("channelId")
    if _nonblank(team) and _nonblank(channel):
        return "teams:%s/%s" % (team.strip(), channel.strip())
    return None


def _hubspot_cms_is_read(short, tool_input):
    if not isinstance(tool_input, dict):
        return False
    field, reads = _HUBSPOT_CMS_READS[short]
    value = tool_input.get(field)
    if field == "action":
        return isinstance(value, str) and value in reads
    if not isinstance(value, dict):
        return False
    kind = value.get("_type")
    if not isinstance(kind, str):
        return False
    if kind in reads:
        return True
    if kind in _HUBSPOT_PREVIEWABLE:
        # Explicit only: the connector's own default for NAV_* is PREVIEW, but an omitted or
        # odd mode is not something this gate should bet a live site menu on.
        return value.get("mode") == "PREVIEW" and not value.get("confirmNavChange")
    return False


def _check_send_and_cms(short, tool_name, tool_input, session_id):
    if short in _HUBSPOT_CMS_READS:
        if _hubspot_cms_is_read(short, tool_input):
            return
        detail = ""
        if isinstance(tool_input, dict):
            probe = tool_input.get("action") or (tool_input.get("operation") or {})
            probe = probe.get("_type") if isinstance(probe, dict) else probe
            detail = " " + probe[:40] if isinstance(probe, str) else ""
        if not override_active(session_id, HUBSPOT_CMS_WRITE):
            block("HubSpot CMS write (%s%s) -- public-facing content" % (short, detail),
                  HUBSPOT_CMS_WRITE, session_id)
        return
    if short in _MS365_TEAMS_SENDS:
        destination = _teams_destination(short, tool_input)
        if destination is None:
            block_shape(tool_name, session_id)
        external = [destination]
        reason = "Teams message send (%s)" % short
        hint = "Name the destination in `recipients:` exactly: %s\n" % destination
    elif short == "outlook_send_draft":
        message_id = tool_input.get("messageId") if isinstance(tool_input, dict) else None
        if not _nonblank(message_id) or set(tool_input) - _DRAFT_SEND_KEYS:
            block_shape(tool_name, session_id)
        external = ["draft:" + message_id.strip()]
        reason = "Outlook draft send (%s)" % short
        hint = ("outlook_send_draft carries no recipient list, so the token must name the "
                "draft itself in `recipients:`: %s\n" % external[0])
    else:
        recipients = _email_recipients(tool_input)
        if recipients is None or set(tool_input) - _EMAIL_SEND_KEYS:
            block_shape(tool_name, session_id)
        external = [a for a in recipients if not _INTERNAL_ADDRESS.fullmatch(a)]
        if not external:
            return  # internal-only: parity with Gate 1, which also leaves internal sends alone
        reason = "external email recipient(s) via MCP (%s): %s" % (short, ", ".join(external))
        hint = ""
    # consume=True (default): this is the ONLY enforcement point for these tools, so it must
    # be the one that spends the single-use grant (see override_active's docstring).
    if not override_active(session_id, EXTERNAL_SEND, external):
        block("%s: %s" % (reason, ", ".join(external)) if hint else reason,
              EXTERNAL_SEND, session_id, extra=hint)


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
        raw = sys.stdin.read()
    except Exception:
        return
    try:
        payload = json.loads(raw)
    except Exception:  # includes RecursionError from pathologically nested input
        if _GATED_NAME_MARKER.search(raw):
            sys.stderr.write(
                "BLOCKED by ORA autonomy gate: the hook payload could not be parsed but it "
                "names a gated tool (send / publish / Netlify write). A payload that cannot be "
                "evaluated for a gated tool fails closed (hard invariant 1/2).\n")
            sys.exit(2)
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
        # The Netlify gate reads only tool_name; Gates 1b/1c/3 also read tool_input and fail
        # closed on any shape they cannot evaluate.
        check_mcp(tool_name, session_id, tool_input)


if __name__ == "__main__":
    main()
    sys.exit(0)
