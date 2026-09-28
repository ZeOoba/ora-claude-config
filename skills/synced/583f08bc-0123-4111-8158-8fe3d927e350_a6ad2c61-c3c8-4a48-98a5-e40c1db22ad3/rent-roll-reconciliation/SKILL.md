---
name: rent-roll-reconciliation
description: Reconcile the Oxford Realty Advisors Notion Tenant Database against an authoritative rent roll export (xlsx), correcting property/suite mistags, filling missing SF/rent/lease-date/escalation fields, retiring phantom or duplicate tenant records, and creating records for genuine gaps. Use whenever the user uploads a rent roll and says it's correct / authoritative and anything that doesn't match should be fixed, or asks to reconcile, audit, true-up, or sync the Tenant Database against a rent roll, master workbook, or PM export. Also trigger on "rent roll reconciliation," "true up the tenant DB," "does the rent roll match Notion," or after any monthly/quarterly rent roll refresh. This is a whole-portfolio pass (all properties, all tenants) — do not treat it as a single-tenant lookup task (use verified-deal-recon or a plain search for that instead).
---

# Rent Roll Reconciliation

## Why this exists

A full reconciliation touches every property and every tenant in the portfolio. Done ad hoc, it turns into 150+ individual manual writes with no consistent method for telling "this tenant is genuinely new/gone" from "this tenant's property tag is just wrong" from "this is a duplicate of a tenant that already exists somewhere else." Those three situations look identical from a single record in isolation — a tenant with no rent-roll match could be a phantom, an out-of-scope property, or a mistagged real tenant. Getting the categorization wrong is the expensive mistake: it either destroys a real tenant's data or leaves stale/duplicate data in place.

The single costliest failure mode observed in practice: correcting a property tag based only on plausible string-matching against the rent roll's bare property label (e.g. "2207 Northwood"), without checking the actual system of record for which state/market that property is in. A rent roll's property column is usually just a street name — it will not disambiguate "2203-2207 Northwood — Columbus OH" from "2203-2207 Northwood Dr — Salisbury MD" if both exist as enum options. Guessing wrong here silently corrupts every tenant at that property, and because the wrong guess still "matches" the rent roll's SF/rent/dates, nothing in the reconciliation process itself will catch the error. The only reliable check is cross-referencing the **Property Register** (sourced from the Master Workbook's Property NOI tab) or HubSpot, which carry the market/state independent of the rent roll. Treat this cross-check as mandatory, not optional, for every property whose enum options could plausibly be confused (same street name across markets, similarly-named nearby properties, etc.) — not just the ones that look ambiguous at a glance, since the whole point is that they don't look ambiguous until you check.

## Prerequisites

- The rent roll file (xlsx). Confirm with the user that it's authoritative before treating any mismatch as ground truth — this skill assumes an explicit statement like "the rent roll is correct, fix anything that doesn't match."
- Read access to the Notion Tenant Database and, if it exists, the Property Register / Property NOI source.
- `notion-query-data-sources` (SQL mode) is far faster than per-record search+fetch for a whole-portfolio pass. It is rate-limited on non-Business Notion plans and will intermittently return `entitlement_required`. Don't wait around for it — fall back to `notion-search` + `notion-fetch` per record when it's down, and retry the SQL path later in the same session; it tends to come back.

## Procedure

### 1. Parse the rent roll into a clean structure

Use `scripts/parse_rent_roll.py` (adjust the header row / column order to match — rent rolls from different property managers vary). Normalize into records with: property, suite/unit, contact, company, SF, monthly rent, lease start/end, escalation date/%, status. Save as JSON so every later step can re-read it cheaply instead of re-parsing the spreadsheet.

Expect a totals row and possibly a lone vacancy row mixed into the data — filter them out (or handle explicitly) rather than letting them pollute the tenant count.

### 2. Pull the full live Tenant Database

Query for all non-retired records (`"Row Retired" IS NULL OR "Row Retired" = '__NO__'`), selecting only the fields you need (id, tenant name/title, property, suite, SF, rent, lease start/end, escalation date/%, retired flag). `SELECT *` on a 100+ row database will blow the token limit — always project just the columns this task needs.

If the query tool is rate-limited, page through `notion-search` + `notion-fetch` results instead, or pull property-by-property with `LIKE` filters once the tool is back, whichever is available. Save the combined result as JSON, same reasoning as step 1: cheap to re-diff without re-fetching.

### 3. Get the authoritative property list before touching any property tags

Before reconciling anything, fetch or query the Property Register (or equivalent Master-Workbook-sourced property list) for the full set of properties, their markets/states, and expected tenant counts. This is your ground truth for property identity — the rent roll only tells you SF/rent/dates matched to a bare property label, not which enum option is correct when more than one plausibly matches. If no Property Register exists, at minimum spot-check HubSpot Address or an executed lease/addendum for any property whose name could collide across markets before mass-editing its tenants' Property Address field.

### 4. Match rent roll rows to Notion records

Fuzzy-match on contact/company name tokens (normalize case, strip legal suffixes like LLC/Inc/Corp, strip punctuation) rather than requiring exact string equality — tenant names drift between systems (nicknames, DBA vs. legal entity, contact name vs. company name). For each rent-roll row, look for a Notion record whose tenant name shares a token. Don't stop at the first plausible substring match if two different tenants share a common word (e.g. "Bay Area") — corroborate with SF/rent before accepting a match, especially across properties.

