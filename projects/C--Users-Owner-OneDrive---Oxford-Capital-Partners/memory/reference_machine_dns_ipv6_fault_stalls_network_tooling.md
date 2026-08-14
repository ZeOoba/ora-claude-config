---
name: reference-machine-dns-ipv6-fault-stalls-network-tooling
description: "LAPTOP-CSHSCBE6 has no IPv6 route but its only DNS server still returns AAAA — every fresh hostname costs ~5s, which is the real cause of \"wrangler stalls\", \"could not resolve host github.com\", and slow npm"
metadata: 
  node_type: memory
  type: reference
  originSessionId: 1212fe18-a05b-453a-b759-cc70bbebd233
  modified: 2026-08-09T14:58:13.731Z
---

**Diagnosed 2026-08-09** while root-causing ~13 consecutive mirror-deploy failures (2026-08-05 20:10 → 2026-08-09 08:51). Do not re-diagnose from scratch — and do not blame the tool that reports the timeout.

## The fault

LAPTOP-CSHSCBE6 is dual-stack but has **no working IPv6 route**, while its **only** DNS server (`10.254.1.1` on Wi-Fi, **no secondary**) still returns AAAA records. Node/curl default dual-stack resolution therefore pays a **~5s penalty per fresh hostname**, and under load fails outright.

Measured:

| Probe | Result |
| --- | --- |
| `curl https://api.cloudflare.com` (default) | `dns=5.11s` |
| `curl -4 https://api.cloudflare.com` | `dns=0.013s` |
| `curl -6 https://api.cloudflare.com` | immediate failure — no route |
| `Get-DnsClientServerAddress` | one server, `10.254.1.1`, no secondary |

Already-cached hostnames (`registry.npmjs.org`, `dash.cloudflare.com`) resolve instantly, so a quick spot-check can look healthy. **Test an uncached hostname.**

## Symptoms it explains

- `fatal: unable to access '…': Could not resolve host: github.com` on `git fetch`/`git push` — intermittent, retry usually works.
- `wrangler` / any Cloudflare CLI: `The request to Cloudflare's API timed out`, `errorType: ConnectionTimeout`.
- `npx <pkg>` hanging indefinitely on a cold cache — **npx has no timeout of its own**, so it hangs until an outer kill. This is what consumed the mirror deploy's 600s budget.
- Slow `npm install` generally.

## Diagnostic that settles it fast

`npx` leaves no trace when it stalls, so check whether the tool ever started: `~/.wrangler/logs/` had **no log at all** across all ~13 failed runs, and wrangler writes a log even for `--version`. **Tool wrote no log ⇒ the stall was upstream in package acquisition, not in the tool.** Generalize this — check for the tool's own log/artifact before assuming it ran.

## Workaround (in code)

`NODE_OPTIONS=--dns-result-order=ipv4first` — made an otherwise-identical failing deploy succeed on the first try. Applied to `scripts/deploy-mirror.ps1` in [PR #266](https://github.com/ZeOoba/oxford-command-center/pull/266), along with pinning wrangler as a devDependency so `npx` never re-fetches it. Becomes a harmless no-op if IPv6 is ever routed properly.

## The actual fix is a host network setting

Adding a secondary resolver and/or disabling IPv6 on the Wi-Fi adapter is a **system settings change** — surface it to Gabriel, never apply it autonomously. Worth checking whether `10.254.1.1` is a router or a VPN resolver before changing anything.

Related: [[reference-command-center-mirror-deploy-gap]], [[reference-mirror-deploy-0xc000013a-is-usually-benign]].
