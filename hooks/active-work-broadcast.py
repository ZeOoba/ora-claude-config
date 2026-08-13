#!/usr/bin/env python3
"""SessionStart hook -- broadcast any live cross-session claims on shared ~/.claude
subsystems (hooks-override-auth, open-items-tracker, oxford-command-center-data,
repo-housekeeping, ora-skills, and any other slug a session chooses to claim -- see
hooks/lib/claim_work.py).

WHY: reference_concurrent_session_duplicate_hardening_work.md logs 6 recorded
collisions where two sessions independently duplicated work on the same shared
subsystem, discovered only by chance (git worktree list) or not at all until both had
sunk real work. The existing mitigation was a MANUAL pre-check the agent has to
remember to run. This makes the signal automatic: if another session has claimed a
subsystem within the last 2 hours, the starting session sees it immediately, the same
way hooks/repo-freshness.py (this hook's template) auto-surfaces oxford-command-center
git staleness instead of relying on the agent to remember `git fetch`.

`repo-housekeeping` ADDED 2026-07-26: two sessions independently ran the identical
worktree/branch cleanup sweep on this repo in parallel (one raced the other deleting
the same remote branch) -- invisible to the original 3 slugs, all scoped to hooks/
override/auth work, not general repo maintenance. See reference_concurrent_session_
duplicate_hardening_work.md's 2026-07-25/26 entry. The mechanism itself needed no
code change (slugs are already free-form, see claim_work.py); only the documented,
named vocabulary grew.

`ora-skills` ADDED 2026-08-12, for the same reason and with the same zero-code-change
shape: two sessions were handed the same remediation prompt and both began work, caught
only when the second read the first's session transcript ~15 minutes in. ora-skills was
deliberately outside this vocabulary because tech.md Sec2 gives it its own single-writer
rule (`git log -1` + `git status` before editing a SKILL.md) -- but that rule cannot see
a concurrent session, because commits there carry the machine's shared human author
identity rather than a per-session one, so git identity cannot answer "is this HEAD
mine?". Both rules now apply; neither replaces the other. See claim_work.py's ORA-SKILLS
note.

DELIVERY: emits ONLY via hookSpecificOutput.additionalContext, never systemMessage --
per reference_hook_systemmessage_not_model_visible.md, systemMessage is user-visible
but INVISIBLE to the model, so a hook meant to steer agent behavior that used
systemMessage alone would silently do nothing useful (measured elsewhere in this
codebase: shared-checkout-guard.py fired 168 times over 7 days with zero effect before
that exact defect was found and fixed 2026-07-16). Do not "simplify" this to
systemMessage.

SAFETY: read-only, warn-only. Never blocks session start. Excludes the starting
session's own claims (a session re-reading its own prior claim is not a collision).
No-ops silently (prints nothing) when there are no other live claims, when the claims
directory doesn't exist yet, or on any error -- must never fail session start.

Stdlib only. ASCII-only. Windows (`python`).
"""
import json
import os
import sys

LIB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib")
sys.path.insert(0, LIB_DIR)
# Guarded import (same reliability rationale as shared-checkout-guard.py's guarded
# import of session_liveness: a broken claim_work.py must not crash this hook at
# MODULE LOAD, before main()'s own try/except runs, on every single session start).
try:
    from claim_work import read_active_claims  # noqa: E402
except Exception:
    def read_active_claims(**_kwargs):
        return []


_MAX_FIELD_CHARS = 200


