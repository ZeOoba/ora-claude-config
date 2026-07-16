---
name: feedback_website_model_tier
description: "Gabriel wants the highest-intelligence model used for all oxfordra.net / website-canonical work, overriding normal dispatch-tier defaults."
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 8ef6e0f7-7c20-46c8-9934-b6b3881e4941
---

For this and all future sessions touching the oxfordra.net website (`website-canonical`, `oxford-site`, Netlify deploys, CSS/CSP/content fixes), always use the highest-intelligence model available (currently Opus 4.8) — do not downgrade to sonnet/haiku dispatch tiers even for what looks like mechanical work.

**Why:** Gabriel said this explicitly (2026-07-09) while confirming a production oxfordra.net deploy (merge `logo-svg-fix` branch fix). Website work sits behind Hard Invariant 2 (never touch oxfordra.net without explicit per-deploy permission) — he wants the best available reasoning applied whenever that invariant is in play, not just for the deploy confirmation itself but for the surrounding investigation/fix work too.

**How to apply:** When Engineering OS dispatch (`CLAUDE.md` Engineering OS section) would normally pick sonnet/haiku for a website-touching task, pin opus instead. This is an explicit exception to the general "opus default · sonnet = standard implementation · haiku = mechanical" dispatch rule — narrower in scope (website only) but overrides the tier logic within that scope.
