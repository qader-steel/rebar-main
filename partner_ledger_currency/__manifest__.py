# -*- coding: utf-8 -*-
{
    'name': 'Partner Ledger - Amount in Document Currency',
    'version': '19.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Show every Partner Ledger line in the currency it was issued in',
    'description': """
Partner Ledger - Amount in Document Currency
============================================

For a company whose main currency is IQD with USD enabled as a second
currency, the standard Partner Ledger already shows the original amount of a
USD document in its "Amount Currency" column - but it leaves that column blank
for documents issued in the company currency, and it never says which currency
a figure is in.

This module:

* fills the "Amount Currency" column for EVERY line, company currency included,
  so an IQD invoice shows its dinar amount instead of an empty cell;
* adds a compact "Currency" column right before it, so 100 reads as 100 USD and
  10,000 reads as 10,000 IQD.

The Debit / Credit / Balance columns keep showing the company currency, exactly
as the general ledger has them. Partner and grand-total subtotals for the
Amount Currency column are deliberately left blank when a partner holds more
than one currency - see README.md.

Requires Odoo Enterprise (account_reports).
    """,
    'author': 'Magic Quantum',
    'depends': ['account_reports'],
    'data': [
        # 'data/partner_ledger_columns.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
