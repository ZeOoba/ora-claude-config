#!/usr/bin/env python3
"""desc-classn-remediate.py — safe MOVE-TO-BODY remediation for ora-skill-text-audit class n.

Class n flags a scheduled-task/skill frontmatter `description` that is >1536 chars
(the Code-surface listing cap, skillListingMaxDescChars) or carries >=2 changelog
fragments matching `vN.N (YYYY-MM-DD`. Severity MEDIUM above 2500 chars or 3 fragments.
Its remediation rule is explicit and non-negotiable:

    MOVE the changelog prose to the BODY. Preserve trigger vocabulary VERBATIM.
    NEVER delete. A trim that drops trigger terms is a routing regression —
    worse than the tokens it saves.

WHY THIS TOOL EXISTS (2026-08-17). 18 of 68 fleet task descriptions breach class n,
the worst at 7,779 chars. Doing this by hand 18 times invites the one mistake that
actually loses data, which is NOT the trim itself:

    SOME VERSIONS EXIST IN THE BODY ONLY AS POINTERS reading "see description field
    above". Trim the description and that pointer dangles — the content is gone.

Which versions those are is DIFFERENT PER FILE and CHANGES OVER TIME as other
sessions backfill entries. On automation-health-monitor it was {v1.20, v1.22} on
2026-08-14 and only {v1.20} by 2026-08-17. So the tool COMPUTES the pointer-only set
per run and refuses to write unless the migrated text is verifiably in the new body.

It also found a pre-existing dangling pointer that way: automation-health-monitor's
v1.16 note was absent from BOTH the body and the description — the pointer had been
lying for some time. Report those as VERIFIED NULLs; never reconstruct them.

USAGE
  # 1. inspect (no writes)
  python desc-classn-remediate.py --path "<...>\\SKILL.md" --report

  # 2. author the replacement description in a UTF-8 file, ONE line, starting with
  #    "description: ". Must retain every trigger phrase and the [MODEL: ...] tag.
  # 3. dry run, then apply
  python desc-classn-remediate.py --path "<...>\\SKILL.md" --new-desc-file new.txt
  python desc-classn-remediate.py --path "<...>\\SKILL.md" --new-desc-file new.txt --apply

  # fleet-wide breach table
  python desc-classn-remediate.py --scan

Exit 0 = ok / would-write   1 = a gate failed, nothing written   2 = could not look.
Always back the file up first (see --backup-hint).
"""
import argparse, io, os, re, sys

CAP_CHARS = 1536
MED_CHARS = 2500
MED_FRAGS = 3
FRAG = re.compile(r"v\d+\.\d+ \(\d{4}-\d{2}-\d{2}")
DEFAULT_ROOTS = [
    r"C:\Users\Owner\OneDrive - Oxford Capital Partners\Documents\Claude\Scheduled",
    r"C:\Users\Owner\.claude\scheduled-tasks",
]


def read(p):
    return io.open(p, encoding="utf-8").read()


def split_desc(txt):
    m = re.search(r"(?m)^description:(.*)$", txt)
    if not m:
        return None, None, None
    return m, m.group(1).strip(), txt.split("---", 2)[2] if txt.count("---") >= 2 else ""


def fragments(desc):
    marks = [x.start() for x in FRAG.finditer(desc)]
    out = {}
    for i, s in enumerate(marks):
        e = marks[i + 1] if i + 1 < len(marks) else len(desc)
        chunk = desc[s:e].strip().rstrip(".").rstrip()
        out[re.match(r"v(\d+\.\d+)", chunk).group(1)] = chunk
    return out


def pointer_only(frags, body):
    """Versions whose body mention is ONLY a back-pointer to the description."""
    res = []
    for ver in frags:
        real = False
        for mm in re.finditer(re.escape("v%s (" % ver), body):
            ctx = body[mm.start():mm.start() + 200]
            if "see description field above" not in ctx and "frontmatter" not in ctx:
                real = True
        if not real:
            res.append(ver)
    return sorted(res, key=lambda s: [int(x) for x in s.split(".")])


def severity(n, f):
    if n > MED_CHARS or f > MED_FRAGS:
        return "MEDIUM"
    if n > CAP_CHARS or f >= 2:
        return "LOW"
    return "-"


def scan(roots):
    rows = []
    for root in roots:
        if not os.path.isdir(root):
            continue
        for d in sorted(os.listdir(root)):
            if d.startswith("_"):
                continue
            p = os.path.join(root, d, "SKILL.md")
            if not os.path.isfile(p):
                continue
            try:
                txt = read(p)
            except Exception:
                continue
            m, desc, body = split_desc(txt)
            if not m:
                continue
            frags = fragments(desc)
            rows.append((len(desc), len(FRAG.findall(desc)),
                         "LAMS" if "OneDrive" in root else "CC", d,
                         pointer_only(frags, body), p))
    rows.sort(reverse=True)
    print("%-6s %-5s %-5s %-8s %-38s %s" % ("CHARS", "FRAG", "FLEET", "SEV", "TASK", "POINTER-ONLY (migrate first!)"))
    n_breach = 0
    for n, f, fl, d, po, _ in rows:
        sev = severity(n, f)
        if sev != "-":
            n_breach += 1
        print("%-6d %-5d %-5s %-8s %-38s %s" % (n, f, fl, sev, d, ",".join("v" + x for x in po) or "-"))
    print("\n%d of %d breach class n" % (n_breach, len(rows)))
    return 0


