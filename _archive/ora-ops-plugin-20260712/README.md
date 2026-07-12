# ORA-Ops Plugin

Bundles Oxford Realty Advisors' daily-automation **logic** so it installs in one step and turns each
scheduled-task prompt into a **one-line slash command**. Each command is a thin pointer at the
authoritative on-disk `SKILL.md` (or audit) spec — no logic is copied or re-pasted, so recipients,
Notion IDs, the full python path, and Outlook send paths stay in exactly one place.

- **Plugin name:** `ora-ops`  ·  **Version:** 1.0.0
- **Author:** Gabriel Goldberg / Oxford Realty Advisors (ggoldberg@oxfordra.net)
- **Marketplace:** `ora-ops-marketplace` (local directory)

---

## What you get (5 commands + 1 bundled skill)

| Slash command | Points at (authoritative spec) | Recommended schedule (ET) |
|---|---|---|
| `/ora-ops:ora-am-brief` | `…\Documents\Claude\Scheduled\ora-am-brief\SKILL.md` | **Daily 06:10** |
| `/ora-ops:ora-deal-sourcing-scan` | `…\Documents\Claude\Scheduled\ora-deal-sourcing-scan\SKILL.md` | **Tue 07:20** |
| `/ora-ops:ora-pm-ledger` | `…\Documents\Claude\Scheduled\ora-pm-ledger\SKILL.md` | **Daily 18:00 (06:00 PM)** |
| `/ora-ops:ora-setup-audit` | `C:\Users\Owner\.claude\daily-setup-audit-prompt.md` + `…\maintenance\setup-self-audit.py` | **Daily 06:30** |
| `/ora-ops:ora-health-guard` | `…\Documents\Claude\Scheduled\ora-health-guard\SKILL.md` | **Daily 05:15** |

Plus a bundled skill `ora-setup-self-audit` (`/ora-ops:ora-setup-self-audit`) that mirrors the
daily self-optimization routine in full, for when you want the routine inline rather than the
on-disk pointer.

**De-conflicted times (no two fire in the same minute):**
`05:15 health` · `06:00 PM ledger` · `06:10 brief` · `06:30 audit` · `Tue 07:20 deal-scan`.

All five commands are `disable-model-invocation: true` — they are side-effecting (email, ledger,
file writes), so **only a human (you) or a scheduled task fires them**; Claude never auto-invokes them.

---

## Install (one step, local)

Inside Claude Code, from any project:

```
/plugin marketplace add C:/Users/Owner/.claude/ora-ops-plugin
/plugin install ora-ops@ora-ops-marketplace
```

Non-interactive CLI equivalents:

```
claude plugin marketplace add C:/Users/Owner/.claude/ora-ops-plugin
claude plugin install ora-ops@ora-ops-marketplace
```

Validate before installing (optional):

```
claude plugin validate C:/Users/Owner/.claude/ora-ops-plugin/plugins/ora-ops
```

> A relative source (`./plugins/ora-ops`) resolves correctly because the marketplace is added as a
> **local directory** (relative-path sources work for a local-dir or Git marketplace, not for a
> remote-URL marketplace). After editing any file here, refresh with `/plugin marketplace update`.
> If you bump a command's behavior, also bump `version` in `plugins/ora-ops/.claude-plugin/plugin.json`
> so installed copies pick up the change.

Once installed, `/ora-ops:ora-am-brief` (etc.) is available immediately for **interactive** runs.

---

## Scheduling — honest note (this is the load-bearing caveat)

**The plugin cannot create the schedules. Claude Desktop schedules are created once per task through
a confirming action; the plugin only makes each one a one-liner.** A plugin manifest has **no
schedule / cron / routine field** of any kind, so there is no way to bundle the 05:15 / 06:00 PM /
06:10 / 06:30 / Tue-07:20 cron inside this plugin.

There is **no supported plain-file seed** that carries the cron either: a Desktop scheduled task's
`SKILL.md` holds only `name`/`description` + the prompt body; the docs state verbatim that
*"Schedule, folder, model, and enabled state are not in this file."* The cron/enabled state lives in
an app-managed store. (Do **not** hand-edit the legacy `local-agent-mode-sessions` /
`claude-code-sessions` `__scheduled-tasks.json` registries — those are orphaned/dead and the app
ignores them.)

