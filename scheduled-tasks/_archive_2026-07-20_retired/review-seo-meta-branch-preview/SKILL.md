---
name: review-seo-meta-branch-preview
description: One-time reminder to review the oxfordra.net SEO metadata fix branch/preview before merge
---

Send Gabriel a reminder (do not take any other action, do not edit any code, do not touch website-canonical) with the following content:

Subject/summary: Review the oxfordra.net SEO metadata fix branch before merging

Body: 
"Reminder: yesterday (2026-07-18) an SEO metadata fix was prepared for oxfordra.net and pushed to a branch, but deliberately NOT merged to main (merging that repo's PRs auto-deploys to production).

- Branch: fix/seo-meta-lengths-202607 (repo: C:/Users/Owner/website-canonical, remote github.com/ZeOoba/Website)
- Commit: 2568e09
- Netlify draft preview: https://6a5bd49eacf340563e64a414--snazzy-frangipane-de3841.netlify.app
- Change: trimmed homepage/about/portfolio/markets-columbus-oh titles+descriptions to SERP-safe lengths, padded privacy/terms descriptions, added /tenant-application to sitemap.xml. Reviewed and approved by the site-qc-reviewer agent (no confidential-data leakage, no broken links).
- Two pre-existing (not introduced by this fix) copy quirks were flagged for a future content pass: portfolio.html's meta description lists 3 markets while its own og:description says 'four core markets'; the Columbus market page title is 69 chars (over the 60-char SERP-safe proxy, kept intentionally to preserve full brand-name consistency with the Maryland market page).

No action has been taken since — the draft preview is still live and the branch has not been touched. Ask Gabriel whether he wants to review the preview now and, if satisfied, proceed to open a PR and then merge (merge = production deploy on this repo, requires his separate explicit in-turn confirmation per Hard Invariant 2), or whether he wants further changes first."

If a routing/notification path exists for this session type, send this to ggoldberg@oxfordra.net only (no cc), matching the standing email routing canon. If no send mechanism is appropriate for this context, simply surface the reminder text as this task's output/message.

This is a one-time task — do not reschedule or repeat it.