def report(path):
    txt = read(path)
    m, desc, body = split_desc(txt)
    if not m:
        print("[ACTION] no description: field in %s" % path)
        return 2
    frags = fragments(desc)
    po = pointer_only(frags, body)
    print("path        : %s" % path)
    print("chars       : %d  (cap %d)" % (len(desc), CAP_CHARS))
    print("fragments   : %d" % len(FRAG.findall(desc)))
    print("severity    : %s" % severity(len(desc), len(FRAG.findall(desc))))
    print("versions    : %s" % ", ".join("v" + v for v in sorted(frags, key=lambda s: [int(x) for x in s.split(".")])))
    print("POINTER-ONLY: %s   <-- these MUST be migrated to the body before trimming"
          % (", ".join("v" + v for v in po) or "none"))
    print("\n--- trigger-vocabulary candidates found in the current description ---")
    tp = re.search(r"[Tt]rigger(?:s| phrases| on|:)([^.]*)", desc)
    print(tp.group(0)[:400] if tp else "  (none detected — inspect manually before trimming)")
    print("\nbackup first:  Copy-Item \"%s\" \"%s.pre-classn-trim\"" % (path, path))
    return 0


def remediate(path, new_desc_file, apply, version_label):
    txt = read(path)
    m, desc, body = split_desc(txt)
    if not m:
        print("[ACTION] no description: field")
        return 2
    frags = fragments(desc)
    po = pointer_only(frags, body)
    new_desc = read(new_desc_file).strip()
    if not new_desc.startswith("description:"):
        print("[ACTION] --new-desc-file must start with 'description: '")
        return 1
    if "\n" in new_desc:
        print("[ACTION] replacement description must be ONE line")
        return 1

    new_txt = txt.replace(m.group(0), new_desc, 1)
    if po:
        block = ("\n\n*Changelog — MIGRATED FROM FRONTMATTER (%s, class-n remediation). These "
                 "entries previously existed ONLY in the `description` field; the body carried "
                 "pointers reading \"see description field above\", which stops being true the "
                 "moment the description is trimmed. Moved verbatim, not summarised.*\n\n"
                 % version_label) + "\n\n".join("- **%s" % frags[v] for v in po) + "\n"
        new_txt = new_txt.rstrip() + "\n" + block

    nd = re.search(r"(?m)^description:(.*)$", new_txt).group(1).strip()
    nb = new_txt.split("---", 2)[2]
    nfrag = len(FRAG.findall(nd))

    # trigger vocabulary that must survive: everything quoted after "Trigger"
    old_trig = re.findall(r"[Tt]rigger(?:s| phrases| on|:)([^.]*)", desc)
    trig_terms = []
    for t in old_trig:
        trig_terms += [s.strip() for s in re.split(r"[,;]", t) if 2 < len(s.strip()) < 60]

    checks = [
        ("<=%d chars" % CAP_CHARS, len(nd) <= CAP_CHARS),
        ("<2 changelog fragments", nfrag < 2),
        ("single line", "\n" not in nd),
        ("MODEL tag preserved", ("[MODEL:" in nd) == ("[MODEL:" in desc)),
        ("migrated text present in body", all(frags[v][:120] in nb for v in po)),
        ("body length not reduced", len(nb) >= len(body)),
    ]
    missing_trig = [t for t in trig_terms if t.lower() not in nd.lower()]
    checks.append(("trigger vocabulary preserved", not missing_trig))

    print("chars %d -> %d   fragments %d -> %d   migrating: %s"
          % (len(desc), len(nd), len(FRAG.findall(desc)), nfrag,
             ",".join("v" + x for x in po) or "none"))
    bad = [n for n, ok in checks if not ok]
    for n, ok in checks:
        print("  %-32s %s" % (n, "PASS" if ok else "FAIL"))
    if missing_trig:
        print("  dropped trigger terms: %s" % missing_trig[:8])
    if bad:
        print("\n[ACTION] REFUSING TO WRITE: %s" % ", ".join(bad))
        return 1
    if apply:
        io.open(path, "w", encoding="utf-8", newline="\n").write(new_txt)
        print("\nWRITTEN — saved %d chars" % (len(desc) - len(nd)))
    else:
        print("\n(dry run — pass --apply to write)")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--path")
    ap.add_argument("--new-desc-file")
    ap.add_argument("--version-label", default="2026-08-17")
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--scan", action="store_true")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    if a.scan:
        return scan(DEFAULT_ROOTS)
    if not a.path or not os.path.isfile(a.path):
        print("[ACTION] COULD-NOT-LOOK :: --path missing or not a file")
        return 2
    if a.report or not a.new_desc_file:
        return report(a.path)
    return remediate(a.path, a.new_desc_file, a.apply, a.version_label)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print("[ACTION] COULD-NOT-LOOK :: %s: %s" % (type(e).__name__, e))
        sys.exit(2)
