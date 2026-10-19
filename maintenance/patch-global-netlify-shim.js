#!/usr/bin/env node
"use strict";

/**
 * Patches the GLOBAL npm install of netlify-cli's shims to route through
 * hooks/bin/netlify-guard-global.js (OI-007 follow-up, 2026-07-17 -- see that file's
 * docstring for the full rationale: this closes the residual gap where `npx netlify` or
 * a bare `netlify` command, run from OUTSIDE any project with its own local guarded
 * install, would otherwise reach an unguarded copy).
 *
 * RUN THIS MANUALLY -- there is no automatic re-trigger:
 *   node maintenance/patch-global-netlify-shim.js
 *
 * WHY MANUAL, RATIFIED 2026-07-17: unlike a project's own package.json (which gets a
 * postinstall hook re-run on every `npm install`), there is no equivalent lifecycle hook
 * for a GLOBAL npm package -- nothing automatically re-applies this patch if netlify-cli
 * is ever reinstalled or updated globally (`npm install -g netlify-cli` /
 * `npm update -g netlify-cli`). Gabriel ratified accepting that as a documented manual
 * step (re-run this script after any such operation) over adding a scheduled health-check
 * for a gap already flagged low-priority -- see
 * memory/project_autonomy_gate_indirection_ceiling_followup.md.
 *
 * Layout note: Windows' GLOBAL npm bin shims sit DIRECTLY in the npm prefix directory
 * (alongside node_modules/, not inside a nested bin/ or .bin/ subfolder) -- structurally
 * different from a project-local install's node_modules/.bin/, so this cannot reuse
 * website-canonical/scripts/patch-netlify-shim.js's relative-path assumptions verbatim.
 *
 * Same fail-loud philosophy as the per-repo patcher: if the global netlify-cli isn't
 * installed, or a shim can't be written, this exits non-zero rather than silently leaving
 * the global install unguarded with no visible signal.
 */

const fs = require("fs");
const path = require("path");
const { execFileSync } = require("child_process");

const GUARD_PATH = path.join(__dirname, "..", "hooks", "bin", "netlify-guard-global.js");

function npmCliPath() {
  // Invoke npm-cli.js directly via node.exe, NOT `execFileSync("npm", ...)`: on Windows,
  // npm itself is a .cmd shim, and execFileSync/spawnSync without shell:true cannot
  // resolve PATHEXT-based .cmd lookup (fails ENOENT). `{ shell: true }` works but trips
  // Node's own DEP0190 warning about unescaped shell arguments -- avoided entirely by
  // locating npm's real entry-point script (a plain Node file) relative to the currently-
  // running node.exe, which sits in the same directory tree as npm on any standard
  // Node distribution.
  return path.join(path.dirname(process.execPath), "node_modules", "npm", "bin", "npm-cli.js");
}

function getPrefixDir() {
  return execFileSync(process.execPath, [npmCliPath(), "config", "get", "prefix"],
    { encoding: "utf8" }).trim();
}

