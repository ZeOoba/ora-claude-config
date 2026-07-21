---
name: reference-skill-args-positional-substitution-bug
description: "Skill tool's `args` string does bash-style $N positional substitution against SKILL.md body text — corrupts literal dollar amounts in any skill with a non-empty multi-word args"
metadata: 
  node_type: memory
  type: reference
  originSessionId: 84e4287b-fdaa-4f07-b075-813d5d381093
  modified: 2026-07-21T17:34:49.515Z
---

Calling `Skill({skill, args})` with a non-empty `args` string causes the harness to scan the rendered SKILL.md body for bare `$<digit>` tokens and replace each with the Nth (0-indexed) whitespace-split word of `args` — a bash/Claude-Code-slash-command-style positional-parameter substitution applied to plain prose that was never authored with placeholders in mind. Confirmed root cause location: inside the compiled, closed-source `claude.exe` binary shipped as the global npm package `@anthropic-ai/claude-code` (v2.1.214 on this machine, `node_modules/@anthropic-ai/claude-code/bin/claude.exe`) — there is no readable/patchable JS source, only `cli-wrapper.cjs` (a no-op fallback launcher) and the compiled binary itself. Not part of `ora-skills`, not part of any repo Gabriel owns.

**Confirmed behavior (two live tests this session, 2026-07-21):**
1. `exception-detection` + args="Targeted scan: Category 2 tenant exceptions only, with emphasis..." → `$5,000`→"exceptions,000" (word[5]), `$0`→"Targeted" (word[0]), `$2.50`→"Category.50" (word[2]). Exact 0-indexed match.
2. Controlled re-test with args="zero one two three four five six seven" → same three tokens corrupted predictably (`$5,000`→"five,000" etc.) **but** `$5K/mo` elsewhere in the same file was left untouched. The substitution regex appears to require the digit run be followed by a non-word-character (space/comma/period) — a `\b`-style boundary — so `$5,000`/`$0`/`$2.50` qualify but `$5K` (letter immediately follows the digit) does not. This looks like an intentional but incomplete guard against corrupting "$5K"/"$10M" shorthand — it does not protect comma-formatted or decimal dollar amounts, which is the common style in ORA's financial skills.
3. Skills whose body has NO `$<digit>` substrings are unaffected — args is instead appended verbatim as a trailing "ARGUMENTS: <raw string>" line (confirmed via the same-session `/debug` skill invocation, which has no dollar figures and rendered cleanly).

**Scope — confirmed vs unconfirmed:**
- Confirmed: interactive `Skill({skill, args})` calls are exposed whenever the target SKILL.md contains a `$<digit>` followed by a non-letter, AND args has enough whitespace-split words to reach that index.
- Unconfirmed (not tested — would require a live scheduled-task trigger, too risky to force): whether the scheduled-task runner invokes SKILL.md bodies through this same args-templating code path. Grep found 9 scheduled-task SKILL.md files on this machine with literal `$<digit>` patterns exposed to the same regex shape if that path is shared: `ora-deal-sourcing-scan`, `ora-pm-ledger` (`$979,772`, `$553,045`, `$252,000`, `$10M`), `ora-broker-touch-cadence`, `ora-am-brief` (×2 copies), `ora-entry-market-scan`, `ora-health-guard`, plus 2 archived orphans. Scheduled tasks likely don't supply a runtime `args` string at all (no `args` references found in `register-scheduled-task` docs), which would make this moot for them — but that's inference, not verified.
- Workflow scripts (`agent()` prompt strings) are very likely a separate code path — the prompt is a plain string assembled by the script, not a SKILL.md rendered via the Skill tool's args mechanism — but this is reasoned, not source-verified (binary is compiled/unreadable).

**Why:** No local fix exists — this is Anthropic's proprietary compiled binary, not an editable file. [[feedback_verify_probe_findings_before_acting]] applies: this write-up is itself a hypothesis grounded in two direct reproductions, not a vendor-confirmed root cause.

**Filed upstream:** [anthropics/claude-code#79859](https://github.com/anthropics/claude-code/issues/79859) (2026-07-21, Gabriel-confirmed) — repro, root-cause evidence, and the appended-context-only fix recommendation are in the issue body. Check this issue for a fix/patch release before re-verifying the mitigation below is still needed.

**How to apply:** Until the linked issue ships a fix, treat any `Skill(..., args:)` call to a financial-numbers-bearing skill (`exception-detection`, `acquisition-underwriting`, `disposition-analysis`, `capex-budgeting`, `cash-position-monitor`, `debt-management`, and likely most of `ora-skills`) as unsafe when args is a non-trivial multi-word string. Prefer invoking with no `args` (state scope in the next chat turn instead) or verify rendered dollar thresholds against the source SKILL.md before trusting them in-session.
