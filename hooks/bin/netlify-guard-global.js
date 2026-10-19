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
 * (pinned to 26.2.0, matching website-canonical) and its global shims (netlify AND its
 * alias ntl; see maintenance/patch-global-netlify-shim.js) are patched to invoke THIS file
 * instead of the global install's own bin/run.js directly. Because npx prefers an existing
 * global install over a fresh download, this makes `npx netlify deploy --prod` (or a bare
 * `netlify`/`ntl` command, also resolved via PATH to the same global shims) go through
 * authorization from ANY directory on the machine, not just from inside a project with its
 * own local guard.
 * authorization from any directory that has NO project-local netlify install of its own.
 *
 * KNOWN RESIDUALS (not closed here; independent review 2026-10-18): (a) inside a project that
 * has its own node_modules/.bin, that LOCAL shim wins over this global one, so it is only as
 * strong as that project's own guard (website-canonical's patcher covers `netlify*` but not
 * `ntl*`, and its guard needs website-canonical PR #175's token-level parse); (b) invoking
 * <globalroot>/netlify-cli/bin/run.js directly, fresh-download runners (`npx -p`, `pnpm dlx`,
 * `bunx`), NODE_OPTIONS=--require injection, and direct REST calls with NETLIFY_AUTH_TOKEN
 * never reach this file; (c) CLI subcommands that change live state (`sites:delete`,
 * `env:set/unset/clone`, `blobs:set/delete`) are not gated, although their `netlify api`
 * equivalents are; (d) CLAUDE_CODE_SESSION_ID is self-asserted (see override_tokens.py).
 *
 * Same detection and authorization logic as the repo-local guard (deliberately duplicated
 * rather than shared as a Node module, since these are two independent entry points with
 * no natural single callable surface between a project-local script and a machine-wide
 * one) -- see that file for the detection-bug history this logic already incorporates.
 * The prod flag is parsed per argv token (2026-10-17, mirrors website-canonical PR #175):
 * the earlier substring `indexOf("--prod")` missed netlify-cli's documented short flag,
 * so `netlify deploy -p` reached production with no authorization check. `netlify api`
 * methods outside a read-only allowlist are treated as production for the same reason.
 *
 * The validator is run with a HARD-CODED interpreter (PYTHON_EXE) in isolated mode, never
 * `process.env.PYTHON` (2026-10-17): an env-var interpreter let any caller that could set
 * the session id also point the validator at `true`/`cmd.exe` and self-authorize.
 *
 * Delegates to the REAL global netlify-cli by resolving its absolute entry-point path via
 * `npm root -g` at runtime (robust against a future Node/npm relocation, unlike a
 * hardcoded path) -- never by re-invoking "netlify" on PATH or via npx, so there is no
 * risk of this wrapper recursing into itself.
 *
 * Environment hardening (2026-10-18, two independent reviews of the 3ef48e0 fix):
 *  - NODE_OPTIONS="--require evil.js" runs BEFORE this file and can replace
 *    child_process.execFileSync to forge an ALLOW. Node 24 has no `--no-node-options`
 *    flag (verified: "bad option"), so the node process cannot opt out; instead main()
 *    refuses (exit 5) on any NODE_OPTIONS naming a known code/config-loading flag (quotes
 *    stripped, as node does), NODE_PATH / NODE_REPL_EXTERNAL_MODULE / NODE_V8_COVERAGE /
 *    OPENSSL_CONF, and any node execArgv; on the prod path it refuses ANY non-empty
 *    NODE_OPTIONS. The flag list is a denylist of KNOWN vectors and is only a tripwire.
 *    The real control is the shims (maintenance/patch-global-netlify-shim.js), which clear
 *    NODE_OPTIONS and OPENSSL_CONF BEFORE node starts. Residual (unfixable in-process):
 *    anything node does before this file's first line -- `--snapshot-blob` replaces this
 *    file entirely, an OpenSSL provider DLL loads at init -- and a preload that deletes the
 *    variable are invisible here, and `node guard.js` run by hand bypasses the shims. An
 *    attacker who can do that can equally run netlify-cli's bin/run.js directly.
 *  - The validator runs `python -I -S` with an environment ALLOWLIST (mirrors the
 *    website-canonical repo-local guard, commit 492a928): the old single-key denylist
 *    missed future test seams, and a planted .pth/sitecustomize in per-user
 *    site-packages runs at startup even under -I unless -S is also given.
 *
 * NETLIFY_GUARD_DRY_RUN=1 performs the full check but does not exec the real netlify-cli
 * -- logs "DRY RUN: would run <cmd>" and exits 0 instead. Same safety valve as the
 * per-repo guard; use it for ANY testing of this file, with no exceptions.
 */

const path = require("path");
const { spawnSync, execFileSync } = require("child_process");

const CHECK_SCRIPT = "C:\\Users\\Owner\\.claude\\hooks\\lib\\check_website_deploy.py";
// Fixed absolute interpreter, the same one the hook dispatcher runs under. If Python is
// ever upgraded/moved this fails CLOSED (execFileSync throws ENOENT -> DENIED, exit 5):
// update this constant, do not reintroduce an env/PATH lookup.
const PYTHON_EXE = "C:\\Users\\Owner\\AppData\\Local\\Programs\\Python\\Python313\\python.exe";
const DRY_RUN = process.env.NETLIFY_GUARD_DRY_RUN === "1";

// Environment passed to the validator: an ALLOWLIST (case-insensitive; Windows env names
// are), values verbatim, everything else dropped. The validator reads test seams such as
// ORA_OVERRIDE_SESSIONS_DIR (override_tokens.py) that would let a caller point it at a
// forged token directory; the sessions-dir default is an absolute path, so nothing else
// is needed.
const VALIDATOR_ENV_ALLOWLIST = [
  "systemroot", "windir", "systemdrive", "path", "pathext", "comspec",
  "userprofile", "homedrive", "homepath", "home", "appdata", "localappdata",
  "temp", "tmp",
];

function validatorEnv() {
  const env = {};
  for (const key of Object.keys(process.env)) {
    if (VALIDATOR_ENV_ALLOWLIST.indexOf(key.toLowerCase()) !== -1) env[key] = process.env[key];
  }
  return env;
}

// Node startup hooks that execute caller-controlled code before this file's first line.
// OPENSSL_CONF can name a provider module that node loads natively at process init.
const PRELOAD_ENV_VARS = ["node_path", "node_repl_external_module", "node_v8_coverage", "openssl_conf"];
// Matched against NODE_OPTIONS with quotes stripped (node strips them itself, so
// `"--require" m.js` is still a preload). --watch is included because it respawns the
// child tree; the rest load code or config at startup.
const CODE_LOADING_FLAG = new RegExp(
  "(^|\\s)(-r|--require|--import|--loader|--experimental-loader|--inspect[\\w-]*|--env-file[\\w-]*" +
  "|--openssl-config|--snapshot-blob|--watch[\\w-]*|--experimental-config-file" +
  "|--experimental-default-config-file)(\\s|=|$)", "i");

function envValue(name) {
  for (const key of Object.keys(process.env)) {
    if (key.toLowerCase() === name) return process.env[key];
  }
  return "";
}

// A reason string when the process started with a preload/loader vector, else null.
// onProdPath additionally rejects any non-empty NODE_OPTIONS.
function preloadProblem(onProdPath) {
  for (const name of PRELOAD_ENV_VARS) {
    if (envValue(name)) return name.toUpperCase() + " is set";
  }
  const nodeOptions = envValue("node_options");
  // Normalise like node's parser: quotes and backslash escapes dropped, `_` == `-`.
  if (CODE_LOADING_FLAG.test(nodeOptions.replace(/["'\\]/g, "").replace(/_/g, "-"))) {
    return "NODE_OPTIONS loads code (" + nodeOptions + ")";
  }
  if (onProdPath && nodeOptions.trim()) return "NODE_OPTIONS is set (" + nodeOptions + ")";
  // The shims (maintenance/patch-global-netlify-shim.js) pass node no flags, so ANY
  // execArgv means someone invoked node directly with options.
  if (process.execArgv.length > 0) {
    return "node was started with flags (" + process.execArgv.join(" ") + ")";
  }
  return null;
}

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

// Short flags of `netlify deploy` that consume a value (-d dir, -f functions, -b branch,
// -m message, -s site). In a bundle like `-sfoo` everything after one of these is that
// flag's value, not more flags, so a "p" inside it (a site named "app") is not `-p`.
const VALUE_SHORT_FLAGS = "dfbms";
// `netlify api <method>`: an ALLOWLIST of read-only methods. Every other method (restore,
// rollback, disableSite, deleteSite, updateSite, split tests, DNS, env vars, snippets,
// commits ...) can change the live site, so it goes through the authorization check.
const READ_ONLY_API_METHOD = /^(get|list|show|search)[a-z0-9]*$/i;

// Token-by-token argv parse. Long forms: --prod, --prod=true, --prod-if-unlocked and
// anything else starting with --prod; --trigger is included because it starts a build of
// the live site on Netlify without uploading local files.
function hasProdFlag(args) {
  for (const arg of args) {
    const lowered = arg.toLowerCase();
    if (lowered.indexOf("--prod") === 0 || lowered === "--trigger" || lowered.indexOf("--trigger=") === 0) {
      return true;
    }
    // Short flags: commander lets boolean shorts bundle (`-ap`, `-Op`) and accepts
    // `-p=true`. Case-sensitive on purpose (`-P` is not a flag), walked left to right.
    if (/^-[^-]/.test(arg)) {
      for (const ch of arg.slice(1)) {
        if (ch === "p") return true;
        if (ch === "=" || VALUE_SHORT_FLAGS.indexOf(ch) !== -1) break;
      }
    }
  }
  return false;
}

function isProdInvocation(args) {
  // Substring match on the JOINED, lowercased argv for "deploy": broad match, false
  // positive costs a retry, false negative deploys unauthorized to the live site.
  const isDeploy = args.join(" ").toLowerCase().indexOf("deploy") !== -1;
  if (isDeploy && hasProdFlag(args)) return true;
  // `netlify api restoreSiteDeploy` and friends reach production with no `deploy --prod`.
  // Candidates are the identifier-shaped non-flag tokens after `api` (JSON --data values
  // never look like identifiers); any candidate that is not a read-only method is prod.
  const apiAt = args.findIndex((a) => a.toLowerCase() === "api");
  if (apiAt !== -1) {
    return args
      .slice(apiAt + 1)
      .some((a) => /^[a-z][a-z0-9]*$/i.test(a) && !READ_ONLY_API_METHOD.test(a));
  }
  return false;
}

function main() {
  const args = process.argv.slice(2);

  // A preload can rewrite argv or child_process before this point, so a code-loading
  // vector is refused on EVERY invocation, not only the prod path.
  let problem = preloadProblem(false);
  if (problem) {
    log("DENIED: " + problem + " -- a preload could forge the authorization check; unset it and retry");
    process.exit(5);
  }

  if (!isProdInvocation(args)) {
    runRealCli(args);
    return;
  }

  problem = preloadProblem(true);
  if (problem) {
    log("DENIED for prod deploy: " + problem + " -- unset it and retry");
    process.exit(5);
  }

  const sessionId = process.env.CLAUDE_CODE_SESSION_ID;
  if (!sessionId) {
    log("prod deploy attempted but no CLAUDE_CODE_SESSION_ID in environment -- " +
        "no override reachable, refusing to deploy");
    process.exit(5);
  }

  try {
    // -I (isolated): ignores PYTHON* env vars and the script directory / user site.
    // -S: no site module, so a planted sitecustomize/.pth in user-writable site-packages
    // cannot run inside the validator. Env is an ALLOWLIST (see validatorEnv).
    const output = execFileSync(PYTHON_EXE, ["-I", "-S", CHECK_SCRIPT, "--session", sessionId],
      { encoding: "utf8", env: validatorEnv() });
    // -I (isolated): ignores PYTHON* env vars (PYTHONPATH/PYTHONSTARTUP/...) and the
    // script directory / user site, so the validator cannot be redirected by environment.
    // ORA_OVERRIDE_SESSIONS_DIR is a test seam in override_tokens.py: drop it so a caller
    // cannot point the validator at a self-minted token directory.
    // Windows env names are case-insensitive, so match the key case-insensitively.
    const validatorEnv = {};
    for (const k of Object.keys(process.env)) {
      if (k.toUpperCase() !== "ORA_OVERRIDE_SESSIONS_DIR") validatorEnv[k] = process.env[k];
    }
    const output = execFileSync(PYTHON_EXE, ["-I", CHECK_SCRIPT, "--session", sessionId],
      { encoding: "utf8", env: validatorEnv });
    log("authorized prod deploy for session " + sessionId + " -- " + output.trim());
  } catch (err) {
    const detail = (err.stderr && err.stderr.toString().trim()) || err.message;
    log("DENIED for prod deploy (session " + sessionId + ") -- " + detail);
    process.exit(5);
  }

  runRealCli(args);
}

if (require.main === module) {
  main();
} else {
  module.exports = { isProdInvocation, preloadProblem, validatorEnv };
  module.exports = { isProdInvocation };
}
