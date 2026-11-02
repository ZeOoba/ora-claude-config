# Spec: exclude session scratch paths from the plan gate's edit count

**Status:** DRAFT — awaiting Gabriel's review. Nothing applied to the live hook.
**Slug claimed:** `hooks-override-auth-plangate` (paths: `hooks/eos-plan-gate.py`)
**Sibling work:** session `109dd884` holds `hooks-override-auth` for the `ora-autonomy-gate.py`
half (OI-313). Disjoint paths, same root cause. Their fix should land first.
**Blast radius:** `hooks/**`. Requires a real review before merge; a bot check is not a verdict.

---

## Problem

`eos-plan-gate.py` denies the 4th+ code edit in a session that has no `plan-approved` or
`override` marker. It classifies by extension (`CODE_EXTS`) minus an `EXCLUDE_SUBSTR` list
(`/docs/`, `/memory/`, `node_modules`, `_smoke`). Files written to a session's own disposable
scratch area are `.py`/`.ts`/etc., match no exclusion, and therefore consume the 3-edit budget.

### Evidence

From `~/.claude/telemetry/lane-telemetry.jsonl` (schema v2, latest record per session, 759
distinct sessions):

| Measure | Count | Share |
|---|---|---|
| Sessions that used the plan-gate override | 187 | 24.6% of 759 |
| ...whose reason cites scratch / throwaway / disposable / read-only / "no product code" | 52 | 27.8% of 187 |

So roughly **1 session in 14** mints an override purely to write files that are deleted when the
session ends.

### The actual argument (not "the gate is annoying")

The gate offers two legitimate exits: run `/plan` or `/build`. Most of those 52 are **analysis**
sessions — mining transcripts, reconciling exports, hostile review — where there is no feature to
build and no bug to fix. Telling an investigation session to declare a build lane is a category
error, so the override is the only exit, and it gets minted for work that was never the gate's
target. That is a doctrine mismatch, not friction.

Counter-evidence worth keeping: session `4775456a` (2026-09-18) did a real L3 build, ran `/build`,
got `plan-approved`, and needed no override — the gate works exactly as designed when a lane
genuinely applies. The exclusion must not weaken that path.

---

## Proposed change

Exclude a file from the edit count when its **resolved** path sits under the per-session scratchpad
tree. Anchor + shape, never a bare prefix:

1. Resolve the temp root from `TMPDIR` / `TEMP` / `TMP` in `tempfile.gettempdir()`'s own order.
   Keep `gettempdir()` itself only as a guarded fallback inside `try/except`.
2. Refuse the anchor outright if the resolved temp root itself contains a site marker.
3. Require the shape `claude/<project-slug>/<session-id>/scratchpad/<file>` beneath that root —
   a prefix match alone is not sufficient.
4. Apply the shape check to the **same resolved string** the decision uses. Resolve once, match
   once.

### Findings folded in from session 109dd884 (peer review of this spec)

- **A bare module-level `tempfile.gettempdir()` can raise `FileNotFoundError`** when no candidate
  temp dir is writable. A hook that exits 1 is treated as NON-BLOCKING here, so an unhandled
  traceback silently disables the whole gate — strictly worse than the friction being fixed.
- **`gettempdir()` probes by creating and deleting a file.** Hooks are a fresh process per
  PreToolUse call, so a naive implementation performs a filesystem write on *every tool call in
  every session*. Hence reading the env vars directly.
- **Process env is influenceable from a Bash call**, so an env-derived anchor needs the shape
  requirement on top of the prefix — otherwise the exclusion is steerable by the thing being gated.
- **Literal-vs-resolved ordering is a live trap.** Their first draft matched the NORMALIZED path
  while the tool opens the LITERAL one, so a junction named `scratchpad` containing a zero-width
  space was exempted while bytes landed in a real checkout; fullwidth and combining-mark forms too.
  Reuse their test vectors from `hooks/tests/test-ora-autonomy-gate.py` rather than inventing new ones.

### Verified about the current file

`eos-plan-gate.py` today performs **no** realpath or normalization — `is_code_path()` does
`os.path.splitext()` plus raw substring tests. The ZWSP/fullwidth class therefore cannot bite it
yet; this change would introduce the first resolved-path matching in the file, which is exactly
when that trap arms.

Related non-issue, recorded so it is not rediscovered: the existing `EXCLUDE_SUBSTR` entries
(`/memory/`, `/docs/`) are raw substrings with no normalization, so a `mem<ZWSP>ory` path is not
excluded. That direction only makes the plan gate *more* conservative (it counts an edit it would
otherwise skip), so it is a nuisance, not a bypass.

---

## What this deliberately does NOT do

- **Does not touch `ora-autonomy-gate.py`.** That is session 109dd884's claim.
- **Does not widen anything to Gate 2b.** `memory/feedback_autonomy_gate_matcher_cannot_be_safely_narrowed.md`
  records four failed narrowing attempts; Round 4 (2026-08-13, OI-147) built a real quote/subshell-aware
  tokenizer and was still killed in round 1 of the gauntlet, because quoting suppresses metacharacters
  but does not remove text from the argument vector. The general problem is shell command *semantics*,
  not quoting state. Any fifth attempt needs the three-round adversarial gauntlet before it may land.
