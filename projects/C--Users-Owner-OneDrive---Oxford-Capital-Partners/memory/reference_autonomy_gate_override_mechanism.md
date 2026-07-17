---
name: autonomy-gate-override-mechanism
description: "Override tokens for BOTH gates (ora-autonomy-gate.py + git-prepush-doctrine-gate.py) are session-scoped (hooks/sessions/<session_id>/overrides/), severity-split, content-bound (scope+session must match), single-use on the deploy/send tiers; one shared validator since 2026-07-17 (hooks/lib/override_tokens.py). The old flat mtime-only sentinel is RETIRED. HONEST LIMITS: session identity is SELF-ASSERTED — this is scoping, NOT authentication (a session that exports another's id replays its token, and the audit log blames the exported id); it cannot defend against the session that WRITES the token; and tokens are not 'un-committable' — gitignore does not protect already-tracked files. Never describe these gates as authenticating or tamper-proof."
metadata: 
  node_type: memory
  type: reference
  originSessionId: 3fc20af9-9fcb-4681-a66a-c6eb07fdd7db
---

> **✅ LIVE on `main` as of 2026-07-16 23:43** — commits `927f6d0` + `f528fe0`, fast-forwarded onto
> `871f5d3` after both land-blockers cleared (token TTL expired; concurrent session `01a43b3e`'s
> dirty-file set stable/untouched for 3.5+ min). Verified post-land: `grep -c session_id
> hooks/ora-autonomy-gate.py` = 40 (non-zero), full suite green on real `main` paths (44 + 3
> tests), the other session's 30 uncommitted files byte-identical before/after (hash-compared).
> The retired flat token was archived (not deleted) to `hooks/archive/allow-website-change.retired-
> 2026-07-16`. If this note ever looks stale, re-verify with the same grep before trusting it.

`hooks/ora-autonomy-gate.py` enforces Hard Invariants 1 (external send) and 2 (oxfordra.net)
under `defaultMode=bypassPermissions`. Hardened 2026-07-16 (Gabriel-ratified). The old override
was a flat, mtime-only sentinel at `hooks/overrides/<name>` — content-blind, session-blind, one
name (`allow-website-change`) for all four Gate-2 paths, and git-trackable (a `git clone` minted a
live prod-deploy grant with age ~0; proven end-to-end). That mechanism is GONE.

**Current mechanism — an override token lives at:**
`hooks/sessions/<session_id>/overrides/<name>` (that dir is gitignored, which defeats the `git
add -A` sweep — but see HONEST LIMIT (c): it is NOT "structurally un-committable"). Content must be:

```
scope: <the tier's scope>
session: <the session_id it was minted in>
recipients: a@x.com, b@y.com    # allow-external-send ONLY; every external recipient
reason: <free text, audit only>
```

**Three tiers (one name = one severity):**
- `allow-website-write` — scope `website-write`, 60 min, MULTI-use → Gate 2b (shell write into
  site tree) + check_file_write (Edit/Write/MultiEdit/NotebookEdit into the tree).
- `allow-website-deploy` — scope `website-deploy`, 5 min, SINGLE-use (consumed at gate-pass) →
  Gate 2a (`netlify deploy --prod`) + Gate 2c (Netlify MCP `*-updater`).
- `allow-external-send` — scope `external-send`, 5 min, SINGLE-use, AND must name every external
  recipient of the send → Gate 1.

