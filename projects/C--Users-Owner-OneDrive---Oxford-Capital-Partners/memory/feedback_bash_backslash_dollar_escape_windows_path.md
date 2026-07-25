---
name: feedback-bash-backslash-dollar-escape-windows-path
description: "In a double-quoted bash string, a backslash immediately before a $variable inside a Windows path (e.g. \"C:\\...\\$SID\\...\") is bash's own \\$ escape sequence -- it prevents variable expansion and leaves a LITERAL '$SID' in the path, not the variable's value. The write silently succeeds against a bogus path; a same-command readback of that bogus path looks correct and hides the bug."
metadata:
  type: feedback
  originSessionId: 3ed3732a-4976-4582-9110-de67cd9ebdb2
  modified: 2026-07-25T15:17:01.570Z
---

Never build a Windows backslash-style path in a double-quoted bash string by placing a
`$variable` directly after a backslash segment (`"C:\Users\...\$SID\overrides"`). Bash
treats `\$` inside double quotes as its OWN escape sequence for a literal `$` — it does
**not** know the following backslash is meant as a Windows path separator, so `\$SID`
expands to the four literal characters `$SID`, not the variable's value. `mkdir -p`/`cat >`
against that string then silently creates a garbage directory literally named
`sessions$SID` (bash never errors — a wrong-but-valid path is still a valid path), and a
same-command `cat` readback of `"$DIR/allow-config-write"` shows exactly what you just
wrote, at the SAME bogus location — completely masking the bug in the moment. The
divergence only became visible on a *separate*, later read (via the `Read` tool, and via a
Python script loading the module's own path-resolution function) of the *intended* real
path, which still held old, stale content.

**Why:** hit live 2026-07-25 minting a `config-write-guard.py` override token
(`hooks/sessions/<session_id>/overrides/allow-config-write`) via a Bash heredoc:
`DIR="C:\Users\Owner\.claude\hooks\sessions\$SID\overrides"`. The write appeared to
succeed (an immediate `cat` in the same command showed the correct new content), but
`eos-review-gate.py --record` then failed the gate as if no fresh token existed. Only
`git status` surfacing an untracked `hooks/sessions$SID/` directory (literal `$SID`, no
path separator before it) revealed the real cause. This is a distinct mechanism from the
sibling entries below — not a sed/Python escape-sequence corruption of an existing file's
*content*, but bash's own quoting rules silently redirecting a *write* to the wrong path
entirely, with a same-shell readback that cannot catch it because it reads back the same
wrong path.

**How to apply:** never interpolate a `$variable` immediately after a backslash inside a
double-quoted Windows path in bash. Either (a) build the path with forward slashes
(`"C:/Users/Owner/.claude/hooks/sessions/$SID/overrides"` — bash expands `$SID` correctly
there since no backslash precedes it, and Windows tools accept forward slashes fine), or
(b) avoid Bash entirely for writes to session-scoped / governance-adjacent files and use
the `Write`/`Edit` tools instead, which do not go through bash quoting at all and have
proven reliable for every other file mutation in this session. After minting any override
token or governance-adjacent file via Bash, verify with a **separate** tool call (`Read`,
or a fresh Python process) that reads the path via its own independent construction (e.g.
the consuming module's own path-resolution function) — never trust a same-command/same-shell
readback of the exact string you just built, since it will faithfully reflect whatever
bogus path you actually wrote to.

Related: [[feedback_sed_windows_path_escapes]] (a different failure mode on the same
"escape characters silently corrupt a Windows path in a text tool" theme — that one
mangles existing file *content* via sed/Python escape sequences; this one silently
misdirects a *write* to the wrong path via bash's own quoting) · [[feedback_bash_unquoted_windows_paths_collapse]].
