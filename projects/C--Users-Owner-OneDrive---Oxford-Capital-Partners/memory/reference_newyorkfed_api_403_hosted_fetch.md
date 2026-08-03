---
name: reference-newyorkfed-api-403-hosted-fetch
description: NY Fed markets.newyorkfed.org API (SOFR + SOFR Averages/Index) returns HTTP 403 to Anthropic-hosted fetch tooling; local Desktop Commander direct pull works fine
metadata: 
  node_type: memory
  type: reference
  originSessionId: 4a7a2556-047a-401e-873f-49ef75635cfc
  modified: 2026-07-29T14:22:04.468Z
---

`markets.newyorkfed.org/api/rates/secured/sofr/...` and `/sofrai/...` (SOFR overnight print + 30/90/180-day averages + SOFR Index) return **HTTP 403 Forbidden** to WebFetch and to Cowork's hosted fetch tooling — confirmed via direct WebFetch test 2026-07-15. This is an infrastructure-level block (Anthropic-hosted egress IP range), not a bad URL or auth issue.

A direct call from the actual local machine (verified via Desktop Commander `start_process` → `Invoke-RestMethod` on LAPTOP-CSHSCBE6) succeeds cleanly with no auth needed — plain public JSON.

**Downstream impact:** `ora-am-brief` Block A (the current live producer of the Notion "Rate Snapshot — Current" page, `35e6ecd8-9e59-814f-ae22-fe99464084d1`) fetches this data as a Cowork/LAMS scheduled task, which runs in the same hosted-fetch environment — so it hits the same 403. Overnight SOFR and UST yields have a web_search fallback (secondary sources cite the print), so they usually still populate (sometimes 1 day stale). **30/90/180-day SOFR averages and the SOFR Index have no reliable web_search fallback** — nobody headline-publishes those numbers — so they silently go `[CARRIED FORWARD — not refreshed this run]` run after run until someone notices. Caught 2026-07-15 after 2 consecutive stale runs.

**Why:** the Cowork sandbox's outbound fetch shares Anthropic's hosted egress, which NY Fed blocks; only a session with real local-machine network access (Code surface + Desktop Commander) bypasses it.

**How to apply:** if the Rate Snapshot page (or any consumer reading SOFR averages/Index) shows a `[CARRIED FORWARD]` or `[STALE]` flag on the SOFR strip, don't just re-run the automated task — it will hit the same 403. Instead, from a Code-surface session on the actual machine, run a Desktop Commander `Invoke-RestMethod` against `markets.newyorkfed.org/api/rates/secured/sofr/last/5.json` (overnight) and `/sofrai/last/1.json` (30/90/180-day avg + index), then patch the Notion page directly via `notion-update-page` `update_content` (targeted old_str/new_str per row, not a full-page `replace_content`) — label it clearly as a manual supplemental patch with the date, don't silently overwrite `fetched_at`/`prefetch_status` as if the whole automated run refreshed. This is a workaround, not a permanent fix — the underlying `ora-am-brief` Block A prefetch will hit the same 403 next scheduled run. A durable fix would need either the Cowork sandbox to gain direct network egress, or the SOFR-averages step to be rerouted through a machine-local task, neither of which exists yet.

**The local pull needs an explicit TLS 1.2 opt-in (added 2026-07-29).** The bare `Invoke-RestMethod` command as written in `ora-sofr-direct-prefetch`'s SKILL.md STEP 1 **fails on LAPTOP-CSHSCBE6** with `The underlying connection was closed: Could not establish trust relationship for the SSL/TLS secure channel` (and, on the second endpoint, the variant `An unexpected error occurred on a send`). Cause: Windows PowerShell 5.1 negotiates its default `ServicePointManager.SecurityProtocol`, which `markets.newyorkfed.org` rejects. Prefix fixes it, first attempt, both endpoints:

```powershell
powershell.exe -NoProfile -Command "[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; (Invoke-RestMethod -Uri '<url>' -UseBasicParsing) | ConvertTo-Json -Depth 6"
```

Two traps this sets. First, the error is a *transport* failure, not a 403 — so it does **not** look like the hosted-fetch problem this whole workaround exists for, and reads as "NY Fed is down." It isn't. Second, the SKILL.md's failure path sends an unretried-or-still-failing fetch straight to a STEP 5 Ops Hub alert, so a task following the file literally would post a **false** "NY Fed unreachable" every weekday while the data was actually reachable the whole time. Any local NY Fed pull — this task, `ora-am-brief` Block A if it ever moves machine-local, or an ad-hoc patch per the paragraph above — should carry the TLS 1.2 prefix. Note PowerShell 7+ (`pwsh`) defaults to TLS 1.2+ and does not need it; the trap is specific to `powershell.exe` 5.1.

See also [WebFetch Markdown False Negatives](feedback_webfetch_markdown_false_negatives.md) for a related but distinct WebFetch gotcha (HTML→markdown stripping, not a 403 block).
