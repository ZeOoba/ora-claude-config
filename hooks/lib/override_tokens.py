"""Shared override-token contract for the ORA human-authorization gates.

One token format, one validator, for every gate that can be overridden by Gabriel's
explicit in-turn confirmation. Both gates use it:
  - git-prepush-doctrine-gate.py -- allow-doctrine-drift
  - ora-autonomy-gate.py         -- allow-website-write / allow-website-deploy /
                                    allow-external-send (adopted 2026-07-17)

A gate keeps only what this module cannot know: its own tiers and TTLs, and any binding
specific to its domain (Gate 1's recipient naming rides in as token_grants' extra_check).

A token lives at:  hooks/sessions/<session_id>/overrides/<name>

and its content must be:

    scope: doctrine-drift
    session: <the session_id it was minted in>
    reason: <free text -- for the human audit trail, not enforced>

It may be created ONLY after Gabriel's explicit in-turn confirmation in a live session.
Scheduled/headless sessions must NEVER self-create one -- flag and stop instead.

WHY THIS SHAPE (2026-07-16). The previous scheme was a flat `hooks/overrides/<name>`
sentinel validated by mtime alone. Four defects compounded:

  1. Content-blind -- any bytes, or none, authorized the action. Justification text was
     theatre: a token reading "DO NOT DEPLOY ANYTHING" authorized a production deploy.
  2. Session-blind and global -- any concurrent session inherited any live token. With
     4+ sessions routinely running here, that is a real cross-session grant leak.
  3. One name keyed several gates, so approving a trivial act silently opened a severe one.
  4. GIT-TRACKED. git stamps a checked-out file with CHECKOUT time, and the gate trusted
     mtime alone -- so a plain `git clone` of ~/.claude materialized the token at age ~0 and
     SELF-GRANTED a live override with no human involved. Proven empirically: a fresh clone
     made ora-autonomy-gate.py return exit 0 for `netlify deploy --prod`, against an
     empty-dir control at exit 2. `hooks/overrides/allow-website-change` really was tracked
     (swept in by 668f9d4, a broad `git add -A` that caught a live token).

Session-scoping addresses 2 and 4 together: `hooks/sessions/` is gitignored, so the broad
`git add -A` sweep that caused defect 4 (668f9d4, and again in 8afad84) cannot pick a token
up. (b23a025 additionally untracked the sentinel and ignored the retired flat dir, as a
second line of defense.)

HONEST LIMITS -- read these before trusting this module further than it goes:

  a. It cannot defend against the session that WRITES the token: that session could write
     any scope it likes. The gate cannot tell an approved token from a self-granted one.
  b. Session identity is SELF-ASSERTED. A git hook has no payload, so the pushing process
     supplies CLAUDE_CODE_SESSION_ID itself and nothing authenticates it. This is SCOPING,
     NOT AUTHENTICATION: it stops a concurrent session from ACCIDENTALLY inheriting a live
     token, but a session that deliberately exports another session's id replays that
     session's token -- and the event_log then blames the id that was exported. Verified by
     adversarial review, 2026-07-16. Closing this needs a channel the pusher cannot forge;
     there isn't one at this layer.
  c. "Cannot be committed" is about the SWEEP, not about git in general. A deliberate
     `git add -f` still tracks a token, and any ref that tracks one re-mints it on checkout
     at age ~0 -- .gitignore does not protect ALREADY-TRACKED files. That is exactly how a
     token survived on a side branch after main was cleaned. The durable guard is
     hooks/tests/test-override-token-hygiene.py, which fails if ANY overrides/ path is
     tracked; run it across refs, not just the working tree.

What it does buy, against the retired sentinel: clone/checkout-minting via the ordinary
`add -A` path, `touch`-minting, accidental cross-session inheritance, mis-scoped reuse --
and an audit trail that records who overrode and why.

Everything fails CLOSED. No session_id, no token, unreadable, oversized, non-UTF-8,
duplicate keys, wrong scope, wrong session, future-dated, aged out, un-consumable -> no
grant. A false positive costs a retry; a false negative bypasses a human gate.

Adoption history: ora-autonomy-gate.py carried an equivalent inline implementation (927f6d0)
while this module was written for the doctrine gate (a64f2e5) -- two gates enforcing the same
security-critical rules from two copies. They were written hours apart by two sessions and
had already begun to diverge: one returned a bool, the other the parsed fields so `reason:`
could reach the audit trail. The gate adopted this module on 2026-07-17, deleting ~88 lines
of duplicate validation. If a third gate ever needs an override, it imports from here.
"""
import os
import re
import time

DEFAULT_SESSIONS_DIR = r"C:\Users\Owner\.claude\hooks\sessions"
OVERRIDE_SUBDIR = "overrides"

