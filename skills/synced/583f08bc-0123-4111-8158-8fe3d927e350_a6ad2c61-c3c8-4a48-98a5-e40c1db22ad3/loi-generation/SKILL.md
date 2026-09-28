---
name: loi-generation
description: "Oxford Realty Advisors letter-of-intent drafting skill. Use whenever the user mentions: draft LOI, produce LOI, create LOI, generate LOI, build LOI, ship LOI, LOI for a property, letter of intent, offer letter, or non-binding proposal to purchase; when an OM, broker package, or listing PDF is uploaded with intent to make an offer; or when an acquisition-underwriting evaluation advances to an offer. Encodes: STANDARD/CONDENSED formats, five conditional blocks (four numbered + one inline entity-interest election), seven state overlays (OH/MD/IN/MO/KS/WI/TN) incl. the HB 126 BOR dual-threshold rule, seller entity-interest matching, 1031-cooperation default w/ concealment overlay, vacancy preservation covenant, single-source deposit token, a 23-point QC Gate (item 23: offer must clear the ORA walk price), a mandatory DEAL-TERMS-REGISTER, and Lost-Deal Ledger capture at draft time. Outputs versioned DOCX + extractable-text PDF on ORA letterhead. v1.9"
---

# LOI Generation — Oxford Realty Advisors (v1.9 — 2026-09-10: changelog retention rule adopted, 6-entry + ~2,000-char caps)

You are operating as the lead acquisitions counsel-substitute for Oxford Realty Advisors. This skill produces a complete, broker-ready, buyer-protective letter of intent from an OM, broker package, or upstream `acquisition-underwriting` evaluation. The output is a condensed, plain-English LOI on ORA letterhead — not a contract, not legalese, but every dollar-material protection Gabriel needs at the LOI stage.

This skill OWNS the LOI-stage drafting decision. Do not delegate to `document-assembly` (template-fill only) or `legal-intelligence` (clause-level review). Use this skill end-to-end.

---

## ROUTING

| Trigger | Mode | Output |
|---|---|---|
| "draft LOI for [property]", broker package uploaded | **DRAFT** | Versioned DOCX + PDF preview |
| "ship the LOI", "send LOI to [broker]" | **SHIP** | DRAFT mode + Outlook draft for review (cc per thread context — no blanket cc of both principals; CC discipline 2026-06-10) |
| "revise LOI", "update LOI", "tweak LOI" | **REVISE** | Apply edits, increment version, re-run QC |
| "compare LOI to [prior version]" | **COMPARE** | Side-by-side diff memo |

When ambiguous, default to **DRAFT** and ask one clarifying question only if a material economic term is missing.

---

## INPUTS — what you need before producing

**Required (refuse to proceed if missing):**
- Property street address, city, state, ZIP
- Building square footage, site acreage
- Seller legal entity name (e.g., "MIINI-OHIO INVESTMENTS LLC")
- Purchase Price
- Earnest Money Deposit
- Seller broker name, firm, address
- **`Walk Price`** — the ORA walk price from `acquisition-underwriting` (the lowest price clearing **all** binding Stage 1 floors: Basis, Yield, and IRR). If no walk price exists for this deal, **run `acquisition-underwriting` first — do not draft.** An LOI is an offer; ORA does not make offers at prices it has not tested. Absence of a walk price is the single most common way a floor-breaching offer reaches a counterparty, because nothing downstream can catch what was never computed.

**Highly preferred (will pull from connectors or use ORA defaults if absent):**
- Tenancy status (vacant / single-tenant / multi-tenant)
- Tenant legal name(s) and affiliation to Seller
- Existence of any Right of First Refusal, ROFO, or pre-emptive right in the lease
- Roof age, HVAC age, known deferred-maintenance disclosures (for §4 carveout)
- Study Period length (defaults to 30 days)
- Closing window (defaults to 15 days post-Study)
- Exclusivity period (default 60 days vacant / 30 days tenanted)

**Source priority for inputs:**
1. User-provided values in the prompt (highest priority — always wins)
2. OM / broker package / listing PDF (extract via PDF text or Vision)
3. Notion **Acquisition Pipeline Tracker** (DB `bcfe4a03`) if the deal is already logged
4. Notion **Deal Sourcing Log** (DB `9a6ae219`) for broker and pricing context
5. HubSpot — Broker Relationships for broker contact details
6. ORA Standard Commercial Terms (this skill, §STANDARDS) for any term still unresolved

---

## DECISION LOGIC — populate before token replacement

### 0. Seller entity interest type (REQUIRED — 470 McCormick lesson)

The Acquisition Structure section's entity-purchase election must match the seller's entity form. Resolve from the seller legal name suffix:

| Seller suffix | {{ENTITY_INTEREST_TYPE}} |
|---|---|
| LLC / L.L.C. / Ltd (limited liability co) | `membership interests` |
| Inc / Corp / Co (corporation) | `equity interests` (or `shares of capital stock` if counsel directs) |
| LP / LLP / Limited Partnership | `partnership interests` |

Never ship "membership interests" against a corporate seller.

**Template hook (added 2026-08-18):** the master template carries this as an INLINE conditional within §13 (Acquisition Structure and Assignment) — a `▶ CONDITIONAL ◀` block containing one sentence keyed to `{{ENTITY_INTEREST_TYPE}}`, immediately following the existing Buyer-designee-LLC paragraph. It does NOT get its own numbered heading and does NOT affect section renumbering — evaluate it independently of the four numbered conditionals (§8/§9/§10/§11). Default is DELETE: fire it only when Seller itself holds the Property through a single-asset entity (an LLC, corporation, or LP whose sole asset is the Property) AND Buyer wants to preserve the option to buy that entity instead of taking a deed. A trust seller does NOT get this treatment — a trust is not a signing legal person in the entity-interest sense, and ORA deals with trust sellers convey by deed with the trustee identified on the Execution Page (see 3700 Kinsman Blvd, 2026-08-18, where this exact question arose and was resolved to deed conveyance).

### 0b. Format selection — STANDARD vs CONDENSED (sophisticated seller)

| Seller profile | Format |
|---|---|
| Institutional / corporate / repeat-player (e.g., Casto-grade developer, REIT, bank REO, family office with in-house or standing counsel, major-brokerage-represented portfolio seller) | **CONDENSED** — 11-section, ~3-page letter + Execution Page + Buyer Information page (5 pages total) |
| Private / individual / estate / unsophisticated seller | **STANDARD** — full condensed-master format (12–16 sections by conditionals) |

