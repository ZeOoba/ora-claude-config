---
name: lease-generation
description: "Oxford Realty Advisors NEW-LEASE production skill — from an LOI, broker term sheet, e-mail or typed deal terms to an execution-ready lease on ORA landlord paper, with a tracked-change redline and an LOI conformance memo. Use when the user says: generate the lease, draft the lease from this LOI, fill in the lease template, new lease for [suite/tenant], make the lease match the LOI, lease from these terms, produce the lease, or uploads an LOI/proposal to lease and wants a lease. Pipeline: DEAL-TERMS-REGISTER → property template (never the last executed lease) → token fill + clause modules (option, gross vs modified gross, escalations, overnight parking, landlord work, maintenance split, co-tenant) → LOI conformance matrix → cross-reference audit → lease-form-qc gate → clean DOCX + PDF + redline. NOT amendments (lease-addendum), template maintenance (masterlease-jurisdiction-rebase), counterparty paper (legal-intelligence) or LOIs (loi-generation). Draft only — outbound send needs confirmation. v1.0"
---

# lease-generation — LOI/term sheet → execution-ready ORA lease

Per-deal production skill. It sits between the two skills that already exist on either side of it:
`masterlease-jurisdiction-rebase` **maintains** the property templates; `lease-form-qc` **grades** a lease.
This skill **produces** one. It never grades its own output — the QC gate is the independent scanner.

Proven end-to-end on 2207 Northwood Suite 15A / Impact Home Technology LLC (2026-09-06/07): legacy draft failed
46/52 scanner checks and conformed to 7 of 16 LOI terms; the produced lease passed 51/52 (F5 Ohio-only), conformed
to every LOI term, with a validator-clean tracked-change redline from the same op list.

## Ratified positions (lease-form-qc, 2026-08-03) — apply by default, log every departure
1 modified gross w/ base year = calendar year of Commencement Date · 2 individuals join as **joint-and-several co-tenants, never a guaranty** · 3 deposit = 1.0× monthly · 4 late fee 10% + 18% default interest with usury savings clause · 5 flat Hazardous Materials ban, no carve-out · 6 no extension option by default.
An LOI can compel a departure (a gross deal, an option). Record it in the register's `ratified_position_departures` and in the memo. Never depart silently and never re-ask a settled position.

## Hard rules
- **Never fabricate deal facts.** Every register field has a `source`. LOI silent → ORA default (state it) or a bracketed blank, never an invented value. Project name, SF, proportionate share, meter configuration: verify against executed leases at the property / Notion Property Register, not the broker's marketing name.
- **Never draft from the last executed lease.** Template = the rebase output for the property/state. If none exists (legacy-form buildings), say so, use the best executed form at that property as the base, flag "re-paper onto master when available", and expect ~40+ scanner failures to clear via the modules.
- **Placement by heading title, never by section number.** All insertions are sub-level (Heading 2/3) inside existing sections except RIGHTS RESERVED BY LANDLORD, which goes after COVENANTS OF LANDLORD. Any Heading-1 insertion above SUBORDINATION breaks "Section 24"-type references — run the audit.
- **Every tenant ask is granted in full and bounded** by landlord conditions (see `references/clause-modules.md`). Do not strip conditions to "simplify".
- **Tracked changes are real** (`w:ins`/`w:del`/`w:pPrChange`), produced by the engine, validated with the docx skill's `validate.py --author`. Never a clean overwrite presented as a redline.
- **Outbound send = Hard Invariant 1.** Draft only. Sign as the property LLC.

## Procedure

### 0. Intake → DEAL-TERMS-REGISTER
Read the LOI/term sheet/e-mail. Build `deal-terms-register.json` per `references/deal-terms-register.schema.json`
(`references/example-register-northwood-15a.json` is a filled example). Compute the rent schedule for **every**
lease year including option years (escalation type from the LOI; if the LOI is silent, flat for the primary term and
raise a decision gate for option rent — recommend 3% compounding). Compute proportionate share from Notion Property
Register total SF. Pull landlord entity/notice block from the property's executed leases. List `decision_gates` and
`open_items`. Ask Gabriel **once**, with all gates in one message, only if a gate is material (option rent basis,
escalations not in the LOI, meter basis, personal co-tenant when the LOI names only the entity — position 2 says add
the individual; confirm identity).

### 1. Template
`python3 scripts/docx_edit_engine.py dump <template.docx>` — confirm it is the property template (footer tag
"ORA Master Lease v…", parcel number in §1) and list paragraph indices/styles. On a template, most fields are `[TOKEN]`s:
`python3 scripts/docx_edit_engine.py fill <template> tokens.json <out>` (body + footers; reports counts; any token
found 0 times is a fill error). Then apply modules for anything the master does not tokenize.

