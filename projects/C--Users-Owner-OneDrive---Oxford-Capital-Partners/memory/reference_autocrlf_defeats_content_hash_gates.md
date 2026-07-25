---
name: reference-autocrlf-defeats-content-hash-gates
description: "On this machine (core.autocrlf=true), hashing raw disk bytes for a working-tree digest vs git's normalized index blob for a staged digest makes them differ for every text file -- use git's own blob object-id instead"
metadata:
  node_type: memory
  type: reference
  originSessionId: 7a4a4780-8a9c-48c2-839a-f10e60f49524
  modified: 2026-07-24T18:29:17.233Z
---

**This machine runs `core.autocrlf=true` globally** (`git config --global
core.autocrlf` → `true`). A checked-out text file on disk has CRLF line
endings; git's index/object store always holds the LF-normalized form.

**The trap:** any gate or tool that computes a content hash to compare
"what's on disk" against "what's staged" — e.g. `sha256(open(path,"rb").read())`
for a working-tree digest vs. `sha256(subprocess.run(["git","show",":"+path]).stdout)`
for an index digest — will get **different hashes for logically identical
content**, unconditionally, for every text file. This isn't a rare edge case;
it fires on the very first file with an `\n` in it.

**Where this bit** (2026-07-24): `hooks/eos-review-gate.py`'s content-hash
review key. `--record`/`--key` always hashed working-tree bytes; the hook,
for a plainly-staged path, hashed the index blob. Every real commit of a
separately-staged file (`git add` in one step, bare `git commit` later —
`git checkout <branch> -- <path>` counts) produced a key mismatch, making the
gate permanently unsatisfiable for that shape. Never caught by test fixtures,
because temp repos built by writing files directly with Python
(`open(path,"w",newline="\n")`) never round-trip through a real `git
checkout`, so autocrlf conversion never had a chance to fire. Same blind spot
class as [[feedback-fixture-shaped-tests-certify-dead-branches]] — found only
by attempting the real operation against the live checkout, not by any
review round's synthetic repro.

**The fix — compare git's own blob object-ids, not raw byte hashes:**
- working-tree digest: `git -C <repo> hash-object --stdin --path <rel>`,
  piping the raw disk bytes as stdin. Applies the SAME clean-filter/autocrlf
  normalization `git add` would.
- index digest: `git -C <repo> rev-parse --verify -q :<path>` (the blob oid
  directly — no need to `git show` the content and hash it yourself).
Two oids computed this way are directly comparable regardless of how the file
sits on disk. This is comparison-by-construction: it can't be fooled by line
endings because both paths route through git's own normalization pipeline
before anything gets compared.

**To reproduce/verify the bug is real** (useful for testing any future
content-hash gate): build a repo, commit a file, `os.remove()` it, then
`git checkout HEAD -- <path>` to force materialization — THIS is what
actually triggers the CRLF conversion (a plain `git add` only warns "will be
replaced... the next time Git touches it"; it doesn't rewrite the working
copy itself).

**How to apply:** any future hook/tool on this fleet that needs to detect
"has this file's content changed" or "does the staged version match the
working-tree version" must use git object-ids, never a raw
`sha256`/`hashlib` digest of file bytes read directly — unless it has
independently confirmed `core.autocrlf` is off for the relevant repo. See
[[project-eos-review-gate-shipped-2026-07-24]] for the full incident.