- **Does not exclude the whole OS temp tree.** An earlier version of this spec did. It is too broad:
  a disposable git clone under temp would stop counting entirely, and the anchor would be
  env-steerable.

## Acceptance

- TDD against `hooks/tests/test-eos-plan-gate.py` (subprocess + `EOS_SESSIONS_DIR` seam).
- New cases: scratchpad path excluded; look-alike outside the shape still counted; ZWSP/fullwidth/
  combining-mark junction still counted; unwritable/missing temp root degrades to "count it" and
  never raises.
- Existing cases unchanged — in particular, a session with no lane must still be denied on the 4th
  edit to real product code.

### Test vectors to mirror (source: session 109dd884)

Path-construction vectors come from `hooks/tests/test-ora-autonomy-gate.py` on branch
`fix/site-gate-slug-dir-exemption` (worktree `~/.claude/worktrees/site-gate-slug-exemption`).
**Dependency:** that branch had not merged when this spec was written. Reuse by name:

- `test_normalization_differential_junction_blocks` — three differential components, each
  junctioned to a sandbox dir whose NAME contains the marker: `scratchpad` with a ZWSP (category
  `Cf`, deleted by the strip); the fullwidth run `ｓｃｒａｔｃｈｐａｄ` (NFKC-folds to `scratchpad`);
  and `scratchpad` + combining low line (`Mn`, deleted).
- `test_invisible_char_junction_blocks_without_any_slug` — the pre-existing-on-main case,
  `mem<ZWSP>ory`, no slug involved.
- `_junction(link_path, target)` — `mklink /J` wrapper returning False when junctions are
  unavailable, so the test SKIPs loudly instead of passing vacuously.

**Reverse the expectations, not the vectors.** Their gate asserts "must BLOCK (exit 2)". Here the
same vector means "must NOT be silently excluded" — the plan gate's failure direction is
over-counting, which is conservative. Port the path construction; write our own assertions.

### Two methodology requirements (each cost them a rewrite)

1. **Assert each variant is NOT a normalization fixed point** before asserting behaviour. A vector
   that silently normalizes to itself makes the test pass while exercising nothing.
2. **Assert the junction was CREATED**, not merely that the exit code matched. Every junction test
   passes trivially if `mklink` failed and the path simply does not exist — check the run output
   for SKIP lines, not just the pass count. They verified 81/81 with zero SKIPs.

### Verified constant — do not copy, read it

`_STRIP_CATEGORIES = ("Cf", "Mn")`. Their caution was well placed: their own first draft used
`("Cf", "Mn", "Cc", "Me")`, which would have asserted the combining-mark case against the wrong
premise.

Read before use, because it is defined **twice, independently**, and both copies are pre-existing
on `main` (verified 2026-09-18 via `git show main:`):

| Definition | Consumers |
|---|---|
| `hooks/ora-autonomy-gate.py:382` (`_normalize_for_matching`) | that hook only — it does NOT import the lib |
| `hooks/lib/tool_call_paths.py:134` (`normalize_text`) | config-write-guard, eos-review-gate, lint-config-guard, memory-index-guard, memory-nag-correction, registry-write-guard, workbook-write-guard |

If the lib copy is ever hardened and the gate's is not, the autonomy gate silently becomes the
weakest normalizer in the hook layer while seven other guards are stronger. This exclusion should
consume the **lib** copy via `tool_call_paths`, never define a third.

**Why the lib copy specifically — and why "collapse them into one" is the wrong instinct.**
`hooks/lib/site_markers.py` already solves this class and its docstring is the precedent: two
hooks that must AGREE on a constant still must not CONSUME it the same way. It exports two tuples
deliberately, because `ora-autonomy-gate.py` substring-matches whole Bash command text as an
immediate hard block, while `confidentiality-guard.py` classifies a single file-path argument and
only blocks on an additional confidential-term hit. Unioning the domain-form aliases into the
whole-command matcher caused empirically-confirmed false-positive hard blocks on routine
operations, including the pre-authorized internal fleet send (2026-07-12 review finding).

`eos-plan-gate.py` reads `tool_input["file_path"]` — one path, never a command string. It is
therefore in the single-file-path family alongside the seven `tool_call_paths` consumers, not the
whole-command family. Consuming the lib copy is correct on that ground, not merely convenient.
Anyone who later takes the de-duplication item should read `site_markers.py` first: the likely
answer there is one shared constant with two distinct consumption rules, not one unified
normalizer.

*De-duplication status:* filed as its own unclaimed item by session 109dd884, deliberately kept out
of `fix/site-gate-slug-dir-exemption` — it would change the normalizer feeding the sole enforcement
of Invariant 2 (earning its own adversarial pass at Fable or above), and would void a review verdict
already in flight, since verdicts are keyed to staged content and do not survive an edit. Not a
dependency of this spec.
