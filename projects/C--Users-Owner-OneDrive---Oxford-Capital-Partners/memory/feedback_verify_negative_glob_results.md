---
name: feedback-verify-negative-glob-results
description: "A Glob search returning 'No files found' inside a git repo is not proof the file/dir doesn't exist — cross-check with git ls-files or ls directly before concluding absence, especially before telling the user something has no git-tracked home."
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 5cf0864a-7da5-4f49-95b8-389c83259d46
---

**What happened (2026-07-15):** investigating where `orphaned-task-forensics` and
`fleet-advisory-remediation` (two Cowork-invoked skills) were authored, `Glob({pattern:
"orphaned-task-forensics/**", path: "C:\Users\Owner\ora-skills"})` and the `fleet-advisory-
remediation` equivalent both returned "No files found." Concluded (and told Gabriel) that
neither skill had a git-tracked source of record, unlike the rest of the ORA skill library —
edited only a per-session Cowork runtime-cache copy as a result, with a durability caveat.

Gabriel asked to investigate further or fix it at the right repo. A plain `git ls-files | grep`
and `ls -1` run directly in the same repo immediately showed both `orphaned-task-forensics/` and
`fleet-advisory-remediation/` present, tracked, and unchanged since their 2026-07-11 commit. The
Glob result was simply wrong — cause not diagnosed (possibly a path-resolution quirk with the
tool in this environment), but the negative result was trusted without cross-verification.

**Why this matters:** a negative search result reads as authoritative ("No files found") but is
only as reliable as the tool's own search mechanics for that specific path/pattern. Trusting it
without a second, differently-implemented check produced a materially wrong claim to Gabriel
("these skills have no repo home") and nearly left a real fix stranded in an ephemeral cache
copy instead of the actual source of record.

**How to apply:** before concluding a file/directory doesn't exist inside a known git repo based
on a `Glob` or `Grep` "no matches" result — especially before stating that conclusion to the user
as a fact, or before deciding "no durable home exists so I'll edit a fallback copy instead" —
cross-check with a direct `git ls-files | grep <name>` and/or `ls -1 <repo>` via Bash. The two
tools have different implementations and failure modes; agreement across both is real evidence
of absence, a single negative result is not. Generalizes beyond skills: any "X isn't tracked
anywhere" claim about a git-managed asset deserves this same cross-check before being reported
as settled. Related: [[feedback_verify_subagent_safe_claims]] and
[[feedback_verify_registry_mutation_claims]] — same family of lesson (don't trust one signal's
"safe"/"absent"/"complete" verdict without an independent second check), applied here to my own
tool output rather than a subagent's or a prior session's log entry.
