---
name: graph-app-registration
description: Runbook for registering a new Azure AD (Entra) application and wiring Microsoft Graph API access for a new integration — app registration, client secret generation, application permissions (e.g. Mail.Send, Sites.Selected), admin consent, and the separate Graph Explorer site-permission grant (POST /sites/{siteId}/permissions) needed to give the app write access to one specific SharePoint site. Use when the user mentions: new Graph-backed integration, Azure AD app registration, Entra app registration, register an app in Azure, SharePoint site permission grant, Sites.Selected, Graph API access provisioning, wire up Microsoft Graph, or rotating/regenerating GRAPH_CLIENT_SECRET (24-month expiry — will recur ~2028). v1.0
license: ORA Internal
---

# Graph App Registration

Runbook for the two-part sequence any new Microsoft Graph-backed integration needs: (1) an Azure AD/Entra app registration with the right Graph permissions and admin consent, and (2) — a separate, easy-to-miss step — granting that app write access to one specific SharePoint site via Graph Explorer's `Sites.Selected` permission model, since site-level access is not covered by the app-registration consent flow alone. In practice these are always done together for a new integration; this skill bundles both rather than splitting them.

Originally extracted from the Azure AD + Netlify setup for the oxfordra.net website pipeline (Graph-backed tenant-application/broker-OM-upload intake, 2026-07). No skill previously covered this; the client secret's 24-month expiry means this exact sequence will need to run again around mid-2028, and the friction points below are non-obvious enough to be worth codifying now, while fresh, rather than rediscovering.

## Scope

Any new service/integration that needs to read or write Microsoft 365 data (mail, one SharePoint site, etc.) via Graph, where no existing app registration already covers the needed permission set.

## Triggers

"New Graph integration", "register an app in Azure AD/Entra", "need Graph API access to SharePoint", "Sites.Selected permission", "rotate the Graph client secret", "grant this app access to [SharePoint site]".

## Inputs

- The integration's required Graph scopes (e.g. `Mail.Send`, `Sites.Selected`, `Files.Read`) — least-privilege, not broad grants like `Sites.Read.All` unless a narrower scope proves insufficient.
- The target SharePoint site (if site-level access is needed) — its URL, to be resolved to both a SharePoint REST GUID and a Graph-format `siteId`/`driveId` (see step 4; these are NOT interchangeable).
- Where the resulting secrets will be consumed (e.g. Netlify env vars, a `.env` file) — see `deploy-site` skill for Netlify-side provisioning.

## Standard Workflows

### App Registration + Graph Permissions

1. **Create the app registration** in the Entra admin center (entra.microsoft.com → Applications → App registrations → New registration). Record the Application (client) ID and Directory (tenant) ID.
2. **Generate a client secret** (Certificates & secrets → New client secret). Azure reveals the plaintext value exactly once — capture it immediately into its final destination (a password manager or directly into the target env-var system per the Secret Handling section below), never into a screenshot or a scratch file. **Set expiry deliberately** (24 months has been the working default here, precisely because no secret-rotation automation exists yet) and note the expiry date in whatever tracks the integration, so its eventual rotation isn't a surprise.
3. **Add application permissions** (API permissions → Add a permission → Microsoft Graph → Application permissions): start with the narrowest scope that could plausibly work (e.g. `Files.Read` before `Sites.Read.All`) and escalate only on a confirmed 403, not preemptively. **Grant admin consent** — the permission has no effect until an admin explicitly consents, a step easy to miss since the UI doesn't always make its absence obvious.
4. **Grant site-level write access separately, via Graph Explorer** — application-permission consent alone does NOT grant `Sites.Selected` access to any specific site; that's a second, explicit call: `POST /sites/{siteId}/permissions` in Graph Explorer, with the app's client ID and the desired role (`write`/`read`) in the request body. To make this call you need the site's **Graph-format** `siteId` (and `driveId` if the integration needs drive access) — resolve these via `GET /sites/{hostname}:/{site-relative-path}` in Graph Explorer; do NOT reuse the SharePoint REST API's site GUID directly, the two ID encodings are not interchangeable and mixing them produces a 404 that looks like a permissions problem rather than an ID-format problem.
5. **Sign-in friction, expect it:** Graph Explorer's own sign-in popup is commonly blocked when triggered by browser automation — it requires a real, manual click each time a fresh Graph Explorer session starts. Flag this to whoever's driving rather than retrying automation against it.
6. **Verify** the site permission landed: re-run the resolving `GET` or attempt the integration's actual first write and confirm it succeeds (a 403 at this stage usually means either consent wasn't granted in step 3, or the site permission grant in step 4 targeted the wrong ID).

## Secret Handling

- Never let Claude type, view, or screenshot a client secret in plaintext once it's been generated — enter it directly into its destination (env var, password manager) per the Explicit Permission / Prohibited Actions rules for credentials.
- **Some Microsoft/Netlify UI surfaces do NOT mask secret fields the way env-var inputs do** — e.g. a webhook-signing-secret edit dialog may display its value in plaintext on open. Treat every credential-adjacent field as unmasked until proven otherwise; never screenshot or "reopen to verify" a field that might be.
- If a secret is exposed (screenshotted, logged, or otherwise handled incorrectly), the correct fix is regenerating it (`openssl rand -hex 32` for a self-issued secret, or Azure's regenerate flow for `GRAPH_CLIENT_SECRET`), not just noting the exposure — treat exposure as compromise.

## Outputs

- Recorded Application (client) ID, Directory (tenant) ID, and secret expiry date (not the secret value itself) in whatever doc/memory tracks the integration.
- Confirmed Graph permissions with admin consent granted.
- Confirmed `Sites.Selected` site-level grant (if applicable), verified against an actual successful call.

## Boundaries

- This skill provisions access; it does not build the integration consuming it (Netlify env-var wiring is `deploy-site`'s territory; the integration's own code is out of scope).
- Least-privilege by default — do not grant `Sites.Read.All`/broad tenant-wide scopes as a first move; escalate only on a confirmed, specific failure.
- No secret-rotation automation exists yet for `GRAPH_CLIENT_SECRET` — expiry is manual-tracked. If this skill fires again before the noted expiry, that's a signal a rotation reminder is overdue, not that this skill needs re-running early.

## Dependencies

- `deploy-site` skill (consumes the resulting credentials as Netlify env vars)
- Explicit-permission credential-handling rules (secret entry, never Claude-typed)

## Changelog

- v1.0 (2026-07-11): initial. Extracted from the Azure AD + Netlify website-pipeline setup session; surfaced by a workflow-audit pass mining recent transcripts for repeated-but-uncodified patterns. No prior skill covered Graph/Entra app registration or Sites.Selected site permission grants.