# A token may not be older than its TTL. Small negative ages (filesystem timestamp
# granularity / clock skew) are tolerated; a genuinely future-dated token is refused, since
# a naive `age < ttl` check would otherwise honor it ~forever.
CLOCK_SKEW_TOLERANCE_SECONDS = 5
MAX_TOKEN_BYTES = 8192
# Only a filename-safe, traversal-free session_id may address a token directory. Rejects
# "..", "../overrides", "a/../../overrides", "\\..\\overrides" -- anything that could escape
# the sessions root and reach the retired flat overrides dir (or anywhere else).
SESSION_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


class Tier(object):
    """One override name == one severity tier. No name may key two tiers.

    requires_extra_check marks a tier whose token carries a binding this module cannot
    evaluate on its own -- today only allow-external-send, whose token must name every
    external recipient of the send. That check is EMAIL domain logic and belongs to the
    gate, not to a generic token contract; the tier flag exists so token_grants can REFUSE
    to grant when a caller omits it, rather than silently skipping the binding.
    """

    def __init__(self, name, scope, ttl, single_use=False, requires_extra_check=False):
        self.name = name
        self.scope = scope
        self.ttl = ttl
        self.single_use = single_use
        self.requires_extra_check = requires_extra_check


def sessions_root():
    """ORA_OVERRIDE_SESSIONS_DIR is a TEST SEAM ONLY -- it must never be set in
    settings.json's env block or any production scheduled-task context. Setting it there
    would let a process redirect a security gate's override lookup to an attacker-writable
    directory. It exists purely so the gate tests can isolate themselves from whatever is
    live in the real sessions folder."""
    return os.environ.get("ORA_OVERRIDE_SESSIONS_DIR") or DEFAULT_SESSIONS_DIR


def token_path(session_id, name):
    """Resolve a token path, or None if the session_id cannot safely address one."""
    if not isinstance(session_id, str) or not SESSION_ID_RE.match(session_id):
        return None
    root = sessions_root()
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


def parse_token(path):
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


def fresh(path, ttl):
    try:
        age = time.time() - os.path.getmtime(path)
    except OSError:
        return False
    return -CLOCK_SKEW_TOLERANCE_SECONDS <= age < ttl


def consume(path):
    """Burn a single-use token. If it cannot be removed we cannot promise single-use, so
    the caller must treat failure as 'no override'."""
    try:
        os.remove(path)
        return True
    except OSError:
        return False


def token_grants(session_id, tier, extra_check=None):
    """The validated token's fields when a valid, fresh, correctly-scoped, session-matched
    token authorizes `tier` for `session_id` -- otherwise None. Consumes the token first
    when the tier is single-use.

    Returns the FIELDS rather than a bool so callers can put `reason:` into the audit trail.
    A granting token always carries scope+session, so the dict is always truthy; callers
    wanting a bool should compare `is not None` explicitly.

    extra_check, when given, is called with the parsed fields and must return truthy for the
    grant to stand. It is for a binding this module cannot evaluate itself -- e.g. Gate 1's
    rule that an allow-external-send token must name every external recipient of the send.
    It runs BEFORE consumption, so a token that fails it is refused WITHOUT being burned.
    A tier declaring requires_extra_check REFUSES to grant when no extra_check is supplied,
    so forgetting one fails closed instead of silently dropping the binding.

    CONSUMES on validation, so call it ONLY when a grant would actually be used. Evaluating
    it speculatively (e.g. before checking whether there is anything to override) would burn
    a single-use token on an action that never needed one.
    """
    if tier.requires_extra_check and extra_check is None:
        return None
    path = token_path(session_id, tier.name)
    if not path or not os.path.isfile(path):
        return None
    if not fresh(path, tier.ttl):
        return None
    fields = parse_token(path)
    if not fields:
        return None
    if fields.get("scope") != tier.scope:
        return None
    if fields.get("session") != session_id:
        return None
    # BEFORE consuming: a token that fails the caller's binding must not be burned -- it may
    # be a legitimate token being tested against the wrong action.
    if extra_check is not None and not extra_check(fields):
        return None
    # Consume BEFORE granting: if we granted first and the delete then failed, the token
    # would silently become multi-use.
    if tier.single_use and not consume(path):
        return None
    return fields


def describe_token(session_id, tier):
    """The exact token an operator must write to grant `tier`, for a block message."""
    path = token_path(session_id, tier.name)
    where = path or ("<no usable session id -- an override cannot be created or honored "
                     "in this context>")
    return (
        "  path: %s\n"
        "  valid: %d min%s\n"
        "  content:\n"
        "    scope: %s\n"
        "    session: %s\n"
        "    reason: <why Gabriel approved this>\n"
        % (where, tier.ttl // 60,
           ", SINGLE-USE (consumed by one gate-pass)" if tier.single_use else ", multi-use",
           tier.scope, session_id or "<none>")
    )