Rationale (Gabriel ruling 2026-06-10): a sophisticated counterparty expects the PSA to carry the legal weight; an over-lawyered LOI invites pre-PSA redlining and delay. With unsophisticated sellers the longer form anchors more terms while leverage is highest.

**CONDENSED merge map** (apply after conditional deletion/renumbering):
1. §1 Price/Deposit/Closing → single block paragraph.
2. §2 document-delivery bullets → one "property file" sentence (tax bills 3 yrs, plans/permits/COs, existing survey & title, environmental reports + governmental correspondence, service contracts + COIs, utility account info, vacancy confirmation or rent roll).
3. §4 Property Condition → two sentences: defect-free assumption (the repricing hook — ALWAYS retain) + as-is delivery with systems-operable standard. Bill-of-sale conveyance moves to the PSA list in Process.
4. §6 Prorations → one paragraph: "customary [County] allocations," long-proration method + BOR rights (OH), Seller pays conveyance fee / owner's policy / half escrow / lien releases; Buyer pays endorsements / deed recording / half escrow / survey.
5. Exclusivity + Definitive Documentation → merged "Process and Exclusivity" section, ending with the PSA-deferred list: bill of sale; Buyer access & insurance during Study Period; **Deposit due within two (2) business days after PSA execution**; closing/deed mechanics per the Acquisition Structure section.
6. Miscellaneous → two sentences (confidentiality 2 yrs; OH law/venue/time-of-essence/counterparts-e-signature).

**Survivors — never cut in either format:** Phase I→Phase II auto-extension (environmental tail cap) and the Acquisition Structure designee-vesting/direct-deeding mechanics.

### 0c. Exchange posture — 1031 cooperation DEFAULT vs concealment overlay

**DEFAULT (template standard): RETAIN the mutual IRC §1031 cooperation clause in Miscellaneous.** It is reciprocal, costless, and ORA transacts via exchange routinely. Removing it is the exception, never the rule (Gabriel ruling 2026-06-10).

**CONCEALMENT OVERLAY — apply ONLY when BOTH are true:** (a) seller is sophisticated/institutional (Format = CONDENSED trigger profile), AND (b) ORA has live buyer-side exchange-timeline pressure (drop-and-swap, 45/180-day identification windows). Then:
- Delete the mutual cooperation sentence from Miscellaneous.
- Delete any "Buyer intends to complete a §1031 exchange" motive language.
- Rely entirely on unnamed mechanics in Acquisition Structure: title may vest in one or more Buyer-designated affiliates or tenants-in-common (including any intermediary or accommodation titleholder designated by Buyer); assignment of LOI/PSA to designees by written notice pre-Closing; Seller cooperation with Buyer's closing structure including direct deeding and customary acknowledgments, at no additional cost, liability, or delay to Seller and without extending Closing.
- **QC leak-check (mandatory):** final document contains ZERO occurrences of "1031", "exchange", or "drop-and-swap".
This delivers full drop-and-swap capability without disclosing Buyer's tax posture or timeline pressure to the counterparty.

### 1. Tenancy classification

Determines opening paragraph phrasing and which conditional blocks fire.

| Signal in OM / inputs | Classification | `{{PROPERTY_TENANCY_PHRASE}}` | `{{TENANT_DISCLOSURE_PHRASE}}` |
|---|---|---|---|
| "Vacant," "100% available," "owner-occupied vacating," no current tenant | **vacant** | `vacant` | (empty string) |
| Single tenant in OM rent roll; not affiliated | **arm's-length single-tenant** | `single-tenant` | `, leased to {{TENANT_NAME}} (the "Tenant")` — no §8 will exist to define "Tenant," so the parenthetical is added here |
| Single tenant; tenant name shares a root with Seller LLC, OR OM discloses common ownership | **affiliated single-tenant** | `single-tenant` | `, leased to {{TENANT_NAME}}, an affiliate of Seller` — no trailing comma; §8 defines "Tenant" separately |
| 2+ tenants | **multi-tenant** | `multi-tenant` | (custom — list largest tenants in opening if material) |

**Punctuation convention (2026-08-18 fix — was producing "...,." in live drafts):** `{{TENANT_DISCLOSURE_PHRASE}}` is followed immediately by a period in the template body. Never let the resolved value end in a trailing comma.

**Affiliation test (decisional):** Set affiliated = TRUE if ANY of:
- Tenant LLC name contains Seller LLC root (e.g., "Buckeye Elm Contracting, LLC" + "BUCKEYE ELM HOLDINGS CO LLC")
- OM discloses sale-leaseback structure
- Tenant manager / principal is same as Seller manager / principal
- Tenant pays below-market rent identified during underwriting
- User explicitly states affiliation

### 2. Conditional block firing

Each conditional in the master template is evaluated independently. **Delete the entire `▶ CONDITIONAL ◀` ... `◀ END CONDITIONAL` block, including both markers, when the criterion is not met. Renumber subsequent sections sequentially.**

| Section | Block | Include if |
|---|---|---|
| §8 | Affiliated Tenant Disclosures | Tenant and Seller are affiliated entities |
| §9 | Tenant Estoppel | Property has any existing lease at Closing (any tenant) |
| §10 | Right of First Refusal Waiver | Existing lease contains ROFR, ROFO, or pre-emptive right |
| §11 | Lease Modification Restriction | Property has any existing lease at Closing |
| §13 (inline) | Entity-Interest Purchase Election | Seller holds the Property through a single-asset entity AND Buyer wants to preserve the option to buy entity interests instead of a deed. Rare — never fire for individual or trust sellers. Does not affect renumbering. |

**Vacant-property preservation covenant (MANDATORY when tenancy = vacant):** append to Continued Operations: "maintain active utility service, heat adequate to prevent freeze damage, and security and life-safety systems in operable condition." Rationale: "ordinary course consistent with past practice" obligates nothing for a long-vacant building (freeze-burst/copper-theft tail).

**Resulting section counts:**
- Vacant property: 12 sections (1–7, 12–16 from template, renumbered to 1–12)
- Arm's-length single-tenant, no ROFR: 14 sections (1–7, 9, 11, 12–16 renumbered to 1–14)
- Arm's-length single-tenant, with ROFR: 15 sections
- Affiliated single-tenant, with ROFR: 16 sections (all sections retained)
- Affiliated single-tenant, no ROFR: 15 sections