// All three shim flavours clear NODE_OPTIONS and OPENSSL_CONF before node starts (2026-10-18
// review): node processes both before any JS, so the guard cannot see or stop them itself.
// Side effect: .cmd and .ps1 clear them in the calling shell session too (sh scopes it to
// the shim's own process); a legitimate NODE_OPTIONS for netlify must be set per-invocation elsewhere.
function shimContent(name, guardPathForShim) {
  name = name.replace(/^ntl/, "netlify"); // ntl is an alias of netlify: identical guard shim
  if (name === "netlify.cmd") {
    return `@ECHO off
GOTO start
:find_dp0
SET dp0=%~dp0
EXIT /b
:start
SETLOCAL
CALL :find_dp0

IF EXIST "%dp0%\\node.exe" (
  SET "_prog=%dp0%\\node.exe"
) ELSE (
  SET "_prog=node"
  SET PATHEXT=%PATHEXT:;.JS;=;%
)

endLocal & goto #_undefined_# 2>NUL || title %COMSPEC% & set "NODE_OPTIONS=" & set "OPENSSL_CONF=" & "%_prog%"  "${guardPathForShim}" %*
`;
  }
  if (name === "netlify") {
    return `#!/bin/sh
basedir=$(dirname "$(echo "$0" | sed -e 's,\\\\,/,g')")

case \`uname\` in
    *CYGWIN*|*MINGW*|*MSYS*)
        if command -v cygpath > /dev/null 2>&1; then
            basedir=\`cygpath -w "$basedir"\`
        fi
    ;;
esac

# Git Bash env names are case-sensitive but node.exe reads them case-insensitively, so
# unset every case variant (an \`env -u\` of the upper-case name alone leaves node_options).
# Shell builtins only, after dropping any exported function: a loop calling env/cut/grep can
# be defeated from the environment (BASH_FUNC_grep%%, GREP_OPTIONS=-v).
\\unset -f compgen 2>/dev/null
for v in $(compgen -e); do
  case "$v" in
    [Nn][Oo][Dd][Ee]_[Oo][Pp][Tt][Ii][Oo][Nn][Ss]|[Oo][Pp][Ee][Nn][Ss][Ss][Ll]_[Cc][Oo][Nn][Ff]) unset "$v";;
  esac
done

if [ -x "$basedir/node" ]; then
  exec "$basedir/node"  "${guardPathForShim}" "$@"
else
  exec node  "${guardPathForShim}" "$@"
fi
`;
  }
  if (name === "netlify.ps1") {
    return `#!/usr/bin/env pwsh
$basedir=Split-Path $MyInvocation.MyCommand.Definition -Parent
# Startup-time node vectors (--require, --snapshot-blob, OpenSSL provider modules) run before
# the guard's first line and cannot be detected from inside it: clear them here.
Remove-Item Env:NODE_OPTIONS, Env:OPENSSL_CONF -ErrorAction SilentlyContinue

$exe=""
if ($PSVersionTable.PSVersion -lt "6.0" -or $IsWindows) {
  $exe=".exe"
}
$ret=0
if (Test-Path "$basedir/node$exe") {
  if ($MyInvocation.ExpectingInput) {
    $input | & "$basedir/node$exe"  "${guardPathForShim}" $args
  } else {
    & "$basedir/node$exe"  "${guardPathForShim}" $args
  }
  $ret=$LASTEXITCODE
} else {
  if ($MyInvocation.ExpectingInput) {
    $input | & "node$exe"  "${guardPathForShim}" $args
  } else {
    & "node$exe"  "${guardPathForShim}" $args
  }
  $ret=$LASTEXITCODE
}
exit $ret
`;
  }
  throw new Error("unknown shim name: " + name);
}

function main() {
  if (!fs.existsSync(GUARD_PATH)) {
    console.error("[patch-global-netlify-shim] FATAL: guard script not found at " + GUARD_PATH +
      " -- refusing to patch shims to point at a file that doesn't exist.");
    process.exit(1);
  }

  let prefixDir;
  try {
    prefixDir = getPrefixDir();
  } catch (e) {
    console.error("[patch-global-netlify-shim] FATAL: could not determine npm's global prefix (" +
      e.message + ").");
    process.exit(1);
  }

  const names = ["netlify.cmd", "netlify", "netlify.ps1", "ntl.cmd", "ntl", "ntl.ps1"];
  const existing = names.filter((name) => fs.existsSync(path.join(prefixDir, name)));

  for (const name of names) {
    if (existing.indexOf(name) === -1) {
      console.warn("[patch-global-netlify-shim] " + name + " does not exist at " + prefixDir +
        " -- skipping (is netlify-cli actually installed globally? `npm install -g " +
        "netlify-cli@26.2.0` first)");
    }
  }
  if (existing.length === 0) {
    console.error("[patch-global-netlify-shim] FATAL: no netlify shim exists globally -- " +
      "netlify-cli is not installed globally, or its bin shims weren't generated. Nothing " +
      "to patch. Run `npm install -g netlify-cli@26.2.0` first.");
    process.exit(1);
  }

  let patchedCount = 0;
  for (const name of existing) {
    const target = path.join(prefixDir, name);
    try {
      fs.writeFileSync(target, shimContent(name, GUARD_PATH), { encoding: "utf8" });
      try { fs.chmodSync(target, 0o755); } catch (e) { /* best-effort on non-POSIX filesystems */ }
      console.log("[patch-global-netlify-shim] patched " + name + " -> " + GUARD_PATH);
      patchedCount++;
    } catch (e) {
      console.error("[patch-global-netlify-shim] could not patch " + name + ": " + e.message);
    }
  }

  if (patchedCount < existing.length) {
    console.error("[patch-global-netlify-shim] FATAL: " + (existing.length - patchedCount) +
      " of " + existing.length + " existing shim(s) failed to patch. The global netlify CLI " +
      "would be PARTIALLY unguarded.");
    process.exit(1);
  }
  console.log("[patch-global-netlify-shim] all " + patchedCount + " global shim(s) patched -- " +
    "the global netlify CLI is guarded. Re-run this script after any future " +
    "`npm install -g netlify-cli` / `npm update -g netlify-cli`.");
}

if (require.main === module) {
  main();
} else {
  module.exports = { shimContent }; // for hooks/tests/test-netlify-guard-global.py
  module.exports = { shimContent };
}
