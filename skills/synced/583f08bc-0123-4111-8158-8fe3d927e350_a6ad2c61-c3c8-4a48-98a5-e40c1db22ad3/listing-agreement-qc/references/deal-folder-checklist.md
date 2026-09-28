# Listing engagement deal-folder checklist

Run at Step 6 of `listing-agreement-qc`. Nine artifacts. Three are routinely
missing — marked ⚠ below with the reason they go missing.

Folder: the property deal folder. Naming follows the deal-file schema
`[Address] [Purpose] [MM-YYYY]`.

---

## Pre-execution

- [ ] **1. Listing agreement — final draft**, scanner-clean or with every
      surviving failure explicitly accepted in writing.
      `[Address] Listing Agreement [MM-YYYY].docx`

- [ ] **2. QC report** from `listing_qc.py`, with the execute / do-not-execute
      recommendation. Retain even when clean — it is the evidence the gate ran.
      `[Address] Listing Agreement Review [MM-YYYY].docx`

- [ ] **3. Excluded Prospects exhibit** (SP-2), built from the Notion Tenant
      Database and attached to the agreement itself, not filed loose.
      `[Address] Exhibit A Excluded Prospects [MM-YYYY].docx`

- [ ] ⚠ **4. Broker's agency disclosure form.**
      *Why it goes missing:* Ohio brokers routinely deliver the agency disclosure
      at the transaction rather than at engagement, and neither ORA listing
      agreement references or attaches one (R.C. 4735.53, 4735.55). Nobody asks,
      so nobody files it. **Request it in the same markup that goes back on the
      listing agreement** — see SP-8.

- [ ] **5. Parcel verification block** — county owner-of-record, site address,
      building area, acreage, class, last sale date and price. Settles the entity
      name (SP-12) and the property description (SP-13). Paste the raw query
      response, not a summary.

- [ ] **6. Encumbrance note** — lender, loan, collateral group, and whether a
      sale requires consent, defeasance, or payoff (SP-11). Query the Notion loan
      register; do not rely on memory.

## Post-execution

- [ ] ⚠ **7. Countersigned PDF** with both signatures visible.
      *Why it goes missing:* an Adobe Sign Final Audit Report evidences only the
      parties who signed **through** the Adobe transaction. On the Livingston
      agreement the audit trail shows Owner's e-signature on 2026-04-21 and
      nothing else; the broker applied a signature image dated 2026-05-04 outside
      the transaction. The audit report therefore does not evidence the broker's
      execution, and a file holding only the audit report is missing half the
      agreement. **Retain the countersigned PDF as the operative record.**

- [ ] ⚠ **8. Broker's clean base template**, archived as the compare baseline.
      *Why it goes missing:* nobody thinks to ask for it. A negotiated agreement
      arrives with the markups already baked in and no tracked changes, so the
      file carries no redline record — there is no way to see what moved off the
      broker's standard form without the standard form. Ask once per broker, and
      archive it under the broker's name rather than the deal.
      `_Broker Forms/[Broker] Base Listing Agreement [Sale|Lease] [MM-YYYY].docx`

- [ ] **9. Deal-terms register entry** — every term negotiated off the face of
      the agreement (fee exceptions, verbal exclusions, side understandings on
      the tail), tracked forward to the PSA. Same discipline as the
      `loi-generation` DEAL-TERMS-REGISTER.

---

## Calendar entries to set at execution

| Date | Entry |
|---|---|
| Primary term expiration | Listing expires — decide renew / re-bid / withdraw |
| Expiration + 10 days | **Broker prospect list due** (SP-6 condition precedent). If it does not arrive, the tail does not attach — record the non-delivery in writing. |
| Expiration + 90 days | Confirm no tail claim pending |
| Expiration + 270 days | Tail cap reached — engagement fully concluded |
| Day 90 of primary term | SP-5 termination right becomes exercisable |