So you create each schedule **once**, two supported ways:

### Path A — GUI (simplest, fully manual)
Claude Desktop → **Scheduled tasks → New task** → for the **Prompt**, paste a single line:

```
/ora-ops:ora-am-brief
```

…then set the **Schedule** to the recommended ET time above and keep **Keep awake = ON**
(these run only while the PC is awake). Repeat for the other four, in this order to keep the times
de-conflicted: **brief → audit → deal-scan → ledger → health-guard**. Each task's prompt is now a
single slash command instead of a paragraph — that's the whole point of the plugin.

### Path B — programmatic seed via the `scheduled-tasks` MCP  ⚠️ UNTRUSTED — USE PATH A
> **Caveat (ORA diagnosis 2026-06-06):** the `scheduled-tasks` MCP on this machine reads/writes the
> **emptied CCS registry** and returns 0 **by design** — it is the same split-brain that left the old
> 29-task fleet orphaned and dark. A `create_scheduled_task` call here may appear to succeed yet **never
> surface in the Desktop panel and never fire.** Do NOT use Path B until it's been empirically proven:
> first call `list_scheduled_tasks` (read-only) and create ONE throwaway task, then confirm it actually
> appears in the Desktop Scheduled-tasks panel and fires. Until then, **Path A (GUI) is the only trusted route.**

If (and only if) Path B is proven, ask Claude to call `create_scheduled_task` once per task with the
slash-command line as the `prompt` and the cron in **local time** (the app evaluates cron in local time,
not UTC, and adds a small deterministic stagger). Suggested ET cron lines (adjust if your machine clock is not ET):

| Task | prompt | cron |
|---|---|---|
| Health Guard | `/ora-ops:ora-health-guard` | `15 5 * * *` |
| Setup Audit | `/ora-ops:ora-setup-audit` | `30 6 * * *` |
| Morning Brief | `/ora-ops:ora-am-brief` | `10 6 * * *` |
| Deal-Sourcing Scan | `/ora-ops:ora-deal-sourcing-scan` | `20 7 * * 2` |
| Evening Ledger | `/ora-ops:ora-pm-ledger` | `0 18 * * *` |

**Each `create_scheduled_task` call pops one approval dialog — that dialog is the confirmation step.**
So this is "programmatic with one click each," not zero-click. After the first run, verify that one
task's email actually lands before trusting the whole set (post the Composio key rotation).

> Either way, the schedule is created **once**. From then on, editing or re-running is a one-liner,
> and the routine logic stays in the single on-disk `SKILL.md` each command points at.

---

## Guardrails (restated in every command body)
- **Never** send email, move money, modify financial models (DSCR 1.25 / LTV 40 governor files),
  or touch oxfordra.net without explicit human action.
- **Outlook send path:** `send-via-outlook.ps1` PRIMARY → `mcp__composio-ora__OUTLOOK_SEND_EMAIL`
  fallback. Deal-Sourcing Scan sends via Composio per its skill.
- **Scheduled sessions call python via the FULL path** (`bare python` is not on PATH):
  `C:/Users/Owner/AppData/Local/Programs/Python/Python313/python.exe`.
- Setup-audit and health-guard **emit reports/proposals only** — they never write `settings.json`,
  `hooks/`, `CLAUDE.md`, memory files, or the scheduler registry; guardrail-protected fixes are
  listed as PROPOSED actions for Gabriel to approve.

---

## Layout

```
ora-ops-plugin/                         # marketplace root (the dir you `marketplace add`)
  .claude-plugin/
    marketplace.json                    # marketplace manifest: name + owner + plugins[]
  plugins/
    ora-ops/                            # plugin root
      .claude-plugin/
        plugin.json                     # plugin manifest: name "ora-ops", version 1.0.0
      commands/
        ora-am-brief.md                 # -> /ora-ops:ora-am-brief
        ora-deal-sourcing-scan.md       # -> /ora-ops:ora-deal-sourcing-scan
        ora-pm-ledger.md                # -> /ora-ops:ora-pm-ledger
        ora-setup-audit.md              # -> /ora-ops:ora-setup-audit
        ora-health-guard.md             # -> /ora-ops:ora-health-guard
      skills/
        ora-setup-self-audit/SKILL.md   # -> /ora-ops:ora-setup-self-audit (full inline routine)
  README.md
```
