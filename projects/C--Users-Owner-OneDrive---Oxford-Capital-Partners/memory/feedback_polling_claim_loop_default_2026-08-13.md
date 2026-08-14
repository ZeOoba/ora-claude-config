---
name: feedback-polling-claim-loop-default-2026-08-13
description: "when a shared-checkout claim (active-work slug, staged-file contention, contested tracker row) is held by another live session, wait and re-check rather than force through with --force/allow_other_staged_paths; short re-checks (minutes, not one-shot) clear reliably"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: b34ec269-3c65-4bc6-ba23-039298513853
  modified: 2026-08-13T04:32:41.200Z
---

Default to a short polling-wait when blocked by another session's live claim on a shared `~/.claude` resource — an `active-work/<slug>.json` claim, a `_assert_no_other_staged_changes` refusal from `hooks/lib/isolated_commit.py`, or a contested `open-items-tracker.md` row — rather than immediately forcing through with `--force`/`--steal`/`allow_other_staged_paths=True` or abandoning the isolated approach for a broad commit.

**Why:** demonstrated live twice in one session (2026-08-13): `open-items-tracker` claim contention cleared in 4 minutes and 1 minute on two separate occasions after simply re-checking rather than forcing. The same session also independently hit `git diff --cached --name-only` staging contention on the live `~/.claude` checkout (4 files staged by another session, blocking an isolated commit of an unrelated single-file fix) — left the fix safely uncommitted in the working tree and moved on to other work rather than forcing a commit or waiting synchronously, matching the same "don't force, don't block on it either" principle. This checkout runs 15+ concurrent sessions; nearly all contention is transient (another session finishing its own commit), not a stuck/abandoned claim.

**How to apply:** when `claim_work.py claim` refuses (exit 3) or `stage_isolated_replacement`/`commit_isolated_replacement` refuses due to other staged paths:
1. Re-check state (re-run `claim_work.py list` or `git diff --cached --name-only`) after a short interval — a few minutes is usually enough per the observed 1-4 minute clear times.
2. If still contended and the work isn't urgent, leave your own change safely applied-but-uncommitted (working-tree edit, or the isolated hunk still staged) and continue with other work in the same turn rather than blocking synchronously on a wait loop.
3. Reserve `--force`/`--steal`/`allow_other_staged_paths=True` for when the holder is confirmed unreachable (an unattended scheduled-task session) or the delay is genuinely blocking something time-sensitive — not as the default first response to contention.

This should be the documented default rather than something each session improvises from scratch, per the optimization-queue item that prompted this note: two independent ad-hoc uses of the same wait-and-recheck pattern in one session, both successful, neither previously written down anywhere.
