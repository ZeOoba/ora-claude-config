---
name: project-ora-pm-outage-2026-10-28
description: ora-pm 500s on cron endpoints since 10-13 traced to the Supabase project host no longer resolving (NXDOMAIN), plus GitHub Actions jobs refused for billing since 10-06; Gabriel must check Supabase and GitHub billing
metadata:
  type: project
---

Found during R33 remediation Phase 0 (read-only). Chains [[project-automation-audit-rev33-2026-10-28]].

**Fact 1 (high confidence):** `tvfarkddtbtdrpvvehth.supabase.co` (the project ref in `ora-pm/.env`, `.github/workflows/db-migrate.yml`, `supabase/.temp/project-ref`) returns NXDOMAIN from the local router, 8.8.8.8 and 1.1.1.1, while supabase.com resolves. `https://ora-pm.pages.dev/api/health` still returns 200 (does not touch the DB); cron routes return 401 unauthenticated and 500 authenticated, because every route reads Supabase. Cron log `ora-pm-cron/cron.log`: last HTTP 200 on 2026-10-05, 500 on 10-13, 10-19, 10-26. Not confirmed: that the Cloudflare Pages secret `SUPABASE_URL` equals the `.env` value (secrets are encrypted), and whether the project was deleted, paused or suspended.

**Fact 2 (high confidence):** every GitHub Actions job in ZeOoba/ora-pm since 2026-10-06 is refused: "The job was not started because recent account payments have failed or your spending limit needs to be increased." This includes the off-host `Delinquency check` (daily) and CI on main; `monthly-billing-backup.yml` (cron `40 17 1 * *`, last success 2026-10-01) will fail the same way on 11-01, so the off-host safety net for billing is down.

**Not a code regression:** last production Pages deploy is `538180a` (10-03, docs only); main commit 10-15 failed CI under Fact 2.

**Why:** property-manager data lives in that Supabase project: charges, payments, tenant portal, delinquency, critical dates. No delinquency email or critical-date alert since 10-05; OI-278 state file stale for the same reason.
**How to apply:** do not re-trigger cron endpoints to "test" (delinquency-check emails and posts late fees). Gabriel checks the Supabase dashboard (deleted/paused/restorable, backups) and GitHub Billing & plans; then re-run the cron manually and confirm `ora-pm-monthly-billing` before Sun 2026-11-01 11:10.
