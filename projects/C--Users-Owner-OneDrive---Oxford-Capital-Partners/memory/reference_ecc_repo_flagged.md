---
name: reference_ecc_repo_flagged
description: affaan-m/ECC (github.com/affaan-m/ECC) evaluated and rejected for install — viral single-maintainer cross-harness agent framework with a documented malware-clone risk in the wild.
metadata: 
  node_type: memory
  type: reference
  originSessionId: c4e72b89-264e-4eea-84b8-4f38b2f0c461
---

**affaan-m/ECC — do not install.** Evaluated 2026-07-10 as part of a batch of 10 GitHub repos Gabriel asked about.

**Why:** Repo self-reports ~220K+ stars (independently verified via GitHub API + star-history.com, global rank #19) for a 6-month-old (created 2026-01-18) single-maintainer project claiming skills/hooks/agents across 7 AI-coding harnesses (Claude Code, Codex, Cursor, OpenCode, etc.). A third-party security audit ([dev.to/joergmichno](https://dev.to/joergmichno/we-audited-the-viral-213k-star-everything-claude-code-repo-and-found-a-malware-clone-in-the-wild-14hb)) found the repo's virality has spawned malicious re-uploads — an obfuscated LuaJIT malware dropper disguised as a "download toolkit." The original repo isn't itself malware, but its own README now carries an "official sources only" warning banner. Functionally it's also fully redundant with the existing [[procurement-stance-deepen-not-migrate]] doctrine — everything it claims (skills, hooks, subagents) is already covered by superpowers + ora-skills, purpose-built and governed by ORA's own CLAUDE.md.

**How to apply:** If ECC (or "the everything Claude Code repo" / similar viral cross-harness framework repos) resurfaces in a tooling sweep or a direct ask, don't re-research from scratch — the answer is skip, and the reasoning is (1) disproportionate auto-executing surface from an unaudited solo-maintainer project on a machine holding confidential deal data, (2) documented malware-clone risk in its ecosystem, (3) full redundancy with the existing skill stack. Also a live example of the general pattern: inflated/self-reported repo stats in a WebFetch summary should be cross-checked against the GitHub API and independent trackers before acting on them, especially when the page's framing seems tuned to exactly the kind of "should I install this" evaluation being run.
