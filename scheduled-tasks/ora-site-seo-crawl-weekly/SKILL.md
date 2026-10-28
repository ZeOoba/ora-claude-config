---
name: ora-site-seo-crawl-weekly
description: Weekly Wednesday 14:10 ET read-only live crawl of oxfordra.net against the website-perfection SEO invariants; silent when at baseline, emails ggoldberg only on a regression. Never edits or deploys the site. [MODEL: claude-sonnet-5-5 | set 2026-10-13]
---

You are running the weekly oxfordra.net SEO regression crawl for Oxford Realty Advisors (Gabriel Goldberg). This task is READ-ONLY. Hard Invariant 2: never edit, build or deploy oxfordra.net, website-canonical or oxford-site, and never open a PR. Do not use Bash commands that name the website-canonical path.

STEP -1. — DOUBLE-FIRE ENTRY GUARD (run first)
python C:/Users/Owner/.claude/scheduled-tasks/_shared/block-sentinel.py claim --task ora-site-seo-crawl-weekly --block main --run-id <run_id> --period week --ttl-min 30 --scheduled-et 14:10
- Exit 10 = this week already completed; Exit 11 = another fire is live. Stand down: no crawl, no email; report a NORMAL skip.
- Exit 0 = proceed.
After the run finishes (at baseline: no email, `complete` with no --email-sent-at; on a regression email: with it): `... block-sentinel.py complete --task ora-site-seo-crawl-weekly --block main --run-id <run_id> --period week --email-sent-at <ISO8601> (only when an email was sent: a regression or a STEP 1/2 tooling-failure email)`. On abort, and on a send that ends in failure (exit 5, or exit 2 or 4 once its single repeat is spent; exit 6 is the exception, see the send step): `... fail ... --error "<what broke>"` (never `complete` without a real `--email-sent-at`, except exit 6: see the send step when an email was owed). Only the claim holder calls complete/fail. ALWAYS pass `--period week`.

STEP 0. Compute the run date and weekday once: `date '+%A %Y-%m-%d'`. Reuse it everywhere.

STEP 1. Locate the crawler. It is `seo_crawl.py` in the website-perfection skill. Search `C:\Users\Owner\AppData\Roaming\Claude\local-agent-mode-sessions\skills-plugin\*\*\skills\website-perfection\scripts\seo_crawl.py` (glob; several copies may exist, pick the newest by mtime). If it cannot be found, STOP and email the failure (STEP 4) saying the crawler is missing.

STEP 2. Run it (stdlib only, GET/HEAD against the public site): `python -I <path-to-seo_crawl.py> --json <a temp file in the system temp dir>`. Exit 0 = crawled; exit 2 = sitemap unreachable (treat as a failure, retry once after 60 seconds, then report). Read its Findings table (HIGH / MED / LOW counts).

STEP 3. Compare to the baseline (verified 2026-10-13): HIGH 0, MED 0, LOW 1, where the single known LOW is "/tenant-application linked page not in sitemap" (the page is intentionally noindex,nofollow and is linked sitewide as the Apply Now CTA; this is expected). Also expect: 40 sitemap pages, robots.txt/llms.txt/manifest.json/favicon.ico all 200, unknown path 404, http://oxfordra.net and https://www.oxfordra.net each 301 to https://oxfordra.net/. KNOWN OPEN OBSERVATION (not a regression): http://www.oxfordra.net/ takes two hops via https://www.oxfordra.net/; ignore it unless it becomes a loop or a non-301.
REGRESSION = any HIGH, any MED, any LOW other than the known one, a sitemap page count that changed without explanation, a non-200 on the domain checks above, or a redirect that is not a 301. A changed page count is flagged as INFO for Gabriel, not as a defect.

STEP 4. Output.
- No regression: send nothing, write nothing, finish with a one-line summary in the session.
- Regression or tooling failure: send ONE email via the Outlook COM script (the SOLE send path; it is `_shared/send-via-outlook.ps1` under ~/.claude, and the sibling task ora-site-exposure-probe's SKILL.md at C:\Users\Owner\.claude\scheduled-tasks\ora-site-exposure-probe\SKILL.md shows the exact invocation). TO ggoldberg@oxfordra.net ONLY, no cc, never ze@. Subject: `[ORA] oxfordra.net SEO crawl: <N> regression(s) <run date>`. Body: the run date, the HIGH/MED/LOW counts, each regression as page + finding + evidence, then a QUESTIONS FOR GABRIEL section for any claim or content decision (never decide copy, markets or close-speed claims yourself). On exit 2 or 4 from the script, retry once, then flag loudly in the session output and do not halt. On exit 5 or 6 (or any code other than 2 or 4) do NOT retry: flag it loudly in the run summary and in the session output and the guard close-out, and never resend (exit 6 = send state unknown — the message MAY have gone out), per rules.md §2. Close the guard `fail` on exit 5, but on exit 6 close it `complete` with no `--email-sent-at` (never `fail`: a same-day re-fire would send the message again).
- Never fabricate figures. Report only what the crawler returned.

Do not run PageSpeed here (it needs PSI_API_KEY, which is not provisioned). Do not touch Netlify, GitHub or the site repo.