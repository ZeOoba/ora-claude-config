---
name: feedback-nul-bytes-survive-the-gate
description: "NUL bytes written into a .ts source file pass typecheck, lint AND the full test suite — only `git diff` showing \"Bin\" catches them"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 70bd543c-295a-42b3-9560-0c3763b7f04e
  modified: 2026-07-25T00:06:34.988Z
---

While adding the business-key diff to `lease-snapshot-drift-check.ts` (2026-07-24), two spaces I intended as separators inside a template literal were written to disk as literal **NUL bytes** (`\x00`):

```
return `${normalize(lease.propertyKey)}\x00${normalize(lease.unit)}\x00${tenant}`;
```

**Why:** the string still decoded as valid UTF-8 (NUL is a legal code point), TypeScript accepted it inside a template literal, ESLint had no rule against it, and the 16 new unit tests passed — NUL works fine as a separator, so behavior was correct. `npm run typecheck` (0), `npm run lint` (0), and 3017/3017 tests were all green on a corrupt file.

**The only signal** was `git diff --stat` reporting `scripts/lease-snapshot-drift-check.ts | Bin 13501 -> 21977 bytes` — git had reclassified a TypeScript source file as **binary**. Had it been committed, the file would have been undiffable and unreviewable in the PR forever.

**Why:** every gate in the chain validates *semantics*, and NUL is semantically inert inside a string literal. Nothing in the gate validates *bytes*.

**How to apply:** after any programmatic write to a source file (Edit tool, python patch, heredoc), if `git diff --stat` says `Bin` for a text file, stop — that is corruption, not a rendering quirk. Cheap explicit check when a file has been machine-edited:

```bash
python -c "d=open('FILE','rb').read(); print('NULs:',d.count(b'\x00'),'ctrl:',sum(1 for c in d if c<9 or 13<c<32))"
```

Related Windows/shell byte-level hazards: [[feedback-sed-windows-path-escapes]], [[reference-autocrlf-defeats-content-hash-gates]], [[reference-command-center-crlf-hazard]].
