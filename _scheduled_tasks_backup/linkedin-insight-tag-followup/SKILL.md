---
name: linkedin-insight-tag-followup
description: One-time reminder: check if LinkedIn Campaign Manager's 2FA gate has cleared and retrieve the Insight Tag Partner ID for oxfordra.net
---

Remind Gabriel Goldberg to follow up on the LinkedIn Insight Tag Partner ID for oxfordra.net.

Context: On 2026-07-16, Gabriel authorized retrieving the real LinkedIn Insight Tag Partner ID for oxfordra.net's analytics instrumentation (a site-wide fix replacing a placeholder GA4/LinkedIn snippet across all pages). The GA4 side is already done — the real Measurement ID (G-YDSX0RW5HC) was found already provisioned in Google Analytics and wired into all 16 relevant HTML files in C:/Users/Owner/website-canonical, committed locally (commit df2bc2a on branch main, not pushed).

The LinkedIn side is blocked: LinkedIn Campaign Manager (account ID 547184587, "Oxford Realty Advisors, LLC") is gated behind a mandatory "We're upgrading your account security — setup two-step verification" modal with no dismiss/close option — it blocks every page in Campaign Manager including the sidebar nav. Gabriel completed 2FA setup on 2026-07-16, but the gate was still showing immediately afterward, even in a brand-new browser tab with the session still logged in. This is most likely a propagation delay on LinkedIn's end.

What to do when this task fires:
1. Ask Gabriel whether he has since gotten LinkedIn Campaign Manager to load past the 2FA gate.
2. If yes and he has the Insight Tag Partner ID (a numeric value, found under Campaign Manager > Account Assets > Insight Tag), take the ID and replace the placeholder `_linkedin_partner_id='XXXXXXX'` (appears twice per file: the `window._linkedin_partner_id=` assignment) across all 16 files in C:/Users/Owner/website-canonical: 404.html, about.html, application-received.html, available-space.html, contact.html, for-brokers.html, index.html, markets/columbus-oh.html, markets/index.html, markets/maryland.html, portfolio.html, privacy.html, tenant-application.html, tenant-resources.html, terms.html, track-record.html.
3. Before editing, run `git status` in that repo — there may be other uncommitted/concurrent work from other sessions in the same shared checkout (this happened during the GA4 swap). Isolate only the LinkedIn ID hunks the same way: verify each file's diff only contains the 1-line _linkedin_partner_id change before staging, and use `git add <specific files>` rather than `git add -A`.
4. Run `node --test` in the repo to confirm nothing broke.
5. Commit locally with a clear message (do NOT push — pushing to main auto-deploys to production oxfordra.net per this repo's Netlify integration, and that requires Gabriel's separate explicit in-turn confirmation every time).
6. If Campaign Manager is still gated or Gabriel doesn't have the ID yet, ask if he wants to keep waiting or investigate directly with LinkedIn support, and do not create another follow-up task unless he asks for one.

This is a one-time reminder — it will auto-disable after firing regardless of outcome.