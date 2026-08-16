---
name: reference-disable-autoupdater-blocks-manual-update
description: "DISABLE_AUTOUPDATER=1 also breaks the MANUAL `claude update`, not just background updates — it fails with a misleading \"npm registry unreachable\" error"
metadata: 
  node_type: memory
  type: reference
  originSessionId: 76023481-9a6c-40ff-b91f-8bd263f287d8
  modified: 2026-08-16T20:57:55.833Z
---

`DISABLE_AUTOUPDATER=1` is set in the OS environment on this machine (not in `~/.claude/settings.json`'s `env` block, which holds only `NETLIFY_SITE_ID` and `USER`). It suppresses the **manual** `claude update` version check too — not just background auto-updates, which is what the documented behavior implies.

**The failure is misleading.** `claude update` reports:

```
Failed to check for updates
Unable to fetch latest version from npm registry
Possible causes: Network connectivity issues / npm registry is unreachable / Corporate proxy...
```

All three suggested causes are wrong. Verified 2026-08-16: `npm config get registry` → `https://registry.npmjs.org/`, no proxy, no `~/.npmrc`, and a plain `npm view @anthropic-ai/claude-code version` from the same shell returned `2.1.233` immediately. The registry was reachable the whole time.

**The working invocation:**

```bash
env -u DISABLE_AUTOUPDATER claude update
```

That succeeded on the first try (2.1.232 → 2.1.233, confirmed by `claude --version`).

**Why it matters:** with `autoUpdates: false` AND this env var set, there is no signal at all that a version is available — the background path is off by design and the manual path lies about why it failed. Version drift is silent. Check periodically with the `env -u` form rather than trusting `claude update`'s error text.

Found during the `/doctor` pass on 2026-08-16; see [[reference-hookify-noop-hooks-every-tool-call]] from the same pass.
