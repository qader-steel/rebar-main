# Partner Ledger - Amount in Document Currency

Odoo 19 Enterprise. Depends on `account_reports`.

## What the manager asked for

> The company's main currency is IQD, USD is enabled as a second currency, and
> in the report what is in dollars should show dollars, and what is in dinars
> should show dinars.

## What Odoo 19 already gives you for free

The standard Partner Ledger **already has an "Amount Currency" column**
(sequence 90). Verified on your own database:

| Line | Debit (IQD) | Amount Currency | Balance (IQD) |
|---|---|---|---|
| INV/2026/00001 (IQD) | 10,000 | *(blank)* | 10,000 |
| INV/2026/00002 (USD) | 155,000 | **100.0** | 165,000 |

So half the requirement is already satisfied out of the box. Show the manager
this column before doing anything else - it may be all he wanted.

## What this module adds

1. **Fills Amount Currency for company-currency lines too.** The IQD invoice
   above shows `10,000` instead of an empty cell. This is the literal
   "and dinars show dinars" half of the request.
2. **Adds a "Currency" column** (sequence 85, right before Amount Currency), so
   `100` reads unambiguously as `100 USD`.

Result:

| Line | Debit (IQD) | Currency | Amount Currency | Balance (IQD) |
|---|---|---|---|---|
| INV/2026/00001 | 10,000 | IQD | 10,000 | 10,000 |
| INV/2026/00002 | 155,000 | USD | 100.00 | 165,000 |

## What it deliberately does NOT do

**Debit / Credit / Balance keep showing IQD.** They are the general-ledger
figures at the historical rate; the accountants and the balance sheet depend on
them. The document currency is shown alongside, not instead.

**Partner and grand-total rows leave Amount Currency blank.** This is Odoo's own
behaviour and it is correct: a partner holding 100 USD and 10,000 IQD has no
single meaningful "amount in currency" total. 100 USD + 10,000 IQD is not a
number. If the manager wants per-currency subtotals, that is a bigger change -
one row per (partner, currency) - and should be a separate decision.

## Install

```bash
# put the folder next to your other addons, then on a STAGING branch first:
#   Apps -> Update Apps List -> install "Partner Ledger - Amount in Document Currency"
```

Or from the shell:

```bash
odoo-bin -d <database> -i partner_ledger_currency --stop-after-init
```

Then: Accounting -> Reporting -> Partner Ledger, unfold a partner.

## If something goes wrong

The module is written so it cannot break the report: every override calls
`super()` first and patches the result inside a `try/except` that logs and
returns the untouched line.

The only structural change is the added column. If that ever misbehaves:

1. remove `'data/partner_ledger_columns.xml'` from `__manifest__.py`
2. upgrade the module

You keep the filled-in Amount Currency figures; you lose only the Currency
label. The two features are independent.

To see what the report is handing the module, turn on debug logging:

```
--log-handler odoo.addons.partner_ledger_currency:DEBUG
```

## Tests

```bash
odoo-bin -d <db> -i partner_ledger_currency --test-enable \
         --test-tags /partner_ledger_currency --stop-after-init
```

Four tests, on a company with IQD as main currency and USD as second:
the column installs, **the report still renders with the right cell count**
(the one that matters), every line shows its own currency and amount, and
Debit/Credit remain in company currency.
