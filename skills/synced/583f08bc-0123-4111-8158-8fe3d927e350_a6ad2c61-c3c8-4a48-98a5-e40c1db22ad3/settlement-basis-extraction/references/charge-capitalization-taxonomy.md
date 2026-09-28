# Closing-Charge Capitalization Taxonomy

Reference for tagging CHARGE_DETAIL lines. This is a working default, not
tax advice -- confirm entity-specific treatment with the preparer before an
IC memo or return relies on a tag.

## Capitalizable to basis (acquisition costs -- Reg. 1.263(a)-2)

- Title insurance premiums (owner's policy)
- Title examination / settlement / closing fees
- Recording fees (deed)
- Transfer taxes / conveyance fees / deed recordation tax (state + county +
  city, all splits)
- Survey costs
- Attorney fees directly tied to the purchase (not general corporate)
- Real estate commission, if paid by buyer (rare; confirm who bears it on
  the specific settlement -- usually seller-paid and reduces seller
  proceeds, not buyer basis)
- Environmental / engineering / PCA reports paid at closing as a condition
  of purchase

## NOT capitalizable -- expense or separately tracked

- Loan origination fees, points, appraisal/credit-report/flood-cert fees,
  and other lender-required charges tied to financing (these amortize over
  the loan term as a separate intangible, not basis)
- Prorated rent, security deposit transfers, and other operating prorations
  (these are working-capital items between buyer and seller, not basis)
- Prorated property taxes (adjust the buyer's first-year tax expense, not
  basis, UNLESS the proration represents taxes for a period the buyer did
  not own the property -- confirm direction before tagging)
- Recording fees on a mortgage/deed of trust (financing cost, not
  acquisition cost)
- Homeowners/hazard insurance premiums or escrow deposits at closing

## Needs a specific facts-and-circumstances call -- do not auto-tag

- Buyer's attorney fee, if the invoice bundles acquisition and financing
  work -- ask for a split, or tag capitalizable by default and flag in
  EXCEPTIONS for preparer confirmation
- Zoning letters, lien searches, UCC searches -- typically capitalizable if
  a condition of purchase, expense if routine due diligence unrelated to
  closing the specific transaction
- Qualified Intermediary (1031) fees -- capitalize to the replacement
  property's basis, not the relinquished property's disposition costs

## Reminders specific to this portfolio

- If the settlement shows a $0 or blank land line with the entire debit
  total flowing to one basis bucket, do NOT tag all of it capitalizable-to-
  improvements without a land/improvement split. Flag in EXCEPTIONS: "needs
  assessor ratio or appraisal split" and leave BASIS_REGISTER's land column
  blank rather than $0.
- Franklin County OH and Baltimore City/County MD both publish
  land/improvement assessment ratios that can back into a reasonable split
  when no appraisal exists -- cite the source (auditor site + as-of date) if
  used, and mark the resulting basis split as **derived**, not transcribed.
