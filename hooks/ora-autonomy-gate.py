#!/usr/bin/env python3
"""ORA autonomy gate (PreToolUse) — preserves the human gates under defaultMode=bypassPermissions.

With bypassPermissions, permission prompts never fire, so invariants 1 and 2 are enforced
here instead (hooks run in every mode, including scheduled/headless sessions):

  GATE 1 — external email: any send-via-outlook.ps1 invocation carrying a -To/-Cc/-Bcc
           flag with a recipient outside @oxfordra.net is blocked. Internal fleet sends
           (ggoldberg/egoldberg) pass untouched.
           Override sentinel: ~/.claude/hooks/overrides/allow-external-send
  GATE 2 — website (oxfordra.net): blocked across every reachable path —
             (a) Edit/Write into a website-canonical or oxford-site tree,
             (b) `netlify deploy ... --prod` via the CLI,
             (c) a raw-shell write (cp/mv/redirect/...) into the site tree, and
             (d) any Netlify MCP *-updater tool (prod deploy / project / CSP+headers).
           Reads and preview deploys pass untouched.
           Override sentinel: ~/.claude/hooks/overrides/allow-website-change

An override sentinel is valid for 60 minutes from its mtime and may be created ONLY after
Gabriel's explicit in-turn confirmation in a live session (same pattern as the eos-plan-gate
override). Money movement has no tool path in this stack; invariant 1 doctrine governs it.

Exit 2 = block (stderr is shown to the model). Unparseable input fails open so a hook
malfunction never bricks every tool call.
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

OVERRIDE_DIR = r"C:\Users\Owner\.claude\hooks\overrides"
OVERRIDE_TTL_SECONDS = 3600
INTERNAL_DOMAIN = "@oxfordra.net"
RECIPIENT_FLAGS = ("-to", "-cc", "-bcc")  # any one means the send has external reach
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


def override_active(name):
    path = os.path.join(OVERRIDE_DIR, name)
    try:
        return (time.time() - os.path.getmtime(path)) < OVERRIDE_TTL_SECONDS
    except OSError:
        return False


def block(reason, override_name):
    sys.stderr.write(
        "BLOCKED by ORA autonomy gate: %s\n"
        "This action requires Gabriel's explicit in-turn confirmation (hard invariant 1/2).\n"
        "If he has just given it, create the override sentinel (valid 60 min) and retry:\n"
        "  %s\n" % (reason, os.path.join(OVERRIDE_DIR, override_name))
    )
    sys.exit(2)


def check_bash(command):
    lowered = command.lower()
    # GATE 1 — any send-via-outlook.ps1 with a recipient flag (To, Cc, OR Bcc).
    # Keying only on -To let a Bcc/Cc-only external send slip through (2026-06-13).
    if "send-via-outlook.ps1" in lowered and any(f in lowered for f in RECIPIENT_FLAGS):
        recipients = EMAIL_RE.findall(command)
        external = sorted({r for r in recipients if not r.lower().endswith(INTERNAL_DOMAIN)})
        if external and not override_active("allow-external-send"):
            block("external email recipient(s): %s" % ", ".join(external), "allow-external-send")
    # GATE 2a — production deploy via the netlify CLI.
    if NETLIFY_INVOKE_RE.search(command) and "deploy" in lowered and "--prod" in lowered:
        if not override_active("allow-website-change"):
            block("production deploy to oxfordra.net (netlify --prod)", "allow-website-change")
    # GATE 2b — writing into the site tree via a raw shell op (cp/mv/redirect/etc).
    # The Edit/Write tool path is covered by check_file_write; Bash bypassed it (2026-06-13).
    # Strip fd-duplication redirects (2>&1, &>) before checking the bare ">" write indicator,
    # so a routine read-only command like `ls ... 2>&1` doesn't false-block (2026-07-09).
    write_check_target = FD_DUP_RE.sub(" ", lowered)
    write_check_target = NULL_REDIRECT_RE.sub(" ", write_check_target)
    markers = [m for m in SITE_PATH_MARKERS if m in lowered]
    indicators = [w for w in SITE_WRITE_INDICATORS if w in write_check_target]
    if markers and indicators:
        if not override_active("allow-website-change"):
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
                "  command             : %s\n"
                "  NOTE: both are matched ANYWHERE in the command, related or not. If this\n"
                "  command does not actually write to the site tree (e.g. it only quotes a\n"
                "  site path inside a string, heredoc, or commit message), do NOT create the\n"
                "  override -- re-run it via the Edit/Write tool, or drop the marker text from\n"
                "  the command. The override is for real site changes Gabriel just approved."
                % (", ".join(markers), ", ".join(repr(i) for i in indicators), command.strip()),
                "allow-website-change")


def check_file_write(file_path):
    normalized = file_path.replace("\\", "/").lower()
    if any(marker in normalized for marker in SITE_PATH_MARKERS):
        if not override_active("allow-website-change"):
            block("write to oxfordra.net site tree: %s" % file_path, "allow-website-change")


def check_mcp(tool_name):
    """GATE 2c — Netlify MCP mutating tools. The deploy/project/extension *-updater
    tools push to prod / change live project config + CSP/headers with no Bash and no
    prompt; under bypassPermissions nothing else stops them. This gate stands in for
    the permission prompt they would otherwise raise (2026-06-13). Reader tools pass."""
    lowered = tool_name.lower()
    if "netlify" in lowered and lowered.endswith("-updater"):
        if not override_active("allow-website-change"):
            block("Netlify MCP mutating call (%s)" % tool_name, "allow-website-change")


def main():
    try:
        payload = json.load(sys.stdin)
        tool_name = payload.get("tool_name", "")
        tool_input = payload.get("tool_input", {}) or {}
    except Exception:
        return  # fail open on malformed input

    if tool_name == "Bash":
        check_bash(tool_input.get("command", "") or "")
    elif tool_name in ("Edit", "Write", "MultiEdit", "NotebookEdit"):
        check_file_write(tool_input.get("file_path", "") or "")
    elif tool_name.startswith("mcp__"):
        check_mcp(tool_name)


if __name__ == "__main__":
    main()
    sys.exit(0)
