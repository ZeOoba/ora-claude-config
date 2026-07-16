---
name: feedback-webfetch-markdown-false-negatives
description: "WebFetch's HTML-to-markdown conversion strips <head>/<script>, producing false \"missing title/meta/schema\" and miscounted-H1 findings — verify via raw curl/HTML before trusting such claims"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 16672292-6559-4a80-a71f-a94dacb155d8
---

When auditing a live page for title tags, meta descriptions, heading counts, or JSON-LD structured data, do not trust a plain WebFetch pass alone — its HTML-to-markdown conversion discards `<head>` and `<script>` content and can mis-parse image/heading markup on some pages. During the 2026-07-10 oxfordra.net SEO audit ([[project_oxfordra_seo_audit_2026-07]]), two haiku-tier sub-agents using WebFetch reported the homepage had zero JSON-LD, no title tag, no meta description, and 3 H1s. Three independent agents that fetched raw HTML (via curl or an equivalent direct-HTTP tool) — and a direct manual `curl | grep` re-check — confirmed the opposite: 1 title, 1 meta description, 1 H1, and a live `application/ld+json` block.

**Why:** WebFetch runs page content through markdown conversion + a summarizing pass before returning it, which is lossy for exactly the elements (head metadata, script tags, some image/alt markup) that on-page/technical SEO checks depend on. The failure is silent — it returns a confident "not found" rather than an error.
**How to apply:** For any technical/on-page/schema SEO check (title, meta, canonical, JSON-LD, heading structure, image alt), prefer `curl`/raw HTTP fetch over WebFetch, or explicitly cross-check a WebFetch "missing" finding against raw HTML before reporting it as fact. When dispatching parallel sub-agents for this kind of audit, brief cheaper/faster-model agents specifically to use a raw-fetch method rather than assuming WebFetch is sufficient — the false negative rate scales with using a fast model + the AI-summarizing fetch path together.
