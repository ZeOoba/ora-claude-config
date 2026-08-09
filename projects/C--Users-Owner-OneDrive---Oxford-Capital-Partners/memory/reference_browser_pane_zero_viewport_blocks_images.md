---
name: reference-browser-pane-zero-viewport-blocks-images
description: "A fresh Browser pane reports a 0x0 viewport and decodes NO images — resize_window with explicit width/height FIRST or every screenshot/photo read silently returns empty; agents misreport this as 'screenshots are impossible'"
metadata: 
  node_type: memory
  type: reference
  originSessionId: 3bd1fb25-7611-474e-9b42-0f4de4adcc9b
  modified: 2026-08-04T16:06:28.032Z
---

# A fresh Browser pane is 0x0 — resize before believing "no images"

**Found 2026-08-04** during `ora-deal-sourcing-scan`, while fixing a scan-wide gap where
all nine market subagents reported construction type as unverifiable.

## The failure

A newly opened Browser pane (`preview_start`) reports `window.innerWidth/innerHeight`
as **0x0**. In that state:
- `read_page` returns `(empty page)` with `Viewport: 0x0`
- image `naturalWidth`/`naturalHeight` are all `0` — nothing decodes
- screenshot/compositing fails

Agents reliably misread this as a hard capability limit and report *"the browser tool
could not render/screenshot"* or *"no tool here can view listing photos."* On the
2026-08-04 run, **9 of 9** independent subagents concluded photo inspection was
impossible. It was not — the pane simply had no size.

**Fix:** call `resize_window` with **explicit width/height** (`{width:1280, height:900}`)
before doing anything visual. Note the `preset:"desktop"` form reported success but left
the viewport at 0x0 in this session — explicit dimensions worked. Verify with
`javascript_tool` (`window.innerWidth`) rather than trusting the resize's return value.

**How to apply:** when any agent reports that images/screenshots are impossible in the
Browser pane, do not accept it — check the viewport first. This is also a reminder that
a *unanimous* subagent conclusion is not evidence: all nine shared the same wrong
instruction and the same unresized pane. See [[feedback_verify_before_repeating_session_claims]].

## Reading page images without screenshots at all

Often better than screenshotting: extract image URLs from the DOM, download, and `Read`
the file (Read renders images).

```
javascript_tool: document.querySelectorAll('<gallery selector> img') -> src (strip ?query)
curl -sL -o out.jpg "<full url>?width=1400"     # many CDNs accept a width param
Read out.jpg
```

Two traps that yield a **confidently wrong** answer, both hit live:
1. **Attribution.** Listing sites embed "similar/nearby property" carousels
   (`.similarproperty`, `.carousel.listings`) whose photos are *other buildings*. On one
   page every image belonged to the carousel and the most prominent one was a different
   property entirely. Scope the selector to the subject gallery and **check the `alt`
   attribute** — it carries the subject address or listing title. If alt doesn't match,
   discard.
2. **CDNs key on a GUID, not the filename.** `…/images/<GUID>/<name>.jpeg` — reusing one
   GUID with different filenames returns the SAME image (four "different" downloads came
   back byte-identical by md5). Never construct these URLs; take each full href from the DOM.

Domain procedure for classifying industrial construction from photos lives in
`ora-deal-sourcing-scan` SKILL.md Step 1 (v2.4) — procedures belong in skills, not here.

Related: [[reference_tech]] · [[feedback_absence_claims_need_verification_before_building]]