This produces four buckets, plus a fifth exception bucket:
- **Matched, fields agree** — nothing to do.
- **Matched, fields differ** — SF/rent/dates/escalation need updating to the rent roll's values, and/or the property/suite tag is wrong (see step 5 for how to tell which).
- **Notion record with no rent-roll match** — could be a phantom/stale/duplicate record, or a tenant at a property the rent roll doesn't cover at all (see step 6 — don't assume "no match" means "delete").
- **Rent-roll row with no Notion record** — a genuine gap; confirm before creating (see step 7).
- **Ambiguous** — 2+ rent-roll rows corroborated equally, a name-token hit whose SF/rent corroboration was attempted but disagreed, or a candidate already claimed by an earlier Notion record in the same run. `diff_tenants.py` reports these separately and never auto-applies them — resolve each by hand the same way step 5 resolves a property/suite mismatch, using SF/rent/property as the deciding evidence. (A single distinctive name-token hit where NEITHER side has any SF/rent data to corroborate against is instead accepted as a "matched, unverified" record — there is no corroborating evidence to defer to, and these are exactly the sparsest records this reconciliation exists to fill in — but it's flagged with a note so you know the match itself was never corroborated.)

### 5. Diagnosing property/suite mismatches specifically

When a Notion record's SF and rent match a rent-roll row exactly but the property tag doesn't, that's strong evidence the record itself is the right tenant, just filed under the wrong property — correct the tag, don't create a new record and don't retire the old one. This is the most common real-world error and it compounds: a property that has been fully migrated to the wrong enum option can end up with every one of its tenants tagged wrong, which looks superficially like "this whole property has no rent-roll coverage" if you're not checking property-by-property.

To catch a systemic mistag (a whole property under a wrong tag), don't just check the properties the rent roll's tenants say they're at — also check for extra live Notion records already sitting under any candidate wrong tag, and reconcile the counts. If the rent roll says a property has 31 tenants and querying that exact enum value only returns 1, the other 30 are very likely sitting under a similarly-named wrong option.

For buildings split across multiple Property Address options by suite-number range (e.g. a strip of units 2800–2826 filed under two different addresses depending on which half of the building), don't guess the split point — query the suites that are *already* correctly tagged on each side and find where the boundary actually falls before assigning an ambiguous suite to either side.

### 6. Retiring vs. leaving alone vs. reassigning "no rent-roll match" records

Before setting `Row Retired: __YES__` on anything, work through this in order:

1. **Does a live counterpart already exist under a different name/spelling for the same tenant?** If so, this record is the duplicate — retire it, don't touch the live one. Search by name before concluding "no match."
2. **Does this record's Property Address fall outside what the rent roll covers at all** (a market/property the rent roll's source genuinely doesn't include — check the rent roll's own property list against the full portfolio)? If so, leave it alone. Absence from an incomplete source is not evidence of a bad record, and retiring good data because the source document didn't cover it is a worse error than leaving stale data in place.
3. **Does it have no Property Address, a name that doesn't match anything in the rent roll under any reasonable normalization, and no corroborating detail (dates/SF that tie it to a real suite)?** That's a phantom/placeholder record — safe to retire.
4. **Is it a specialty income line** (cell tower, billboard, rooftop, parking) that might legitimately not appear in a per-suite rent roll? Don't retire on absence alone; check if the rent roll has an equivalent line elsewhere (e.g. an ancillary-income section) before deciding.

**Never retire one side of a suspected duplicate pair without first confirming a live counterpart actually exists and carries correct data.** It is easy to retire the wrong one, or to retire the only copy while believing a survivor exists. Before writing `Row Retired: __YES__`, fetch or query for the counterpart by name and confirm its current `Row Retired` value and that its fields are populated — don't rely on memory of what "should" be live from earlier in the session. This exact mistake — retiring both halves of a duplicate pair and leaving zero live records for a real, currently-paying tenant — has happened before and is a material revenue-tracking gap, not a cosmetic one.

### 7. Creating new records for true gaps

Only create a new Tenant Database record when you've exhausted steps 4–6 and a rent-roll row still has no plausible Notion counterpart anywhere in the portfolio (not just at the property the rent roll names). Populate every field the rent roll gives you, and note in the record that it was created from this reconciliation with the source file name and date.

### 8. Batch the writes, verify, then re-run the match

Execute corrections in parallel batches (property/suite fixes, then field fills, then retirements, then creates — roughly in that order of risk, cheapest-to-verify first). Notion API calls occasionally time out under load; retry a failed call once before assuming it didn't apply.

When done, re-run the property-level counts from step 3 (rent-roll tenant count per property vs. live Notion count per property) to confirm they now match. A clean reconciliation ends with every property's live tenant count equal to its rent-roll count, plus only the specialty/out-of-scope exceptions you explicitly decided to leave.

## Output

Report back: total records corrected / retired / created, grouped by what kind of fix (property/suite reassignment, field fill, mismatch correction, phantom retirement, gap creation), and specifically call out anything from step 6.2 (out-of-scope properties left alone) and step 6.1/duplicate-pair cases so the user can sanity-check the judgment calls, not just the mechanical ones.
