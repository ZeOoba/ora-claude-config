---
name: reference_claude_md_wc_w_locale_undercounts
description: "Plain `wc -w` in this shell undercounts ANY heavily-Unicode-punctuated file (em-dashes, middle dots, arrows) by a locale/UTF-8 bug — not just CLAUDE.md, ~140 words on CLAUDE.md specifically. Never eyeball a word-count gate with a bare `wc -w`; use `LC_ALL=en_US.UTF-8 wc -w` or Python's `.split()`"
metadata: 
  node_type: memory
  type: reference
  originSessionId: f91bfd95-26da-4fd2-9c5a-275814c22796
  modified: 2026-08-13T20:11:26.885Z
---

Three word-count readings of CLAUDE.md disagreed within one session on 2026-08-13 (1587 / 1623 / 1725, then 1623 / 1762 on a re-check) — traced to root cause, not a real 08-11→08-13 size swing.

**Root cause:** this shell's active locale (`LANG` empty, `LC_CTYPE=C.UTF-8`) makes bare `wc -w` misclassify the em-dashes (—), middle dots (·), and arrows (→) CLAUDE.md is dense with, undercounting by ~138–140 words on a ~1,700-word file. Confirmed directly: `wc -w CLAUDE.md` → 1623; `LC_ALL=en_US.UTF-8 wc -w CLAUDE.md` → 1762; `python -c "print(len(open('CLAUDE.md',encoding='utf-8').read().split()))"` → 1762 — same content, same moment, two of three methods agree exactly and one is wrong. `doctrine-integrity-probe.py` (`maintenance/doctrine-integrity-probe.py:510`, `words = len(text.split())`) uses the correct method — it IS the authoritative gate, and it agrees with the UTF-8-locale `wc -w` and with Python `.split()`, not with a bare `wc -w`.

**Why:** nobody was lying or measuring at different times — `wc -w`'s word-boundary classification is locale-dependent, and this shell's effective locale mishandles this specific file's heavy non-ASCII punctuation. A file with fewer em-dashes/middle-dots would show a much smaller gap, which is why this wasn't caught earlier.

**How to apply:** never trust a bare `wc -w CLAUDE.md` reading against the WARN 1700 / FAIL 1850 gate — it reads LOW, so it can falsely suggest headroom that doesn't exist. Use `python maintenance/doctrine-integrity-probe.py` (the actual gate) or, for a quick manual check, `LC_ALL=en_US.UTF-8 wc -w CLAUDE.md`. This likely generalizes to any heavily-Unicode-punctuated file measured with a bare `wc -w` in this environment, not just CLAUDE.md. See [[reference_claude_md_word_budget_is_a_floor]] for what the numbers mean once correctly measured.
