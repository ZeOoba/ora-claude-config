"""Post-Netlify-updater liveness probe of oxfordra.net (hooks-audit 2026-09-30).

Replaces the inline `bash -c 'INPUT=$(cat); TOOL=...; curl ...'` PostToolUse
hook that was registered on matcher `mcp__a66aaa4a-ffcd-4066-b2af-79c4ce807809__.*`.
Same trigger (tool name ends in "updater", the old `grep -qE "updater$"`), same
probe (one GET, redirects NOT followed -- curl's default, so a 301 still warns
exactly as before), same warning text. Two deliberate changes:

  1. `curl -m 10`: the old probe had NO timeout, so a hung TLS handshake could
     hold the PostToolUse hook for the harness's full hook timeout.
  2. DELIVERY: the old hook wrote the warning to STDERR and exited 0, which the
     harness shows to nobody on a successful PostToolUse -- the warning was
     structurally invisible. It is now returned as additionalContext, which the
     post dispatcher emits as {"hookSpecificOutput": {"hookEventName":
     "PostToolUse", "additionalContext": ...}} on stdout, exit 0, so the MODEL
     sees it. (systemMessage would be user-visible but model-invisible -- see
     reference_hook_systemmessage_not_model_visible.md.)

NOTE: all three netlify *-updater tools are in settings.json permissions.deny as
of 2026-09-30, so this path can only fire if that deny is lifted. It is kept,
not deleted, because that is exactly when a post-change probe matters.

Never raises out of check(); never blocks (PostToolUse cannot block anyway).

Stdlib only. ASCII-only. Windows (`python`).
"""
import os
import re
import subprocess

URL = "https://oxfordra.net"
UPDATER_RE = re.compile(r"updater$")
CURL_MAX_TIME_S = 10


def http_status(url=URL):
    """curl's %{http_code} for one GET of `url` ("000" on any failure),
    bounded by -m 10 plus a subprocess backstop."""
    try:
        proc = subprocess.run(
            ["curl", "-s", "-m", str(CURL_MAX_TIME_S), "-o", os.devnull,
             "-w", "%{http_code}", url],
            capture_output=True, timeout=CURL_MAX_TIME_S + 5)
        code = proc.stdout.decode("ascii", "replace").strip()
        return code or "000"
    except Exception:
        return "000"


def check(payload, fetch=None):
    """additionalContext text when a Netlify *updater* tool just ran and the
    site did not answer 200; None otherwise. Never raises. `fetch` defaults
    to the module-level http_status, resolved at CALL time (a test seam)."""
    try:
        if not isinstance(payload, dict):
            return None
        tool = payload.get("tool_name")
        if not isinstance(tool, str) or not UPDATER_RE.search(tool):
            return None
        status = (fetch or http_status)(URL)
        if status == "200":
            return None
        return "WARNING: oxfordra.net returned HTTP %s after Netlify MCP %s" % (
            status, tool)
    except Exception:
        return None
