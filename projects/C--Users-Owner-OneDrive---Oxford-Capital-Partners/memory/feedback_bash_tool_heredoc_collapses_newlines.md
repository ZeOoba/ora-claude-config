---
name: feedback_bash_tool_heredoc_collapses_newlines
description: "The Bash tool collapses \\n inside a heredoc, corrupting a test file mid-edit -- write the patch content to a scratch file first (Write tool) and cat/move it into place, never inline a multi-line heredoc through Bash for file content that matters."
metadata:
  node_type: memory
  type: feedback
  originSessionId: 20d42965-6e98-4b9d-9fb6-1a2952b06678
  modified: 2026-09-07T17:15:29.235Z
---

**Pattern (flagged 2026-09-07, closing-sweep session).** Writing a test file's content via a Bash heredoc (`cat <<'EOF' > file` or similar) collapsed literal `\n` sequences inside the payload, corrupting the file mid-edit rather than writing it verbatim.

**Why this is the Bash tool specifically, not the shell.** The tool's own instructions already warn that Bash here is Git Bash / POSIX sh and that PowerShell here-strings don't apply — but the failure here is upstream of shell quoting: the tool's own transport mangles embedded `\n` before the shell ever sees the heredoc body, so quoting the delimiter correctly (`<<'EOF'`) does not protect against it the way it would in a real terminal.

**How to apply.** For any file content with embedded newlines/escapes that must round-trip exactly (test fixtures, multi-line strings inside code, anything with literal `\n`/`\t`), do not inline it through a Bash heredoc:
1. Write the full content to a scratch file with the **Write** tool (or **Edit** for an existing file) — these tools are not subject to the heredoc-collapsing path.
2. If the content needs to land somewhere Write/Edit can't reach directly (e.g. assembled programmatically), write it to a scratch file first, then use Bash only to move/copy that already-correct file into place — never to carry the payload itself.
3. Treat a heredoc-in-Bash as safe only for short, escape-free, single-purpose shell snippets (a git commit message with no literal backslash-n, a one-line script) — not as a general file-writing mechanism.

Related: session-context general Bash-tool caveats (PowerShell here-strings, backtick continuation) — this is the same class of "looks like a normal shell, isn't" hazard, one level deeper.
