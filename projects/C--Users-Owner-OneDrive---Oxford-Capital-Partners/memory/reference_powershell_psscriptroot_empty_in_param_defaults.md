---
name: reference-powershell-psscriptroot-empty-in-param-defaults
description: "$PSScriptRoot is EMPTY inside a PowerShell param-block default under `powershell -File` (populated in the body, and populated everywhere under `-Command`) — never resolve script-relative paths in a param default"
metadata: 
  node_type: memory
  type: reference
  originSessionId: 33e74279-bdb0-499e-888c-3d8b85d96d2b
  modified: 2026-08-04T15:45:34.310Z
---

In PowerShell (5.1), a `param()` block's **default expressions are evaluated before `$PSScriptRoot` is populated in the script scope** when the script is launched with `powershell -File`. So this dies on every `-File` launch:

```powershell
param([string]$RepoRoot = (Split-Path -Parent $PSScriptRoot))
# Split-Path : Cannot bind argument to parameter 'Path' because it is an empty string.
```

Measured across invocation modes (probe, 2026-08-04):

| Invocation | `$PSScriptRoot` at param default | in body |
| --- | --- | --- |
| `-File`, forward slashes | **empty** | populated |
| `-File`, backslashes | **empty** | populated |
| `-Command &` | populated | populated |

**Slash direction is irrelevant** — that was my first (wrong) diagnosis, and backslash `-File` fails identically. The discriminator is `-File` vs `-Command`.

**Why this is a nasty one:** the bug hides behind two coincidences. (1) Under `-Command &` the same expression works, so testing by hand in a PowerShell console passes. (2) Passing the parameter explicitly makes the whole script work, which makes it read as an *environment quirk rather than a script defect* — because every BODY-level `$PSScriptRoot` use (dot-sourcing a lib, `Split-Path -Parent $PSScriptRoot`) is fine. I recorded exactly that wrong conclusion in a Notion ops row before a `/debug` pass overturned it.

**How to apply:** resolve script-relative paths in the **body**, never in a param default:

```powershell
param([string]$RepoRoot)
if (-not $RepoRoot) { $RepoRoot = Split-Path -Parent $PSScriptRoot }
```

A typed `[string]` param left unbound is `''`, so `-not $RepoRoot` fires correctly. Keeps explicit override working; still throws loudly (rather than silently targeting the wrong directory) if `$PSScriptRoot` were ever empty in the body too. This is the idiom `oxford-command-center`'s `lib/deploy-beacon.ps1` `Get-DeployBeaconPath` already used.

**Testing gotcha:** a regression test for this must **shell out via `-File`** — dot-sourcing the script evaluates its param block in a context where `$PSScriptRoot` IS set, so the test passes against the very bug it guards. Invocation mode is the thing under test. Related: `$null -notmatch 'x'` returns an empty `Object[]`, not `$true` (PowerShell applies collection-filtering to `$null`), which breaks `[bool]` assertion helpers in precisely the clean/empty case — cast to `[string]` first.

Found 2026-08-04 in `oxford-command-center/scripts/mirror-run-classify.ps1`, which the `ora-command-center-mirror-drift-check` task invokes via `-File`; broken from PR #249 (2026-08-03) until PR #256. Distinct mechanism from [[feedback_bash_unquoted_windows_paths_collapse]] (that one is Bash word-escaping destroying the path before PowerShell ever sees it — both were hit in the same session and look similar at the terminal).
