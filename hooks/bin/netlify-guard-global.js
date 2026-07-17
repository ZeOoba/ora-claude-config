#!/usr/bin/env node
"use strict";

/**
 * MACHINE-WIDE outbound-action check for Hard Invariant 2 (OI-007 follow-up, 2026-07-17).
 *
 * website-canonical/scripts/netlify-guard.js closes the value-indirection gap for the
 * netlify CLI *inside that repo* (its postinstall hook patches the repo-local
 * node_modules/.bin/netlify* shims). But `npx netlify ...` run from OUTSIDE any project
 * that has its own local install does NOT go through that repo-local guard at all --
 * npx's own resolution order is: (1) a local project's node_modules/.bin, (2) an already-
 * installed GLOBAL package, (3) fetch-and-run a fresh, unguarded copy from the npm
 * registry. A local guarded install (like website-canonical's) ALWAYS wins over a global
 * one in that order, so there is no double-check risk between this file and the per-repo
 * guard -- this file is only ever reached when no local guarded install exists.
 *
 * This script closes that residual gap: netlify-cli is deliberately installed globally
 * (pinned to 26.2.0, matching website-canonical) and its global shims are patched (see
 * maintenance/patch-global-netlify-shim.js) to invoke THIS file instead of the global
 * install's own bin/run.js directly. Because npx prefers an existing global install over
 * a fresh download, this makes `npx netlify deploy --prod` (or a bare `netlify` command,
 * also resolved via PATH to the same global shims) go through authorization from ANY
 * directory on the machine, not just from inside a project with its own local guard.
 *
 * Same detection and authorization logic as the repo-local guard (deliberately duplicated
 * rather than shared as a Node module, since these are two independent entry points with
 * no natural single callable surface between a project-local script and a machine-wide
 * one) -- see that file for the detection-bug history this logic already incorporates
 * (substring match on joined/lowercased argv, not an exact-array check, closing the
 * `--prod=true` / `--prod-if-unlocked` bypass found by adversarial review).
 *
 * Delegates to the REAL global netlify-cli by resolving its absolute entry-point path via
 * `npm root -g` at runtime (robust against a future Node/npm relocation, unlike a
 * hardcoded path) -- never by re-invoking "netlify" on PATH or via npx, so there is no
 * risk of this wrapper recursing into itself.
 *
 * NETLIFY_GUARD_DRY_RUN=1 performs the full check but does not exec the real netlify-cli
 * -- logs "DRY RUN: would run <cmd>" and exits 0 instead. Same safety valve as the
 * per-repo guard; use it for ANY testing of this file, with no exceptions.
 */

const path = require("path");
const { spawnSync, execFileSync } = require("child_process");

const CHECK_SCRIPT = "C:\\Users\\Owner\\.claude\\hooks\\lib\\check_website_deploy.py";
const DRY_RUN = process.env.NETLIFY_GUARD_DRY_RUN === "1";

function log(message) {
  process.stderr.write("[netlify-guard-global] " + message + "\n");
}

function npmCliPath() {
  // Invoke npm-cli.js directly via node.exe, NOT `execFileSync("npm", ...)`: on Windows,
  // npm itself is a .cmd shim, and execFileSync/spawnSync without shell:true cannot
  // resolve PATHEXT-based .cmd lookup (fails ENOENT). The alternative, `{ shell: true }`,
  // works but trips Node's own DEP0190 warning about unescaped shell arguments -- avoided
  // here entirely by locating npm's real entry-point script (a plain Node file, no shell
  // involved) relative to the currently-running node.exe, which sits in the same
  // directory tree as npm's own installation on every standard Node distribution.
  return path.join(path.dirname(process.execPath), "node_modules", "npm", "bin", "npm-cli.js");
}

function resolveRealCliEntry() {
  // Resolved at runtime, not hardcoded: robust against a future Node/npm relocation, and
  // this file has no fixed relative position to node_modules the way a project-local
  // node_modules/.bin/netlify.cmd shim does.
  const globalRoot = execFileSync(process.execPath, [npmCliPath(), "root", "-g"],
    { encoding: "utf8" }).trim();
  return path.join(globalRoot, "netlify-cli", "bin", "run.js");
}

function runRealCli(args) {
  if (DRY_RUN) {
    log("DRY RUN: would run `netlify " + args.join(" ") + "` (no real CLI invoked)");
    process.exit(0);
  }
  let realEntry;
  try {
    realEntry = resolveRealCliEntry();
  } catch (e) {
    log("FATAL: could not resolve the global netlify-cli entry point (" + e.message + ") -- " +
        "refusing to run anything rather than guessing a path.");
    process.exit(1);
  }
  // spawnSync (a genuinely separate process), not require(): netlify-cli's run.js expects
  // to be the entry-point module, so requiring it in-process would not behave like a real
  // invocation (same reasoning as the per-repo guard).
  const result = spawnSync(process.execPath, [realEntry].concat(args), { stdio: "inherit" });
  process.exit(result.status === null ? 1 : result.status);
}

function main() {
  const args = process.argv.slice(2);
  const argsJoined = args.join(" ").toLowerCase();
  const isDeploy = argsJoined.indexOf("deploy") !== -1;
  const isProd = argsJoined.indexOf("--prod") !== -1;

  if (!(isDeploy && isProd)) {
    runRealCli(args);
    return;
  }

  const sessionId = process.env.CLAUDE_CODE_SESSION_ID;
  if (!sessionId) {
    log("prod deploy attempted but no CLAUDE_CODE_SESSION_ID in environment -- " +
        "no override reachable, refusing to deploy");
    process.exit(5);
  }

  try {
    const output = execFileSync(process.env.PYTHON || "python",
      [CHECK_SCRIPT, "--session", sessionId],
      { encoding: "utf8" });
    log("authorized prod deploy for session " + sessionId + " -- " + output.trim());
  } catch (err) {
    const detail = (err.stderr && err.stderr.toString().trim()) || err.message;
    log("DENIED for prod deploy (session " + sessionId + ") -- " + detail);
    process.exit(5);
  }

  runRealCli(args);
}

main();
