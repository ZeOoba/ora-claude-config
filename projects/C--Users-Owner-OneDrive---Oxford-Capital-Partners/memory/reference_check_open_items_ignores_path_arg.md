---
name: reference_check_open_items_ignores_path_arg
description: "check-open-items-duplicate-ids.py takes NO arguments — it always reads the canonical live tracker and ignores any path you pass, while PRINTING that canonical path as though it were your input. Any 'differential' built on it silently compares one file to itself."
metadata: 
  node_type: memory
  type: reference
  originSessionId: 1d88885d-fe6f-4999-a3fd-011a313384b4
  modified: 2026-08-09T16:05:00.000Z
---

# A checker that prints a path it did not read

`maintenance/check-open-items-duplicate-ids.py` **accepts no CLI arguments.** It always reads
the canonical live tracker at
`~/.claude/projects/C--Users-Owner-OneDrive---Oxford-Capital-Partners/memory/open-items-tracker.md`.
Pass it a path — a temp file, a `git show` export, a worktree copy — and it will ignore your
argument, read the canonical file anyway, and then **print the canonical path in its own
output header** as if that were what you asked for. Even `--help` just runs the check.

That last detail is what makes it a trap rather than a limitation: the output *looks* like it
is reporting on your file, because it names a plausible path.

## The failure it caused (2026-08-09)

A pre-push gate blocked on `ORPHANED_SECTION OI-111`. To decide whether the defect was
committed or another session's transient WIP, this was run:

```
git show main:...open-items-tracker.md > /tmp/tracker-committed.md
python maintenance/check-open-items-duplicate-ids.py /tmp/tracker-committed.md   # "committed"
python maintenance/check-open-items-duplicate-ids.py ...open-items-tracker.md    # "working tree"
```

Both printed identical findings, and that was reported to Gabriel as evidence that *"the
defect is present in the committed version, identical to the working tree — so it is not
transient WIP,"* which in turn was used to justify minting an override token.

**Both invocations had read the same live file.** The "differential" compared a file to
itself, so of course it matched. The real answer was the opposite: grepping the committed
blobs directly showed OI-111 (and later OI-112) existed **only** in the live working tree and
were committed nowhere — genuinely transient WIP that cleared on its own. Waiting would have
worked; the override was never needed, and two later pushes passed the gate with no token at
all.

It was caught only because a later run reported `### OI-112` as orphaned in a file that
provably did not contain that string.

## How to actually diff tracker state

Never route a committed-vs-working comparison through this checker. Read the blobs:

```
P=projects/C--Users-Owner-OneDrive---Oxford-Capital-Partners/memory/open-items-tracker.md
for ref in origin/main HEAD; do
  git show $ref:"$P" | grep -c "^### OI-111"   # sections
  git show $ref:"$P" | grep -c "^| \[OI-111\]" # table rows
done
grep -c "^### OI-111" "$P"                     # live working tree
```

A section count > 0 with a row count of 0 is the ORPHANED_SECTION condition.

## The general lesson

**A tool that echoes a path is not thereby proving it read that path.** Before treating any
checker's output as a differential, confirm it actually consumed the input you handed it —
cheapest test is to pass a path that cannot possibly produce the observed finding (a
nonexistent file, or a copy with the finding removed) and see whether the output changes. If
it doesn't, the argument is decorative.

This sits alongside the rest of the verify-before-trusting family: the defect was not that the
tool was wrong, but that its output was **shaped like** an answer to a question it never asked.

Related: [[feedback_verify_probe_findings_before_acting]] · [[feedback_verified_null_vs_inferred_null]] · [[feedback_self_flattering_error_bias]] · [[open-items-tracker]]
