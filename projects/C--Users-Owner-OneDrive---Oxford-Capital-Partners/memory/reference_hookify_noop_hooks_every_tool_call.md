---
name: reference-hookify-noop-hooks-every-tool-call
description: "The hookify plugin runs pre+post hooks on EVERY tool call with zero rules configured — 225,556 no-op invocations; it is Cowork-enabled, so there is no Code-side key to disable it"
metadata: 
  node_type: memory
  type: reference
  originSessionId: 76023481-9a6c-40ff-b91f-8bd263f287d8
  modified: 2026-08-16T20:58:08.780Z
---

The `claude-plugins-official` **hookify** plugin registers `hooks/pretooluse.py` and `hooks/posttooluse.py` against **every tool**, and on this machine it has **no rules to evaluate**.

`core/config_loader.py:210` globs `.claude/hookify.*.local.md` relative to cwd. No such file exists anywhere under `~/.claude` (the only matches are the plugin's own `examples/`). Every invocation therefore loads an empty ruleset and returns `{}` — confirmed by the recorded `stdout: "{}"` on sampled transcript attachments. `pluginUsage` shows **225,556 lifetime invocations**, the largest of any plugin by two orders of magnitude.

**The cleanest measurement of its cost:** no ORA hook in `~/.claude/settings.json` matches `Read`, so 100% of Read-event hook latency is hookify alone. Over 180 session transcripts (2026-08-09 → 2026-08-16): `PreToolUse:Read` n=32, **median 1,563 ms**, p90 2,891 ms; `PostToolUse:Read` median 1,399 ms. Individual samples ran 179–546 ms. On every other tool it stacks on top of the ORA guard chain.

**⛔ Do not look for it in Claude Code settings.** hookify is absent from `~/.claude/plugins/installed_plugins.json` (5 plugins listed, none hookify) and absent from `~/.claude/settings.json` `enabledPlugins`. It is enabled at the Cowork/desktop-app layer as `hookify@inline`. There is **no Code-side key to flip** — disabling it requires `/plugin` from a Cowork session. A prior read of the empty `plugins/data/hookify-*` dirs briefly looked like evidence hookify was inert; it is not — the empty dirs are the *confirmation* that it fires and does nothing.

Tracked as OI-176 (half 1) in [[open-items-tracker]]; the companion half is the 10-deep `PreToolUse:Bash` chain. Found during the `/doctor` pass 2026-08-16, alongside [[reference-disable-autoupdater-blocks-manual-update]].
