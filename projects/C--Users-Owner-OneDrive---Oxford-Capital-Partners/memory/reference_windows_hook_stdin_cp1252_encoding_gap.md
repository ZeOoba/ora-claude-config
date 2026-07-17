---
name: reference-windows-hook-stdin-cp1252-encoding-gap
description: "A Claude Code PreToolUse/PostToolUse hook spawned directly by the harness on this Windows machine can get sys.stdin.encoding resolved to cp1252 (not UTF-8), silently corrupting any non-ASCII byte in the JSON payload before json.loads ever runs -- any hook doing exact-match/byte-comparison on payload content (not just ASCII substring checks) needs an explicit UTF-8 stdin decode."
metadata: 
  node_type: memory
  type: reference
  originSessionId: bc2d4e6b-45f9-42bd-9aba-61501d4f40cd
---

**The gap.** `sys.stdin.read()` in a Python hook script decodes using whatever
encoding Python resolves for that stream (`sys.stdin.encoding`,
`locale.getpreferredencoding(False)`). Confirmed live 2026-07-17, by direct
instrumentation of an actual harness-spawned `hooks/eos-claude-md-guard.py`
process: `sys.stdin.encoding == 'cp1252'` (Windows ANSI codepage), even
though the harness sends the PreToolUse JSON payload as UTF-8 bytes. Decoding
a UTF-8 em-dash (`E2 80 94`) as cp1252 produces 3 garbage characters
("â€"" mojibake) instead of 1 correct one. `json.loads()` still "succeeds"
(JSON's structural characters are ASCII) but string VALUES inside the parsed
object are silently corrupted.

**Why it's easy to miss.** `sys.stdin.encoding` reporting `cp1252` is NOT
reliably reproducible via synthetic `subprocess.run()` tests from a dev
shell — stripping `PYTHONUTF8`/`PYTHONIOENCODING`/`LANG`, or forcibly
setting `PYTHONIOENCODING=cp1252` in the child env, did NOT reproduce the
corruption on this machine, even though a separate diagnostic script showed
`cp1252` in both cases. Only the REAL harness-spawned process (likely a
Node.js `child_process` pipe on Windows, vs. Python's own `subprocess.Popen`
anonymous pipe) reproduced it. **Do not trust a synthetic repro's "it
decoded fine" as proof the bug is absent** — verify live, or unit-test the
decode helper directly with a monkeypatched `sys.stdin` (see
`hooks/tests/test-eos-claude-md-guard.py`'s
`test_read_stdin_text_decodes_utf8_independent_of_locale` for the pattern:
fake `.buffer`/`.read()`, no subprocess).

**When it actually matters.** Only when a hook does an EXACT MATCH or
byte-comparison against payload content that can legitimately contain
non-ASCII characters — e.g. `eos-claude-md-guard.py` diffing `old_string`
against CLAUDE.md's own prose (full of em-dashes/arrows/≥≤/middle-dots). A
hook that only checks ASCII substrings (file paths, `.env`/`credentials`
patterns, tool names) is unaffected — ASCII decodes identically under cp1252
and UTF-8.

**The fix pattern.** Read raw bytes and decode explicitly, never trust the
stream's own encoding:
```python
def _read_stdin_text():
    return sys.stdin.buffer.read().decode("utf-8")
```

**Known-affected surface — AUDITED, closed.** `grep -rn "sys\.stdin\.read()"
~/.claude/hooks/*.py` turned up 16 hooks with the identical unguarded
pattern. Full triage completed same session: 4 fixed
(`eos-claude-md-guard.py`, `confidentiality-guard.py`, `rules-md-guard.py`,
`memory-index-guard.py` — all four share the exact `simulate_edit()` /
`current_text.count(old)` shape, diffing stdin-derived `old_string` against
a correctly-UTF-8-read target file), 12 confirmed LOW-RISK (compare only
fixed ASCII literals/regexes/paths — unaffected regardless of decode).
`confidentiality-guard.py` (Invariant 3's fail-closed leak scanner) has the
inverse structure — the "needle" (confidential term) comes from clean file
I/O, the "haystack" (`scan_text`) from stdin — so it's exploitable only when
an active confidential TERM itself contains a non-ASCII character (verified:
the live roster's one deal, `e_fulton`, is 100% ASCII, so not live-exploited
today, but the fix was applied proactively). Its fix also required moving
the read INSIDE the existing try/except (previously outside it) since
strict `.decode("utf-8")` can raise where the old `sys.stdin.read()`
essentially never did, and an uncaught exception on a fail-closed gate would
exit 1 (non-blocking) — a silent fail-OPEN regression. `rules-md-guard.py`
and `memory-index-guard.py` are fail-OPEN by design, so no such
restructuring was needed there. All four fixes verified via mutation testing
(revert `_read_stdin_text()`, confirm new tests fail cleanly) and a
dedicated adversarial refute pass each (all SHIP verdicts). Commits:
414de37, 8385220, 417abf6.

**Adversarial-review catch worth repeating.** The first regression test
written for this fix used `json.dumps({"old_string": "em dash — test"})`
with the default `ensure_ascii=True`, which `\u`-escapes the em-dash to pure
ASCII *before* `.encode("utf-8")` — so the test payload never actually
contained a multi-byte UTF-8 sequence, and passed even against the unfixed
code. Caught only by a dedicated adversarial refute pass, confirmed by
mutation-testing (revert the fix, confirm the test now fails). Any test for
this class of bug MUST use `ensure_ascii=False` (or a literal non-ASCII
string) to actually put multi-byte bytes on the wire.
