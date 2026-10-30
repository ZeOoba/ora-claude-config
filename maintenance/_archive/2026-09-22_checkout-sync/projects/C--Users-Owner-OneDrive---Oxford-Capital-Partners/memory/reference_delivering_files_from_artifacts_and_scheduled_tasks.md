---
name: reference-delivering-files-from-artifacts-and-scheduled-tasks
description: "How a generated file reaches Gabriel. Found building the ORA Forward Calendar 2026-09-18/19: an artifact page cannot download via <a download>/blob (needs the downloads capability); .ics is NOT on that capability's extension allowlist (ship .ics.txt); scheduled tasks CAN attach files since PR #220 via send-via-outlook.ps1 -Attachment (internal-only, '|'-delimited for several)."
metadata:
  node_type: memory
  type: reference
---

Three independent limits govern how a generated file reaches Gabriel. All three were hit while building
the ORA Forward Calendar (2026-09-18/19); each failed in a way that looks like success. Limit 3 was
LIFTED the next day — kept here because its history is why the digest task was built the way it was.

**1. An artifact page cannot hand over a file by itself.** `<a download>`, `URL.createObjectURL`,
and `data:`/`blob:` hrefs are all inert in the claude.ai artifact viewer — the button renders, the
click does nothing, and there is NO console error. The publish step warns about this; the warning is
the only signal. The supported path is the `downloads` capability: declare `capabilities:
{downloads: true}`, `const d = await claude.use("downloads")` (may resolve `null` — hide the
affordance), then `await d.save({filename, data})`. The viewer sees a confirmation and may decline,
so handle `declined` / `rate_limited` / `too_large` and never auto-retry.

**2. `.ics` is NOT on the downloads extension allowlist.** The allowlist is
`gif png jpg jpeg webp mp4 webm txt json md` plus `docx pptx epub csv ttf html svg pdf xlsx zip` —
calendar files are absent, and a `.ics` filename rejects with `rejected_extension`. Workaround used:
ship it as `<name>.ics.txt` and tell the viewer to delete the trailing `.txt`. Do not build a
fallback chain to other formats; pick the one allowed name knowingly and say so in the UI.

**3. Scheduled tasks CAN now attach files — since ora-claude-config PR #220 (2026-09-19).**
`scheduled-tasks/_shared/send-via-outlook.ps1` gained `-Attachment`. Until then its signature was only
`-To -Subject -Body -BodyFile -BodyFormat -Cc` (no attachment path existed on the sole fleet send path).
Rules of the new parameter, all deliberate:
- **Several files travel as ONE `'|'`-delimited token.** Under `powershell -File` (how every fleet task
  calls it) a `[string[]]` parameter can never receive more than one element: `-Attachment a b` binds
  `a` plus a stray positional, and `-Attachment a,b` binds the literal string `"a,b"`.
- **Internal-only.** Any attachment plus any external recipient is refused (exit 5): the outbound check
  authorizes recipients and cannot see file CONTENT, and an attachment bypasses every content scan.
- **Fail-closed.** A missing file, a directory, an empty element or >20 MB total rejects the whole send
  with exit 1 and nothing is sent — a body that promises a file must never go out without it.
- Resolved absolute paths are logged on the `send-log.txt` OK line. Tests: `_shared/test-send-via-outlook.ps1`.

**Caveat — "merged" is not "live".** The fleet runs the working tree of the shared `~/.claude` checkout,
which lagged origin/main by ~179 commits, so PR #220 reached production only via a targeted single-file
swap (OI-326; method in [[reference_git_merge_blocks_on_identical_dirty_files_targeted_deploy]]). If a
task reports an unknown `-Attachment` parameter, the live script has regressed to the pre-PR version.

**How to apply.** Scheduled task → attach with `-Attachment` (internal recipients only), and still print the
file's absolute path in the body as a fallback. Published artifact page → use the `downloads` capability and
accept the allowlist. A file this session generates → `SendUserFile` has none of these limits and is the
simplest route; it delivered a real `.ics` the same day the in-page button could only manage `.ics.txt`.

Related: [[feedback_website_canonical_slug_blocks_scratchpad_and_memory]].