These counts reflect the four numbered conditionals only. The inline §13 entity-interest election adds a paragraph (not a numbered section) when fired, and never changes the count above or triggers renumbering.

### 3. State overlay selection for §6 (Prorations and Costs)

Replace the §6 default Ohio language with the matching overlay from `references/state-overlays.md`.

| State | County customs |
|---|---|
| **OH** | Long proration for Franklin/Cuyahoga/Hamilton counties; Seller pays state ($1/$1,000) + permissive county fee (varies $1–$3/$1,000); BOR appeal rights |
| **MD** | Recordation tax + transfer tax typically split 50/50; verify county (Montgomery, PG, Baltimore County, Frederick — different conventions) |
| **IN** | No state transfer tax; Sales Disclosure Form required; in-arrears tax billing |
| **MO** | No state real estate transfer tax; standard recording fees |
| **KS** | Mortgage registration tax abolished 2019; recording fees only; no transfer tax |
| **WI** | Wisconsin Real Estate Transfer Fee ($3/$1,000) paid by Seller |
| **TN** | Tennessee Realty Transfer Tax ($0.37/$100) paid by Seller |

**For any state not listed:** flag `[FORECAST]`, draft generic prose, and instruct user to verify locally.

### 4. Jurisdiction phrase resolution

`{{PROPERTY_JURISDICTION_PHRASE}}` fills the §2 jurisdiction-verification clause. Resolve as:

| Property location pattern | Phrase |
|---|---|
| Incorporated city, no surrounding township ambiguity | `the City of [CityName] and [County] County` |
| Address may straddle city/township (Columbus area, KC area) | `the City of [CityName], [County] County, [Township1], and/or [Township2]` |
| Unincorporated county area | `[County] County` |
| Confirmed Gahanna/Columbus suburb fully incorporated | `the City of [CityName] and Franklin County` |

When unclear, default to the broader formulation listing all potentially applicable jurisdictions.

### 5. Known-condition carveout (§4)

`{{KNOWN_CONDITION_CARVEOUT}}` fills inline within §4. Use when OM discloses a known condition:

| OM disclosure | Carveout text |
|---|---|
| Roof age ≥18 years | `(except for the roof, which the parties acknowledge is approximately [N] years old and approaching the end of its useful life)` |
| HVAC age ≥15 years | `(except for the HVAC system, which the parties acknowledge is approaching the end of its useful life)` |
| Deferred maintenance disclosed | `(except for the items of deferred maintenance disclosed in [Seller's marketing materials / Schedule X])` |
| Multiple conditions | Combine: `(except for [item 1] and [item 2])` |
| No known issues | DELETE the `{{KNOWN_CONDITION_CARVEOUT}}` token; leave no replacement |

### 5b. PSA-deferral list — standard contents (Process/Definitive Documentation section)

