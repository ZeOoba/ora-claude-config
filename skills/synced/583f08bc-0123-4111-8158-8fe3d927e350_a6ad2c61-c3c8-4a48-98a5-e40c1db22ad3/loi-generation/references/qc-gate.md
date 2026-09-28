# 22-Point QC Gate — LOI Pre-Transmission Checklist

This gate runs after document assembly and before the file is presented or shipped. Every item must pass; if any fails, fix and re-run. Do not present a failing file.

| # | Check | How to verify |
|---|---|---|
| 1 | All `{{TOKENS}}` resolved; no gold sans-serif placeholders remain in body | Grep PDF text for `\{\{[A-Z_]+\}\}` — must return zero |
| 2 | All `▶ CONDITIONAL ◀` blocks evaluated; markers removed | Grep PDF text for `CONDITIONAL` — must return zero |
| 3 | §6 language matches property state | Confirm state-specific transfer-tax / proration language present |
| 4 | Section numbering sequential; non-binding paragraph cross-references match retained sections | Read non-binding paragraph; verify each `§N` cited exists |
| 5 | Template Metadata page deleted; State Overlay Appendix deleted | Confirm document starts with letterhead + date and ends with proof-of-funds page |
| 6 | Tenancy disclosure in opening paragraph matches `{{PROPERTY_TENANCY_PHRASE}}` | Read intro; verify "vacant" / "single-tenant" / "multi-tenant" matches the deal |
| 7 | Economic terms within ORA acceptable ranges | EMD, Study Period, Closing, Exclusivity all within ranges in `ora-standards.md` |
| 8 | Buyer signatory matches user instruction | Execution page reads "Gabriel Goldberg / Authorized Representative" (or override) |
| 9 | Letterhead phone reads **301.512.6125** in both top and bottom letterhead tables | Grep PDF for `301.983.8000` — must return zero; grep for `301.512.6125` — must return ≥2 |
| 10 | Footer reads `[PROPERTY_STREET_ADDRESS] LOI · Page X of Y` with PAGE/NUMPAGES fields | Visual inspection of any page footer |
| 11 | "Proof of funds available upon request." appears centered, italic, grey on the very last page, lower third | Visual inspection of last page; grep for "Proof of funds available upon request" — must return exactly 1 |
| 12 | Tenant count in BUYER INFORMATION trailer reads "approximately 140 tenants" | Grep PDF for "170 tenants" — must return zero; grep for "140 tenants" — must return 1 |
| 13 | Offer expiration date is a business day at least 5 business days from LOI date | Calendar arithmetic |
| 14 | EXECUTION PAGE present with Buyer block populated, Seller entity name filled | Visual inspection |
| 15 | Strike list clean | Grep for `\bshall\b` (excluding "shallow") — must return zero. Grep for each banned phrase — must return zero |
| 16 | PDF generated via `soffice` (not Microsoft Print to PDF); extractable text confirmed | `pdftotext` round-trip yields readable text |
| 17 | Pagination: Buyer Information page starts its own page (page_break_before on its heading, never stacked empty paragraphs); proof-of-funds line sits on the final page lower third; page count = 5 (CONDENSED) or 6–8 (STANDARD) | Visual inspection; strip empty/page-break-before paragraph runs during assembly — known template defect otherwise renders 7–8 pages |
| 18 | Entity-interest language matches seller suffix (Rule 0) | "membership interests" must never ship against an Inc/Corp seller |
| 19 | Zoning phrase matches the OM verbatim | Compare `{{PROPERTY_ZONING_PHRASE}}` against source OM/listing text |
| 20 | If concealment overlay active (Rule 0c): leak-check confirms zero occurrences of "1031" / "exchange" / "drop-and-swap" | Grep final document text for each term — must return zero |
| 21 | Deposit-timing consistency: all Deposit due-window mentions resolve from `{{EMD_DUE_DAYS_WORDS}}` and are identical in the final text | Grep for every deposit-due mention; confirm same value throughout |
| 22 | Vacant deals: preservation covenant present; casualty threshold "five percent (5%) of the Purchase Price" survived CONDENSED compression | Visual inspection of Continued Operations / Casualty sections |

---

## Strike list (full)

Phrases that must NOT appear anywhere in the body:

- `shall` (replace with "will")
- `I hope this finds you well`
- `Just following up`
- `As discussed`
- `FYI`
- `Going forward`
- `At your earliest convenience`
- `Hopefully`
- `I think we should`
- `Quick question`
- `Sorry for the delay`
- `Notwithstanding the foregoing` (replace with "However")
- `Pursuant to` (replace with "under" or drop)
- `Hereunder`, `hereof`, `thereof`, `thereunto` (drop)
- `Without limitation` (replace with "including" or drop)
- `Subject to` (drop where meaning survives)

---

## Verification helper script

```python
# qc_gate.py — run after document save
import re
from pathlib import Path
import subprocess

def run_qc(pdf_path: Path) -> dict:
    text = subprocess.run(["pdftotext", str(pdf_path), "-"], capture_output=True, text=True).stdout
    results = {}
    # 1. No tokens
    results["tokens_resolved"] = len(re.findall(r"\{\{[A-Z_]+\}\}", text)) == 0
    # 2. No conditional markers
    results["conditionals_removed"] = "CONDITIONAL" not in text
    # 9. Phone
    results["phone_correct"] = "301.983.8000" not in text and text.count("301.512.6125") >= 2
    # 11. Proof of funds appears exactly once at end
    results["proof_of_funds_once"] = text.count("Proof of funds available upon request") == 1
    # 12. Tenant count
    results["tenant_count_140"] = "170 tenants" not in text and "140 tenants" in text
    # 15. Strike list
    shall_hits = re.findall(r"\bshall\b", text, re.IGNORECASE)
    results["no_shall"] = len(shall_hits) == 0
    banned = ["I hope this finds you well", "Just following up", "As discussed",
              "FYI", "Going forward", "At your earliest convenience", "Hopefully",
              "I think we should", "Quick question", "Sorry for the delay",
              "Notwithstanding the foregoing"]
    results["no_banned_phrases"] = not any(b in text for b in banned)
    return results
```
