---
name: feedback-config-write-guard-bash-read-shaped-false-positive
description: "Before any Bash grep/python -c/sed one-liner whose command text will name hooks/**, settings.json, or CLAUDE.md -- even purely to read -- use Read/Grep/Glob instead. config-write-guard blocks these by design; the matcher must NOT be narrowed to fix it -- reinvestigated 2026-08-05, same conclusion."
metadata: 
  node_type: memory
  type: feedback
  originSessionId: eacae185-2a38-44f4-b688-a79e554c7de0
  modified: 2026-08-05T22:12:51.767Z
---

**Do not narrow `hooks/config-write-guard.py`'s shell matcher** in response to a read-only
Bash command (`grep`, `python -c`, `sed`, etc.) getting blocked for merely NAMING a
governance path (`hooks/**`, `settings.json`, `settings.local.json`, `CLAUDE.md`). This was
re-investigated 2026-08-05 after two such blocks in one session (a `grep` and a `python -c`
one-liner, both read-only, both named a governance path) — conclusion: **working as intended,
no code change.**

**Why both blocks were expected, not bugs:**
- `python -c "..."` one-liners naming a governance path are ALWAYS treated as write-shaped when
  they name one, because a script's actual runtime behavior is not statically decidable — the
  guard's own block message says this explicitly (`config-write-guard.py`'s
  `_block_governance`).
- `grep`/`sed` with quoted pattern text (e.g. `grep -rn '"del"' hooks/...`,
  `sed -n 's/rm/x/p' hooks/...`) trips the bounded-verb matcher on the quoted PATTERN text
  itself, not on any real write verb. This is a named, accepted-cost example directly in
  `hooks/lib/tool_call_paths.py`'s false-positive-class comment (~line 337-341, "quoted/regex
  TEXT" class, measured at 19 FPs / 107 probed benign commands, all requiring a governance-path
  marker too).

**Why the matcher can't be safely narrowed to fix this:** same structural reason as
[[feedback_autonomy_gate_matcher_cannot_be_safely_narrowed]] — a flat text matcher cannot track
real shell/interpreter quoting or runtime state, so "is this really just a read" is not
decidable by pattern-matching. `config-write-guard.py`'s own docstring cites that file directly
and inherits its breadth-over-precision posture on purpose. Any narrowing attempt needs the same
three-round independent adversarial gauntlet before it may land — not attempted here, and not
warranted: this is an already-documented, already-accepted false-positive class, not a new
defect.

**How to apply — the fix is behavioral, not code:** the round-trip cost (Bash blocked → read the
block message → retry via Read/Grep/Glob) cannot be eliminated from the detection side without
touching the matcher, which is off the table. It CAN be avoided on the prevention side: before
reaching for a Bash `grep`/`python -c`/`sed`/`cat` one-liner whose command text will contain
`hooks/`, `settings.json`, `settings.local.json`, or `CLAUDE.md` (even a plain, obviously
read-only inspection), default straight to the Read/Grep/Glob tools instead — they are never
gated by this guard. The block message already names this workaround correctly every time; the
only real cost is the wasted round trip, not confusion about what to do next. CLAUDE.md was
considered as a higher-visibility home for this reminder and rejected: the file is already at
its consolidation floor ([[reference_claude_md_word_budget_is_a_floor]], ~1700-1755 words) and
its own layering rule says an operational tooling gotcha like this belongs in memory, not the
top-level operating prompt.

Related: [[feedback_autonomy_gate_blocks_writes_not_reads]] (companion lesson: verify a
"blocked" claim before invoking the override protocol) · [[reference_config_write_guard_quote_split_gap]]
(a different, still-open class — actual bypasses, not this false-positive class) ·
[[reference_config_write_guard_blocks_eos_review_gate]] (a real bug, already fixed — contrast
with this entry, which is NOT a bug).