def _sanitize_field(text) -> str:
    """Collapse a claim's free-form description/title field to a single
    printable-ASCII line before it is interpolated into additionalContext.

    WHY (2026-07-26, adversarial review of the config-write-guard.py
    hooks/active-work/ exemption landed alongside this fix): claim_work.py's
    own docstring is explicit that claims are "NOT a security boundary -- any
    session can release or overwrite any claim file" -- the write path is
    deliberately open. That is fine for the claim mechanism's own purpose
    (a courtesy broadcast, not access control), but this hook is the ONE place
    a claim's free-form text becomes MODEL-VISIBLE context for every future
    session via additionalContext (unlike systemMessage, which is user-visible
    but invisible to the model -- see the module docstring's DELIVERY note).
    An unsanitized description is therefore a prompt-injection vector: text a
    session ingested from an untrusted source (a scraped page, an email) and
    then passed to `claim_work.py claim <slug> "<desc>"` would be replayed
    verbatim, embedded in newlines and blank lines, into every subsequent
    session's context -- confirmed reproducible via adversarial review.
    Collapsing to one line and stripping control characters does not make the
    TEXT trustworthy (it is still untrusted, observed data, same as any other
    hook/tool output -- see the instruction-source-boundary rule), but it
    removes the structural cues (blank lines, fake headers) an injection
    attempt needs to visually pass as separate, authoritative system text
    rather than one clearly-bounded line inside a claim listing."""
    s = str(text or "")
    s = "".join(c if (c.isprintable() and c not in "\r\n\t") else " " for c in s)
    s = " ".join(s.split())
    if len(s) > _MAX_FIELD_CHARS:
        s = s[:_MAX_FIELD_CHARS].rstrip() + "...(truncated)"
    return s or "(no description)"


def emit(ctx: str) -> None:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": ctx,
        }
    }))


def main() -> None:
    raw = ""
    try:
        raw = sys.stdin.read()
    except Exception:
        pass

    own_sid = ""
    try:
        if raw.strip():
            own_sid = (json.loads(raw) or {}).get("session_id", "") or ""
    except Exception:
        own_sid = ""

    try:
        claims = read_active_claims()
    except Exception:
        return

    others = [c for c in claims if c.get("session_id") != own_sid]
    if not others:
        return  # nothing live, or the only live claim(s) are this session's own

    lines = [
        "[cross-session claims] other session(s) have active claims on shared "
        "~/.claude subsystems -- check before independently duplicating this work "
        "(see reference_concurrent_session_duplicate_hardening_work.md):",
    ]
    for c in others:
        # The host id ("local_<uuid>") is what send_message accepts; the 8-char agent id
        # printed below is not, so without this a reader can SEE a colliding claim but
        # cannot contact its owner. Printed in full (truncating makes it unresolvable)
        # but still _sanitize_field()'d -- it reaches model-visible additionalContext
        # from world-writable claim JSON, exactly the R4 threat model noted below.
        # read_active_claims() has already normalized this to "a usable id, or ''"
        # (claim_work._clean_host_session_id), so the emptiness test here is exact.
        # It is NOT enough to test raw truthiness before sanitizing: a whitespace-only
        # value is truthy, sanitizes to "", and _sanitize_field renders "" as its
        # "(no description)" placeholder -- producing "(message it at (no description))".
        # That escaped a first fix here and was caught by independent review.
        # _sanitize_field is still applied as defense in depth for any caller that hands
        # us a claim dict that did not come through the normalizing reader.
        host = _sanitize_field(c.get("host_session_id")) if c.get("host_session_id") else ""
        lines.append("- %s: session %s%s claimed %.0fm ago -- %s" % (
            _sanitize_field(c.get("slug", "?")),
            # session_id is attacker-controlled claim JSON same as description --
            # ROUND 2 REFUTE finding R4: the slug field (already sanitized above)
            # can never actually carry a newline (it comes from a Windows
            # filename via claim_work.py's _safe_filename()), so the ORIGINAL
            # sanitization pass wrapped the one field that structurally could not
            # break, and skipped this one, which can.
            _sanitize_field(str(c.get("session_id", "?"))[:8]),
            (" (message it at %s)" % host) if host else "",
            c.get("age_minutes", 0.0),
            _sanitize_field(c.get("description") or c.get("title")),
        ))
    emit("\n".join(lines))


if __name__ == "__main__":
    main()
