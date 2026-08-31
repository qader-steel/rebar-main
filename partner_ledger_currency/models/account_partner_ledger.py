# -*- coding: utf-8 -*-
"""
Partner Ledger - show every document in the currency it was issued in.

What Odoo 19 already does
-------------------------
The standard Partner Ledger already carries an "Amount Currency" column
(sequence 90).  For a document issued in a foreign currency it shows the
original amount, e.g. a 100 USD invoice booked at 155,000 IQD displays:

    Debit = 155,000     Amount Currency = 100

What it does NOT do, and what this module adds
----------------------------------------------
1. For a document issued in the COMPANY currency the Amount Currency cell is
   left blank, so an IQD invoice shows nothing there.  The manager asked for
   "dollars shown in dollars AND dinars shown in dinars", so we fill it for
   every line.

2. There is nothing telling you WHICH currency the number is in - "100" on its
   own is ambiguous.  We add a small "Currency" column next to it.

Deliberately NOT changed
------------------------
The subtotal on the partner row and on the grand-total row is left blank, the
way Odoo leaves it.  That is not a bug: a partner holding both USD and IQD
lines has no single meaningful "amount in currency" total - 100 USD + 10,000
IQD is not a number.  See README.md.

Safety
------
Every override calls super() first and then patches the result.  If anything
unexpected happens the exception is logged and the ORIGINAL, untouched line is
returned, so this module can never break the report.
"""

import logging

from odoo import models
from odoo.tools.misc import formatLang

_logger = logging.getLogger(__name__)

# Keys the aml query row might use for the journal item id, in order of
# likelihood. Kept as a tuple so a future Odoo rename is a one-line fix.
AML_ID_KEYS = ('id', 'aml_id', 'move_line_id', 'line_id')

CURRENCY_COLUMN_LABEL = 'currency_name'


class PartnerLedgerCurrencyHandler(models.AbstractModel):
    _inherit = 'account.partner.ledger.report.handler'

    # ------------------------------------------------------------------
    # HELPERS
    # ------------------------------------------------------------------

    def _plc_resolve_currency(self, row):
        """Return (currency, amount_currency) for one journal-item query row.

        Tries the query row first (no extra SQL), and falls back to reading the
        journal item itself if the row does not carry what we need.
        """
        currency = self.env['res.currency']
        amount = None

        if isinstance(row, dict):
            currency_id = row.get('currency_id')
            if currency_id:
                currency = self.env['res.currency'].browse(currency_id)

            if row.get('amount_currency') not in (None, False, ''):
                amount = row['amount_currency']

            if not currency or amount is None:
                aml_id = next(
                    (row[key] for key in AML_ID_KEYS if row.get(key)), None,
                )
                if aml_id:
                    aml = self.env['account.move.line'].browse(aml_id).exists()
                    if aml:
                        if not currency:
                            currency = aml.currency_id
                        if amount is None:
                            amount = aml.amount_currency

        return currency, amount

    def _plc_column_index(self, options, expression_label):
        """Positions of a column, by expression label.

        A report can repeat its columns once per column group (period
        comparison), so this returns every matching position.
        """
        return [
            index
            for index, column in enumerate(options.get('columns') or [])
            if column.get('expression_label') == expression_label
        ]

    def _plc_patch_move_line(self, options, line, row):
        """Fill in the Currency and Amount Currency cells of one line."""
        cells = line.get('columns') or []
        option_columns = options.get('columns') or []

        if len(cells) != len(option_columns):
            # The engine built a different number of cells than we expect;
            # do not guess, leave the line exactly as Odoo produced it.
            _logger.debug(
                "partner_ledger_currency: %s cells for %s columns, skipping",
                len(cells), len(option_columns),
            )
            return

        currency, amount = self._plc_resolve_currency(row)

        # ---- the "Currency" column ------------------------------------
        for index in self._plc_column_index(options, CURRENCY_COLUMN_LABEL):
            cells[index]['name'] = currency.name or ''
            cells[index]['no_format'] = currency.name or ''

        # ---- the standard "Amount Currency" column --------------------
        # Odoo blanks it for company-currency lines; fill it in.
        for index in self._plc_column_index(options, 'amount_currency'):
            cell = cells[index]
            if cell.get('no_format') not in (None, False, ''):
                continue  # a foreign-currency amount is already there
            if amount in (None, False):
                continue
            cell['no_format'] = amount
            cell['name'] = formatLang(
                self.env, amount, currency_obj=currency or None,
            )

    # ------------------------------------------------------------------
    # OVERRIDES
    # ------------------------------------------------------------------

    def _get_report_line_move_line(self, options, aml_query_result,
                                   partner_line_id, init_bal_by_col_group,
                                   level_shift=0):
        line = super()._get_report_line_move_line(
            options, aml_query_result, partner_line_id,
            init_bal_by_col_group, level_shift=level_shift,
        )
        try:
            self._plc_patch_move_line(options, line, aml_query_result)
        except Exception:  # never break the report over a display detail
            _logger.exception(
                "partner_ledger_currency: could not patch a journal item line"
            )
        return line

    def _get_aml_values(self, options, partner_ids, offset=0, limit=None):
        """Log the query row shape once, so the module is easy to diagnose."""
        results = super()._get_aml_values(
            options, partner_ids, offset=offset, limit=limit,
        )
        if _logger.isEnabledFor(logging.DEBUG):
            sample = results
            if isinstance(results, dict):
                sample = next(iter(results.values()), None)
            if isinstance(sample, (list, tuple)) and sample:
                _logger.debug(
                    "partner_ledger_currency: aml row keys = %s",
                    sorted(sample[0].keys())
                    if isinstance(sample[0], dict) else type(sample[0]),
                )
        return results