Fails CLOSED on: no/invalid session_id, no token, wrong scope, wrong inner session, retired name,
unparseable/oversized/duplicate-key content, future-dated mtime, un-consumable single-use token,
recipient not named, or a gated tool with a malformed input shape (non-dict tool_input /
non-string command|path → block_shape, exit 2). Only an UNPARSEABLE hook payload fails open (by
design — don't brick every tool call).

**HONEST LIMITS — read before claiming these gates are "secure".** The canonical copy lives in
`hooks/lib/override_tokens.py`; this is the summary a session needs when reasoning ABOUT the gates
without opening them:

- **(a) It cannot defend against the session that WRITES the token** — that session can write any
  scope it likes. The gate cannot tell a Gabriel-approved token from a self-granted one.
- **(b) Session identity is SELF-ASSERTED — this is SCOPING, NOT AUTHENTICATION.** Nothing
  authenticates the session id. The autonomy gate reads it from the PreToolUse payload; the
  doctrine gate reads `CLAUDE_CODE_SESSION_ID` from the environment, which the *pushing process
  supplies itself*. So session-scoping stops a concurrent session from ACCIDENTALLY inheriting a
  live token — the real 4+-sessions-running failure it was built for — but a session that
  deliberately exports another session's id **replays that session's token**, and the event_log
  then blames the id that was exported, not the actor. Demonstrated by adversarial review
  2026-07-16: control (own id) → exit 1 BLOCK; attack (exported id) → exit 0, drift pushed.
  Closing it needs a channel the caller cannot forge; there isn't one at this layer. **Do not
  describe these tokens as authenticating, per-session-proof, or tamper-proof.**
- **(c) "Structurally un-committable" is about the SWEEP, not about git.** `hooks/sessions/` being
  gitignored defeats the `git add -A` that caused the original defect (`668f9d4`, again in
  `8afad84`) — but a deliberate `git add -f` still tracks a token, and **.gitignore does not
  protect ALREADY-TRACKED files**: any ref that tracks one re-mints it at age ~0 on checkout. Not
  hypothetical — after `b23a025` cleaned `main`, the token was still tracked on
  `commit-provenance-guard`, and `git checkout` of that branch self-granted a 60-min prod-deploy
  window. The durable guard is `test-override-token-hygiene.py`, which scans **every ref**, not
  just the index (an index-only `git ls-files` check was blind to exactly that case).

What the mechanism DOES buy over the retired sentinel: clone/checkout-minting via the ordinary
sweep, `touch`-minting, accidental cross-session inheritance, mis-scoped reuse — and an audit
trail that records who overrode and why. The teeth are session-scoping + severity-split +
single-use.

**Test seam:** `ORA_OVERRIDE_SESSIONS_DIR` (was `OVERRIDE_DIR`) — TEST ONLY, never set in
settings.json/production. Tests: `hooks/tests/test-ora-autonomy-gate.py` (44) +
`test-override-token-hygiene.py` (git-untrackability, added by the concurrent b23a025 fix).

**Do NOT touch the matcher** (`SITE_PATH_MARKERS`/`SITE_WRITE_INDICATORS`/block conditions) — see
[[feedback_autonomy_gate_matcher_cannot_be_safely_narrowed]]. This hardening was strictly on the
authorization axis (WHO/WHAT a grant authorizes, for how long), never WHAT is matched.

**ONE CONTRACT, TWO GATES (2026-07-17).** Superseded: the sibling gate no longer uses the old flat
pattern. `git-prepush-doctrine-gate.py` (`allow-doctrine-drift`, scope `doctrine-drift`, 60 min,
multi-use) was session-scoped + content-bound in `a64f2e5`, and `6efd943` moved BOTH gates onto one
shared validator — `hooks/lib/override_tokens.py` (path/traversal, size cap, UTF-8, duplicate-key
refusal, TTL + clock-skew + future-dating, single-use consumption). Read that module first; it is
the canonical home for the contract and its limits. Each gate keeps only what the module cannot
know: its tiers, and any domain binding (Gate 1's recipient naming rides in as `token_grants`'
`extra_check`, which runs BEFORE consumption so a failing token is refused without being burned).

Consequences worth knowing:
- The doctrine gate reads its session from **`CLAUDE_CODE_SESSION_ID`** (a git hook gets no
  payload). A push from a bare terminal carries none, so it **cannot be overridden at all** — fix
  the drift instead. Mint the token in the session that will PUSH: a subagent has its own id.
- **The coupling cuts both ways** — an edit to the shared module made for one gate can break the
  other. Live example: adopting the module bare-imported it, and a PreToolUse hook exiting 1 is
  NON-BLOCKING, so an ImportError silently disabled Gates 1+2 (prod deploy passed through). It now
  degrades to "no override exists"; `test_broken_token_module_fails_closed` guards it. Do not
  "simplify" that try/except away, and do not `sys.exit(2)` at import — that bricks every tool call
  ([[feedback_confidentiality_guard_selfdeadlock]]).

Tests: `test-ora-autonomy-gate.py` (45) · `test-git-prepush-doctrine-gate.py` (37) ·
`test-override-tokens-lib.py` (15 — covers `extra_check` + consume-ordering, unreachable through
either gate) · `test-override-token-hygiene.py` (all refs). Related:
[[autonomy-gate-blocks-writes-not-reads]].