Always enumerate, so the PSA anchor is set without LOI negotiation: bill-of-sale conveyance at no cost; Buyer access & insurance during Study Period; Deposit due {{EMD_DUE_DAYS_WORDS}} business days after PSA execution; closing/deed mechanics per the Acquisition Structure section; specific-performance remedy for Buyer upon Seller default (all-cash buyer's primary risk is being shopped); title commitment within ten (10) days after PSA execution; Property delivered broom-clean, free of debris and personal property of others. OHIO DEALS add: Seller cooperation with — and agreement not to independently stipulate to — real-property-tax valuation proceedings affecting pre-Closing periods.

### 5c. Ohio BOR risk — statutory thresholds (HB 126, eff. 2022)

School districts may file ORIGINAL Board of Revision complaints only when the recorded sale exceeds auditor value by BOTH 10% AND $500,000 [verify thresholds with counsel]. Below either, the school-board route is barred; only scheduled reappraisal applies. Run the dual test at offer price vs auditor value before asserting BOR risk. (470 McCormick: +$117.8K = over 10%, under $500K → original complaint barred.)

### 6. Economic term defaults

When the user hasn't specified, apply ORA Standard Commercial Terms from `references/ora-standards.md`. Prefer the deal-size-adjusted values.

| Term | Default (deal <$3M) | Default ($3M–$10M) | Notes |
|---|---|---|---|
| EMD | 3% PP, min $50K | 2% PP | Larger EMD for tenanted/complex |
| Study Period | 30 days | 45 days | Add days for environmental complexity |
| Closing | 15 days post-Study | 30 days post-Study | Per Gabriel's standing preference |
| Exclusivity | 60 days vacant / 30 days tenanted | 60 days | Tenanted moves faster, less DD overhang |
| PSA initial draft | 10 business days | 10 business days | |
| PSA execution | 15 calendar days | 15 calendar days | |

### 7. Buyer signatory

Default values from `references/ora-standards.md`:
- `{{BUYER_SIGNATORY_NAME}}` = `Gabriel Goldberg`
- `{{BUYER_SIGNATORY_TITLE}}` = `Authorized Representative`

Override only if user explicitly directs (e.g., "Eric to sign this one").

### 8. Offer expiration

Default: 7 calendar days from `{{LOI_DATE}}`, adjusted to the next business day if it falls on a weekend or federal holiday. Never less than 5 BD; never more than 14 calendar days.

---

## TOKEN REFERENCE (canonical list)

These are the tokens that appear in the master template. The skill is responsible for resolving every one before saving the file.

### Date and money
| Token | Example | Source |
|---|---|---|
| `{{LOI_DATE}}` | `May 15, 2026` | Today's date (or user-specified) |
| `{{OFFER_EXPIRATION_DATE}}` | `May 22, 2026` | LOI_DATE + 7 calendar days, business-day-adjusted |
| `{{PURCHASE_PRICE_WORDS}}` | `One Million Four Hundred Thousand and 00/100` | User / OM offer |
| `{{PURCHASE_PRICE_NUMERIC}}` | `1,400,000.00` | Same |
| `{{EMD_WORDS}}` | `One Hundred Thousand and 00/100` | User or ORA standard |
| `{{EMD_NUMERIC}}` | `100,000.00` | Same |
| `{{EMD_DUE_DAYS_WORDS}}` | `two (2)` | Deposit due window after PSA execution — DEFAULT two (2) for all-cash certainty signaling; SINGLE SOURCE: feeds §1 AND any PSA-deferral mention. Root cause of the 470 McCormick §1-vs-§10 conflict |

### Time periods (all phrased as `[word] (digit)`)
| Token | Example |
|---|---|
| `{{STUDY_PERIOD_WORDS}}` | `thirty (30)` |
| `{{CLOSING_DAYS_WORDS}}` | `fifteen (15)` |
| `{{EXCLUSIVITY_DAYS_WORDS}}` | `sixty (60)` or `thirty (30)` |
| `{{PSA_DRAFT_DAYS_WORDS}}` | `ten (10) business` |
| `{{PSA_EXECUTE_DAYS_WORDS}}` | `fifteen (15) calendar` |

### Property
| Token | Example |
|---|---|
| `{{PROPERTY_STREET_ADDRESS}}` | `1333 Research Road` |
| `{{PROPERTY_CITY}}` | `Gahanna` |
| `{{PROPERTY_STATE_FULL}}` | `Ohio` |
| `{{PROPERTY_STATE_ABBR}}` | `OH` |
| `{{PROPERTY_ZIP}}` | `43230` |
| `{{PROPERTY_COUNTY}}` | `Franklin County` |
| `{{PROPERTY_SF}}` | `19,018` |
| `{{PROPERTY_ACRES}}` | `2.46` |
| `{{PROPERTY_USE_TYPE}}` | `industrial` or `industrial / warehouse` or `flex` |
| `{{PROPERTY_TENANCY_PHRASE}}` | `vacant` / `single-tenant` / `multi-tenant` |
| `{{PROPERTY_ZONING_PHRASE}}` | `zoned M2 Manufacturing` — VERBATIM from the OM/listing. Body sentence reads "...acres of land {{PROPERTY_ZONING_PHRASE}}", so the value should read naturally after "land" (e.g. `zoned M2 Manufacturing`, `zoned CC`). Never invent a designation not in the marketing materials or a verified GIS pull — if unknown, ask rather than defaulting to a generic phrase. |
| `{{ENTITY_INTEREST_TYPE}}` | `membership interests` / `equity interests` / `partnership interests` per Decision Rule 0 |
| `{{PROPERTY_JURISDICTION_PHRASE}}` | `the City of Gahanna and Franklin County` |
| `{{KNOWN_CONDITION_CARVEOUT}}` | `(except for the roof, which the parties acknowledge is approximately twenty-one (21) years old and approaching the end of its useful life)` or empty |

### Seller / broker
| Token | Example |
|---|---|
| `{{SELLER_ENTITY_NAME}}` | `BUCKEYE ELM HOLDINGS CO LLC` (preserve original capitalization) |
| `{{SELLER_BROKER_FULL_NAME}}` | `David Ludwig` |
| `{{SELLER_BROKER_FIRM}}` | `Coldwell Banker, Ludwig Real Estate Group` |
| `{{SELLER_BROKER_ADDRESS_1}}` | `8800 Lyra Drive, Suite 600` |
| `{{SELLER_BROKER_ADDRESS_2}}` | `Columbus, Ohio 43240` |
| `{{SELLER_BROKER_SALUTATION}}` | `David` |

### Tenant (only if conditional §8 / §10 fires)
| Token | Example |
|---|---|
| `{{TENANT_NAME}}` | `Buckeye Elm Contracting, LLC` |
| `{{TENANT_DISCLOSURE_PHRASE}}` | Arm's-length: `, leased to Buckeye Elm Contracting, LLC (the "Tenant")`. Affiliated: `, leased to Buckeye Elm Contracting, LLC, an affiliate of Seller`. Never end in a trailing comma — a period follows immediately in the template. |

### Buyer signatory
| Token | Example |
|---|---|
| `{{BUYER_SIGNATORY_NAME}}` | `Gabriel Goldberg` |
| `{{BUYER_SIGNATORY_TITLE}}` | `Authorized Representative` |

---

## WORKFLOW — execute in this order

### Phase 1 — Ingest and parse
1. Read user prompt for any explicit values (Purchase Price, deposit, dates, etc.).
2. If a PDF/DOCX is attached, extract OM data: address, SF, acreage, asking price, tenant status, broker contact, photos, building age, rent roll if present.
3. If property is already in Notion Acquisition Pipeline Tracker (`bcfe4a03`), pull existing fields.
4. If broker email/contact missing, search HubSpot CRM for broker by name or firm.

### Phase 2 — Apply decision logic
1. Classify tenancy (vacant / arm's-length / affiliated / multi-tenant).
2. Determine which conditionals fire.
3. Select state overlay for §6.
4. Resolve jurisdiction phrase for §2.
5. Resolve known-condition carveout for §4 (or leave empty).
6. Apply economic term defaults from ORA Standards for any unspecified term.

### Phase 3 — Token resolution
1. Build full token map.
2. Verify no required token is unresolved. If any is missing, list them and ask Gabriel for clarification before producing the file.
3. Convert numeric amounts to word form for `_WORDS` tokens. Format numerics with commas and trailing `.00`.

### Phase 4 — Document assembly (Python)
Use `python-docx` to:
1. Open `templates/LOI_Master_Template_Condensed.docx`.
2. Delete the Template Metadata page (paragraphs 0 through the start of the LOI body at "VIA ELECTRONIC TRANSMISSION").
3. Delete the State Overlay Appendix at the end (paragraphs from "APPENDIX  ·  DELETABLE" to end of document, excluding the closing letterhead table).
4. Replace each `{{TOKEN}}` with its resolved value, preserving gold sans-serif formatting only for unresolved tokens (none should remain).
5. For each conditional block: if criterion met, strip the `▶ CONDITIONAL ◀` and `◀ END CONDITIONAL` marker paragraphs; if criterion not met, delete all paragraphs between markers (inclusive).
6. Renumber sections sequentially (§1, §2, … §N) after conditional deletions. The inline §13 entity-interest conditional (added 2026-08-18) does NOT participate in renumbering — evaluate and strip/retain it independently of the four numbered conditionals.
7. Update Non-Binding paragraph cross-references to match the new section numbers.
8. Replace §6 body with the matching state overlay if non-Ohio.
9. If known condition exists, replace `{{KNOWN_CONDITION_CARVEOUT}}` with the carveout text. Otherwise, delete the token cleanly (no stray punctuation).
10. Confirm `{{PROPERTY_ZONING_PHRASE}}` and (if the inline §13 conditional fires) `{{ENTITY_INTEREST_TYPE}}` are resolved — both are now live template tokens (2026-08-18 sync), not documentation-only.

### Phase 5 — QC Gate (refuse to save if any item fails)

| # | Check |
|---|---|
| 1 | All `{{TOKENS}}` resolved; no gold sans-serif placeholders remain in body |
| 2 | All `▶ CONDITIONAL ◀` blocks evaluated; markers removed |
| 3 | §6 language matches property state |
| 4 | Section numbering sequential; cross-references in non-binding paragraph match retained sections |
| 5 | Template Metadata page deleted; State Overlay Appendix deleted |
| 6 | Tenancy disclosure in opening paragraph matches `{{PROPERTY_TENANCY_PHRASE}}` |
| 7 | Economic terms within ORA acceptable ranges (or deviations explicitly noted in chat) |
| 8 | Buyer signatory matches user instruction (default Gabriel) |
| 9 | Letterhead phone reads **301.512.6125** (both top and bottom letterhead tables) |
| 10 | Footer reads `[PROPERTY_STREET_ADDRESS] LOI · Page X of Y` with PAGE/NUMPAGES fields |
| 11 | "Proof of funds available upon request." appears centered italic in grey on the very last page, lower third |
| 12 | Tenant count in BUYER INFORMATION trailer reads "approximately 140 tenants" |
| 13 | Offer expiration date is a business day no fewer than 5 business days from LOI date |
| 14 | EXECUTION PAGE present with Buyer signature block populated (Gabriel Goldberg, Authorized Representative) and Seller block populated with `{{SELLER_ENTITY_NAME}}` |
| 15 | Strike list clean: NO "shall" (excluding "shallow"), NO banned phrases ("I hope this finds you well," "Just following up," "As discussed," "FYI," "Going forward," "At your earliest convenience") |
| 16 | PDF generated via `soffice` (NOT Microsoft Print to PDF); extractable text confirmed by `pdftotext` round-trip |
| 17 | PAGINATION: Buyer Information page starts its own page (page_break_before on its heading — never rely on stacked empty paragraphs); Proof-of-funds line sits on the FINAL page lower third; page count = 5 (CONDENSED) or 6–8 (STANDARD). KNOWN TEMPLATE DEFECT: the master template carries ~40 trailing empty paragraphs + stray page-break-before paragraphs that render 7–8 pages — strip empty/PBB paragraph runs during assembly |
| 18 | Entity-interest language matches seller suffix (Rule 0) — "membership interests" never ships against an Inc/Corp seller |
| 19 | Zoning phrase matches the OM verbatim (Rule: zoning token) |
| 20 | If concealment overlay active (Rule 0c): leak-check confirms ZERO occurrences of "1031" / "exchange" / "drop-and-swap" |
| 21 | DEPOSIT-TIMING CONSISTENCY: all Deposit due-window mentions resolve from {{EMD_DUE_DAYS_WORDS}} and are identical in the final text |
| 22 | Vacant deals: preservation covenant present; casualty threshold "five percent (5%) of the Purchase Price" survived CONDENSED compression |
| 23 | **Offer ≤ Walk Price (v1.8).** Compare `ORA Offer Price` against `Walk Price`. If the offer **exceeds** the walk price, **FAIL the gate and refuse to save the document.** Report: the offer, the walk price, the dollar and percentage gap, and which Stage 1 floor binds. The only permitted override is an **Exception Register** entry (per acquisition-underwriting's EXCEPTION REGISTER + TRIPWIRE) carrying a one-sentence compensating factor and Gabriel's explicit in-turn ratification — logged to the ranking workbook's Exception Register tab **and** the Notion row's "Exception Compensating Factor" field **before** the document is saved, not after. This gate is deliberately redundant with the Phase 6c consistency rule below: 6c catches the contradiction for the ledger, item 23 prevents the document. Two live incidents where 6c alone was insufficient — 511 Industrial Mile Road (Walk $930K / LOI $1.45M, loss permanently `UNCLASSIFIED` as a result) and 3700 Kinsman Blvd (Walk $2,661,000 / drafted LOI $3,800,000, caught only because a FULL underwrite was separately requested four days after the LOI was drafted). |

If any check fails, fix and re-run. Do not present a failing file.

### Phase 6 — Save and present
1. Filename: `LOI [Property Street] [City] [State] [M.D.YYYY].docx` — match Gabriel's convention (e.g., `LOI 1333 Research Rd Gahanna OH 5.14.2026.docx`).
2. Save to outputs folder.
3. Generate PDF preview via `soffice --headless --convert-to pdf`.
4. Present both files to user via `present_files`.
5. Log to Notion Acquisition Pipeline Tracker (`bcfe4a03`): set `LOI Status` = "Submitted", set the **`LOI Expiration Date`** date field (added 2026-08-05) to `{{OFFER_EXPIRATION_DATE}}` from Phase 5 §8, link to file, and a single-line summary of terms in `Next Action`. **Write the expiration into the dedicated date column — never only into `Next Action` prose.** A date sitting only in prose is exactly the "embedded arithmetic" anti-pattern `ora-deal-aging-sla` was hardened against on 2026-08-03 ("an aging anchor belongs in a computed field or nowhere") — it rots the moment anyone edits the field, and nothing can safely alert against it. The dedicated column is what `ora-deal-aging-sla` STEP 3c (added 2026-08-05) reads to flag a drafted-and-unshipped LOI whose own expiration has lapsed — see that skill's changelog; origin was 470 McCormick Blvd's LOI FINAL v2 sitting unshipped 21 days past its stated expiration before being killed. **Also set `Last Activity` = today (date-only).** This field — not Notion's system last-edited timestamp — is what the weekly `ora-deal-command-board` reads to decide staleness; stamping it here keeps the stall flag honest (added 2026-07-17). **And set `Next Action Date` (added 2026-08-12) to the date ORA must next act on** — for a submitted LOI that is normally the seller-response deadline. The single-line `Next Action` summary you write above is precisely where a date would otherwise get buried in prose, which is the failure this column exists to end; the paragraph above already makes this argument for `LOI Expiration Date`, and it applies unchanged to a second field. **Keep the two dates distinct even when they coincide:** `LOI Expiration Date` is the instrument's own expiry (what `ora-deal-aging-sla` STEP 3c reads to catch a drafted-but-unshipped LOI), while `Next Action Date` is when ORA is next on the hook. They are usually the same date on a submitted LOI and diverge the moment a response arrives early or an extension is granted — at which point `Next Action Date` moves and the expiration does not. If the next action has no date, leave the column NULL rather than defaulting it to the expiration.

### Phase 6b — Deal Terms Register (MANDATORY — at draft AND at execution)
The register is the deal's tracking point for every material term — especially terms agreed OUTSIDE the LOI (easements, parcel exclusions, verbal agreements, strategy-driven omissions). Side-channel terms exist in NO binding document until the PSA captures them; the register is how they survive the LOI→PSA handoff. (Origin: 2026-06-11, 754 Old State — the deal's linchpin easement lived only in an IC memo and meeting notes, and was absent from counsel's PSA draft.)

1. **At draft time**: create `DEAL-TERMS-REGISTER.md` in the deal folder (status DRAFT). Sections:
   - **Off-LOI terms** — every term agreed in negotiation but deliberately or accidentally not in the LOI. ASK the user explicitly: "What was agreed with the seller that is NOT in this LOI?" Each item gets: source (memo/notes/call), **Must land in** (PSA / DD / closing docs), **Status** (OPEN/RESOLVED).
   - **Strategy constraints** — positions to keep OUT of deal documents (e.g., no tenant-retention commitments, confidential rationales). Marked INTERNAL ONLY.
   - **Tracking items** — facts that must reconcile through DD (SF discrepancies, stale title work, election deadlines that expire at PSA execution).
2. **At execution** (when the countersigned LOI returns): update the register to EXECUTED status, re-confirm the off-LOI list against the final negotiation record, and date it.
3. Header must carry: "INTERNAL ONLY — never share with seller, broker, or any counterparty."
4. Downstream: deal-execution Workflow 2A reads this register at every PSA draft/redline round — every OPEN "Must land in: PSA" item missing from a draft is an automatic CRITICAL. psa-reconciliation validates the executed PSA against it.
5. Confidential-deal overlay: for hook-protected deals, the register stays in the deal folder / approved staging paths only (rules.md §7a) — never in outputs/ trees bound for external surfaces.

### Phase 6c — Lost-Deal Ledger capture (MANDATORY — at draft time)
Write ORA's own offer into structured Notion fields the moment the LOI exists. **Every value below is already in working memory at this point in the run — capturing it now is free, and reconstructing it in six months is expensive or impossible.** This is the capture half of the lost-deal post-mortem ledger; the outcome half is written later by `ora-passed-deal-tracker` Step 4b.

1. Locate the deal's row in the Notion **Deal Sourcing Log** (`collection://9a6ae219-85a3-4621-899c-c757fd062f8b`), matching on normalized street address. **If no row exists, create one** — a deal that reached LOI without a sourcing row is a gap, not a reason to skip capture. **If more than one row matches, do not guess:** write to the row with the most complete underwriting and flag the duplicate to Gabriel (this is live — `511 Industrial Mile Road` currently has two rows).

2. Set these properties (Block A):

   | Property | Value |
   |---|---|
   | `LOI Sent Date` | the date the LOI is actually delivered (leave NULL at draft if unshipped) |
   | `ORA Offer Price` | the purchase price in the LOI |
   | `ORA Offer $/SF` | offer ÷ Total SF |
   | `ORA Basis @ Offer (% RCT LOW)` | all-in basis ÷ RCT v03 LOW for the market |
   | **`ORA Max Defensible Price`** | **see §3 — the load-bearing number** |
   | `Offer: DD Days` / `Offer: Close Days` / `Offer: Deposit $` | from the LOI terms |
   | `Offer: All-Cash` / `Offer: Financing Contingency` | from the LOI terms |
   | `LOI Outcome` | `PENDING` |

3. **`ORA Max Defensible Price` — compute it NOW, at LOI time.** It is the price at which this deal *first breaches a Stage 1 floor* (the vintage-ramp basis floor or the 8% YoC floor, whichever binds first) — i.e. the most ORA could have paid without breaking a ratified governor. It is fixed at this moment and **never recomputed at outcome time**; recomputing it once the winning price is known is hindsight bias, and the downstream classifier explicitly refuses to run on a value written after the fact. Without this number a lost deal can never be classified as basis-vs-execution and the row is permanently `UNCLASSIFIED` — which is precisely the hole this phase closes.

   It is a *different number from `Walk Price`*, and both must be internally consistent with `ORA Offer Price`. **An offer above the walk price is a contradiction — stop and resolve it, do not write both.** (Live example of the failure: `511 Industrial Mile Road` carries Walk $930,000 against a $1,450,000 LOI, and its loss is stuck unclassifiable as a result.)

4. `LOI Sent Date` is written at Phase 7 SHIP, not here. A drafted LOI that never ships is a real and recorded failure mode — 470 McCormick Blvd's LOI FINAL v2 lapsed 21 days unsent — and it is logged as `LOI Outcome = EXPIRED-UNSENT` with `ORA Offer Price` left **BLANK**: an unsent LOI has no offer price, and treating a drafted figure as an offer corrupts every downstream aggregate.

5. This phase writes ORA's own numbers only. It never records a competitor's price, never estimates one, and never recommends an offer level.

### Phase 7 — Optional SHIP mode
If user requested ship:
1. Draft the email for Gabriel's review. (Composio `OUTLOOK_*` retired 2026-06-11 — connector removed, no fallback. The approved send, if Gabriel green-lights, runs via Outlook COM `C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1`, the SOLE send path.)
2. To: `{{SELLER_BROKER_EMAIL}}` (pull from HubSpot).
3. Cc: per thread context — no blanket cc of both principals (CC discipline, ratified 2026-06-10). Never `ze@oxfordra.net`.
4. Subject: `LOI — [Property Street], [City], [State]`.
5. Body: 3-sentence cover note in ORA broker voice (collegial, market-aware, no over-commitment). Attach DOCX and PDF.
6. Do NOT send — present the draft for Gabriel's review and approval. Pause for explicit go-ahead before send.

---

## STANDARDS — ORA defaults reference

See `references/ora-standards.md` for the full standards table. Key numbers:

| Term | ORA Standard | Acceptable Range | Rationale |
|---|---|---|---|
| EMD | 2–3% PP, min $50K | 1–7% PP | Smaller deals warrant proportionally larger % |
| Study Period | 30 days | 30–60 days | 30 default; 45 if complex DD anticipated |
| Closing post-Study | 15 days | 15–45 days | Gabriel's standing preference: 15 |
| Exclusivity | 60 days | 30–90 days | 60 for vacant; 30 acceptable for tenanted |
| PSA initial draft | 10 BD | 5–15 BD | |
| PSA execution | 15 calendar days from draft | 10–30 days | |
| Phase I auto-extension | To Phase II receipt | Standard | |
| Tenant Estoppel | 10 BD before Closing | 5–15 BD | Condition precedent |

---

## STATE OVERLAYS — quick reference

Full overlay text in `references/state-overlays.md`. Summary of §6 distinguishing language:

- **OH** — Franklin/Cuyahoga County long proration; Seller pays state conveyance ($1/$1,000) + permissive county fee (varies); BOR appeal rights to Buyer
- **MD** — Recordation + transfer tax customarily 50/50; verify by county
- **IN** — No state transfer tax; Sales Disclosure Form required; tax billing in arrears
- **MO** — No state real estate transfer tax; standard recording fees
- **KS** — Recording fees only; no transfer tax
- **WI** — Real Estate Transfer Fee $3/$1,000 Seller-pays
- **TN** — Realty Transfer Tax $0.37/$100 Seller-pays

---

## STRIKE LIST — banned phrases (LOI must not contain any)

- "shall" (anywhere — use "will")
- "I hope this finds you well"
- "Just following up"
- "As discussed"
- "FYI"
- "Going forward"
- "At your earliest convenience"
- "Hopefully"
- "I think we should"
- "Quick question"
- "Sorry for the delay"
- "Notwithstanding the foregoing" (use "However")
- "Pursuant to" (use "under" or drop)
- "Hereunder," "hereof," "thereof," "thereunto" (drop)

---

## CONNECTORS USED

| Connector | Tool | Purpose |
|---|---|---|
| Notion | `notion-search`, `notion-fetch`, `notion-update-page` | Pull Acquisition Pipeline Tracker, Deal Sourcing Log, Tenant DB |
| HubSpot | `search_crm_objects`, `get_crm_objects` | Pull broker contact details from Broker Relationships |
| Outlook (COM) | `send-via-outlook.ps1` via Desktop Commander `start_process` | Ship mode send after explicit approval (Composio `OUTLOOK_*` retired 2026-06-11) |
| Workspace bash | `python3` with `python-docx` | Document assembly |
| Workspace bash | `soffice` headless | PDF generation |
| Cowork | `present_files` | Deliver outputs |

---

## SPECIAL CASES

### Multi-tenant property
- `{{PROPERTY_TENANCY_PHRASE}}` = `multi-tenant`
- `{{TENANT_DISCLOSURE_PHRASE}}` = `` (empty) OR include short phrase referencing largest tenants
- Conditional §8 (Affiliated Tenant) typically DOES NOT fire (multi-tenant rarely all-affiliated)
- Conditional §9 (Estoppel) — modify to "Seller will cause each Tenant occupying more than [SF threshold] to deliver an estoppel"
- Conditional §11 (Lease Modification) fires; flag in chat that this should be PSA-strengthened with portfolio-wide restrictions

### Vacant property
- All four conditionals DELETE
- `{{TENANT_DISCLOSURE_PHRASE}}` = empty string (resulting opening reads "... acres of land {{PROPERTY_ZONING_PHRASE}}.")
- §4 may include vacant-building maintenance covenant (heat/sprinkler) — the master template already contains this in §7 bullets

### Property in unfamiliar state (not in seven-state overlay list)
- Flag `[FORECAST]` in chat
- Draft generic §6 language with placeholder reading "[STATE]: confirm customary proration method and transfer-tax allocation with local counsel before transmission"
- Do not ship without user verification

### Sale-leaseback indicated
- Tenancy = affiliated single-tenant
- All four conditionals fire
- Add `[SPECULATIVE]` flag in chat: sale-leaseback financing structures often warrant stronger §11 lease-modification restrictions including capped concessions
- Recommend lengthening Study Period to 45 days to allow tenant credit underwriting

### Seller refuses long proration (rare)
- Cite ORC § 5709.01 et seq. and Franklin County Bar custom in pushback memo
- Fall-back: short proration with Seller credit for prior year unpaid taxes (preserve buyer-protective substance)

---

## VERSIONING

- v1.9 — 2026-09-10, retention rule adopted (ORA Automation Audit R24-11). This skill was the 3rd-largest in the catalog at 7,208 words and carried **no growth bound of any kind** — the full v1.0–v1.8 history sat inline and had never been extracted. Added the 6-entry count cap and the ~2,000-char per-entry cap below, and performed the extraction the count rule demanded in the same pass (v1.3/v1.2/v1.1/v1.0 → `versions/CHANGELOG-v1.0-v1.3.md`). **No conditional block, state overlay, QC Gate item, walk-price precondition or token changed** — documentation discipline only.

**Retention rule (added 2026-09-10, ORA Automation Audit R24-11 — ported from `register-scheduled-task` v2.18/v2.20, `package-and-stage-skill` v1.30 and `ora-setup-audit` v1.12, which already carry it):** keep at most the **6 most recent versions** as full inline entries. The moment an edit would add a 7th, that same edit must also compress the oldest full inline entry to a one-line `**vX.Y (date):** Full text: versions/CHANGELOG-vA.B-vX.Y.md` summary and append its full original text to the versions file for that range (opening a new one if the prior range is closed out). Do it inline, in the pass that adds the new entry — never as deferred cleanup, and never wait for an audit to notice.

**Per-entry length cap (same pass, and the reason the count cap alone is not enough).** The 6-entry rule bounds how MANY entries are inline, never how LARGE each is — the exact defect `ora-setup-audit` v1.10 fixed in its artifact's rev-bands and `ora-cc-schematic-refresh` fixed at its v1.4. Cap each full inline entry at **~2,000 characters**, calibrated rather than copied: measured 2026-09-10, inline entries across this skill and its two siblings run 127–2,142 chars, so the cap fits every compliant entry with headroom while binding the two outliers. An entry that would exceed it states its finding and verdict inline and cites the deal folder or `versions/` file for the detail. Check both caps in the pass that adds an entry.

- v1.8 — 2026-08-22, walk-price precondition moved upstream: the offer-vs-walk-price contradiction rule already existed at Phase 6c (Lost-Deal Ledger capture) but ran only after the document was assembled, QC'd, and saved — a ledger-capture concern, not a precondition. Added `Walk Price` to the required-inputs list (refuse to draft without it — run `acquisition-underwriting` first) and a new hard-fail QC Gate item 23 (Offer ≤ Walk Price, refuse to save on breach, override only via a ratified Exception Register entry). Phase 6c is left unchanged and is now deliberately redundant with item 23: 6c catches the contradiction for the ledger, item 23 prevents the document. Two live incidents drove this: 511 Industrial Mile Road (Walk $930K / LOI $1.45M, loss permanently `UNCLASSIFIED`) and 3700 Kinsman Blvd (Walk $2,661,000 / drafted LOI $3,800,000, caught only because a FULL underwrite was separately requested four days later) — 6c alone was insufficient both times because it never blocked the save. QC Gate item numbering is 1–23, not the 1–16 assumed by the originating patch proposal; the gate had already been expanded to 22 items same-day by an unrelated fix (`references/qc-gate.md` title/count sync, commit `0eb8f5f`) before this patch landed, so item 23 (not 17) is the correct insertion point. No scorecard weight, Stage 1 floor, or governor constant changed.
- v1.7 — 2026-08-21, repo-first reconciliation: merges two independently-built v1.6 revisions that collided on the same version number after diverging from a common v1.5 base without either side knowing about the other. Combines the Lost-Deal Ledger capture (Phase 6c, below) with the 2026-08-18 template/token sync pass. `templates/LOI_Master_Template_Condensed.docx` replaced with the platform-side v1.1 copy carrying the template-mechanics fixes; Phase 6c writes only to Notion and required no template changes, so nothing from the repo side was lost in the swap. Discovered via `tools/repo_first_check.py`'s full sweep (`_staging/STORE_AHEAD_OF_REPO.md`, pending since 2026-08-21T21:39Z); reconciled per Gabriel's direction.
- v1.6 — 2026-08-18, template/skill sync pass (triggered by 3700 Kinsman Blvd / Madison WI deal, where both gaps surfaced live). Master template `LOI_Master_Template_Condensed.docx` bumped to its own v1.1: (1) `{{PROPERTY_ZONING_PHRASE}}` wired into the opening paragraph, replacing the hardcoded "commercially zoned industrial land" — Variable Reference table updated with a matching row; (2) `{{ENTITY_INTEREST_TYPE}}` wired in as a new INLINE conditional within §13 (Acquisition Structure), independent of the four numbered conditionals and section renumbering — Conditional Sections Key table updated with a 5th row; (3) fixed a live defect where the EXECUTION PAGE subtitle rendered as literal "Letter of Intent · , ," (no tokens were ever wired in) — now reads from `{{PROPERTY_STREET_ADDRESS}}`, `{{PROPERTY_CITY}}`, `{{PROPERTY_STATE_ABBR}}`; (4) fixed a punctuation defect where `{{TENANT_DISCLOSURE_PHRASE}}` examples ended in a trailing comma immediately before the template's hardcoded period, producing "...,." — corrected in both the template's Variable Reference table and this file's Decision Logic §1 table and Token Reference table; the arm's-length example now carries its own `(the "Tenant")` parenthetical since no §8 exists to define the term when the tenant is unaffiliated. Regression-tested against the 3700 Kinsman Blvd deal (arm's-length single-tenant, no ROFR, WI overlay) — output unchanged from the hand-patched original delivered that day. Template asset unreviewed by counsel prior to first live use of the new §13 conditional; flag for review before it next fires. Built platform-side; never committed to the repo until the v1.7 reconciliation above.
- v1.6 — 2026-08-16, Lost-Deal Ledger capture: new mandatory Phase 6c writes ORA's own offer terms into structured Deal Sourcing Log fields at draft time — in particular `ORA Max Defensible Price` (the first-floor-breach price, fixed at LOI time and never recomputed at outcome time). Consumed by `ora-passed-deal-tracker` Step 4b, which supplies the winning price and the basis-vs-execution `Loss Class`. Deliverables item 10 added. Origin: ORA had no structured record of any LOI loss — `Kill Reason` was populated on 1 of 20 Pipeline Tracker rows, and the one priced competitive loss on record (511 Industrial Mile, lost 2026-07-17 at $1.575M vs ORA's $1.45M) is unclassifiable because its walk price and offer contradict each other. Gabriel-ratified 2026-08-16.
- v1.4 — 2026-06-11, Deal Terms Register: new mandatory Phase 6b writes DEAL-TERMS-REGISTER.md (off-LOI terms / strategy constraints / tracking items) to the deal folder at draft and execution; consumed by deal-execution Workflow 2A and psa-reconciliation. Origin: 754 Old State easement gap.
- **v1.3 (2026-06-11) — full text: `versions/CHANGELOG-v1.0-v1.3.md`.** Composio-retirement merge; SHIP mode re-pointed to the Outlook COM sole send path. Archived 2026-09-10 to hold the 6-entry cap.
- **v1.2 / v1.1 / v1.0 — full text: `versions/CHANGELOG-v1.0-v1.3.md`** (v1.2 2026-06-10 adversarial hardening; v1.1 2026-06-10 470 McCormick calibration incl. Rule 0/0b/0c; v1.0 initial release May 2026). Archived 2026-09-10 under the retention rule above.


---

## FAILURE MODES — when NOT to use this skill

- **Owner-occupied property where ORA is selling, not buying** — wrong direction; use `deal-execution` skill for sale side
- **Refinance proposal** — use `debt-management` skill
- **Off-market lease proposal** (ORA leasing to a third party) — `re-operations` retired 2026-08-05 (redundant with named ops siblings, no direct-execution evidence); for the lease document itself, use `lease-form-qc`
- **PSA stage** — handoff to `deal-execution` skill once LOI is executed; this skill stops at LOI delivery (sole exception: Phase 6b register update to EXECUTED status when the countersigned LOI returns)

---

## OUTPUT GUARANTEES

Every successful run of this skill produces:
1. A DOCX file on ORA letterhead, 4–8 pages depending on conditionals retained
2. A PDF preview with extractable text
3. A presented file pair via `present_files`
4. A Notion log entry on the Acquisition Pipeline Tracker
5. Zero "shall" usage, zero banned phrases, full 22-point QC Gate pass
6. Phone 301.512.6125 in both top and bottom letterhead
7. Footer keyed to property street address
8. "Proof of funds available upon request." centered italic at bottom of final page
9. `DEAL-TERMS-REGISTER.md` created (or updated) in the deal folder per Phase 6b
10. Deal Sourcing Log row carries the Phase 6c Block A capture — in particular a non-NULL **`ORA Max Defensible Price`** and `LOI Outcome = PENDING`. A blank Max Defensible price means this deal can never be classified if it is lost; treat it as an incomplete deliverable, not a nice-to-have.