### 2. Ops file → build
Write `ops.json` (format in the engine docstring). Take module text from `references/clause-modules.md`, fill
`{PARAMS}` from the register, refs by `{"match": "HEADING TEXT"}`. Standard op order: §1 defs/as-is carve-out →
§2 term/delivery/option → §3 rent schedule → §4 expense structure → §6/§13/§14 conformity → §10 utilities →
§11 maintenance → §18/§19/§23/§24/§25/§26 conformity → §20 parking → §27 landlord work → §28 broker → §29 notices →
RIGHTS RESERVED insert → MISC (b)/(e)/(f)/(j)/(k)–(p) → seals → exhibits → footer → strip_highlight/strip_nbsp.
```
python3 scripts/docx_edit_engine.py apply <base.docx> ops.json <clean.docx>
python3 scripts/docx_edit_engine.py apply <base.docx> ops.json <redline.docx> --redline --author "Oxford Realty Advisors"
```
Exhibits: A = suite plan (+ office location + Overnight Parking Area) — "TO BE ATTACHED" is acceptable in a draft,
never in an execution copy; B = Landlord Work spec; C = ORA Rules & Regulations v1.2 exhibit (use the canonical
file when available; the module library carries a fallback set).

### 3. Gates (all four, in this order; fix and rebuild until clean)
1. `validate.py <clean> --original <base>` and `validate.py <redline> --original <base> --author "…"` → **All validations PASSED**.
2. `python3 scripts/xref_audit.py <clean.docx>` → section map + findings. Zero HIGH; every "Exhibit referenced but not
   attached" resolved or listed as an open item; unfilled tokens = BLOCK.
3. `lease-form-qc` scanner on the clean file. Target **0/52** on a master-derived lease. Acceptable residuals must be
   named and justified in the memo: F5 (Ohio seal check — inapplicable in MD/other seal states), T1 blanks deliberately
   left for the tenant (or convert to underscores), B7 only if Gabriel chose Premises-only notice.
4. **LOI conformance matrix**: one row per register field → lease section → CONFORMS / CONFORMS+ / PARTIAL /
   MISSING / CONFLICT. Nothing ships with PARTIAL/MISSING/CONFLICT unless Gabriel resolved it as a gate.
Render to PDF (`soffice --headless --convert-to pdf`, never Print-to-PDF) and look at the pages: numbering 1…N
continuous, sub-items (a)(b)(c), schedule lines, signature seals, exhibits.

### 4. Deliverables (deal-file naming: `[Address] [Purpose] [MM-YYYY]`)
`<Address> Suite <X> Lease <Tenant> <MM-YYYY> v0N.docx` · `.pdf` (text layer) · `… v0N REDLINE vs <base>.docx` ·
`YYYY-MM-DD_<Property>-<Suite>_LOI-Lease-Conformance-Memo_v0N.docx` (ORA style guide: matrix, numbering audit,
position departures, decision gates, open items, counsel-pass list). Save the register alongside. Present files;
state residual scanner items and open items in ≤6 lines.

### 5. Close-out
Record in memory: decision-gate resolutions (option rent basis, escalations), verified project name/meter basis,
and any new module or template defect discovered → route template defects to `masterlease-revision-cycle`.

## State overlays (minimum; counsel pass remains)
- **MD**: no recording ≤ 7 yrs (RP § 3-101); keep "under seal" + "(SEAL)" (12-yr specialty SOL, CJP § 5-102); no commercial
  duty to mitigate (*Circuit City v. Rockville Pike JV*, 376 Md. 331 (2003)) — qualifier "except to the extent required by law"
  still added; dual-agency consent (BOP § 17-530); e-sign Com. Law § 21-101; venue = county district/circuit court.
- **OH**: total term incl. options > 3 yrs → R.C. 5301.01 acknowledgment; mitigation qualifier required (*Frenchtown v.
  Lemstone*); seals abolished (drop "(SEAL)"); e-sign R.C. Ch. 1306.
- **MO/KS/IN/WI/TN**: use the rebase overlay; if none exists for the state, stop and say so.

## What this skill does not guarantee
Conformance to the LOI, the ratified positions, the scanner and internal consistency — yes. Substitute for state-law
counsel review — no. Every memo ends with a counsel-pass list (acceleration formula, attorney-in-fact estoppel,
notice-to-quit waiver, state-specific items).

## Files
- `scripts/docx_edit_engine.py` — JSON-op editor: set_body / replace_all / sub / sub_all / append / insert_after /
  delete / restyle / fill_tokens / footer ops; clean or tracked-change output; `dump` lists paragraphs.
  Requires `lxml` (non-stdlib): `pip install lxml`.
- `scripts/xref_audit.py` — reconstructs auto-numbering; flags missing numeric/title targets, fragile
  "this Section N", unattached exhibits, undefined quoted terms, unfilled tokens. Also requires `lxml`.
- `references/deal-terms-register.schema.json` — register schema. `references/example-register-northwood-15a.json` — filled example.
- `references/clause-modules.md` — M-01…M-13 landlord-drafted modules with parameters and scanner-canonical phrasing.

## Handoffs (Code surface)
- `masterlease-revision-cycle`: tokenize M-03 (option), M-05 (gross §4 variant), M-04 (schedule block), M-08
  (overnight parking), M-09 (landlord work + Exhibit B), M-01 defs into the master (v2.7) so this skill becomes a pure
  token fill + module toggle; rebase Northwood/MD and re-paper that building's 31 suites over time.
- `lease-form-qc`: add a FILENAME/DOCPROPERTY-field check (a footer resolving to another tenant's lease path = cloned
  from an executed lease) and an "LOI conformance" mode that consumes the register.
- `package-and-stage-skill`: package into ora-skills via tools/package_skills.py.

## Changelog
- v1.0 (2026-09-07) — initial. Engine, xref audit, register schema, 13 modules, four-gate procedure. Built from the
  Northwood 15A / Impact Home Technology run.
