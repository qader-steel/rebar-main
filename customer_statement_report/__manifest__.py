# -*- coding: utf-8 -*-
{
    'name': 'Customer Statement Report',
    'version': '19.0.2.0.0',
    'category': 'Accounting',
    'summary': 'Multi-currency customer / vendor statement with product details',
    'description': """
Customer / Vendor Statement Report
==================================

Prints a partner statement with the product detail of every invoice.

Multi-currency
--------------
The statement is split into one section per currency.  Each section shows its
own opening balance, debit / credit totals and closing balance, expressed in
the currency the documents were actually issued in - a USD invoice is shown in
USD, an IQD invoice in IQD.  Currencies are never summed together inside a
running balance.

When a partner has more than one currency, a consolidated total is added in the
company currency, taken from the general ledger amounts (historical rates).
    """,
    'author': 'Magic Quantum',
    'depends': ['account'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/customer_statement_wizard_views.xml',
        'view/account_move_line_view.xml',
        'report/customer_statement_report.xml',
        'report/customer_statement_templates.xml',
    ],
    'installable': True,
    'license': 'LGPL-3',
}
