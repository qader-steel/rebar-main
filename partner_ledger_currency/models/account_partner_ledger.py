# -*- coding: utf-8 -*-
"""Safe multi-currency display patch for Odoo 19 Enterprise Partner Ledger."""

import logging

from odoo import models
from odoo.tools.misc import formatLang

_logger = logging.getLogger(__name__)

AML_ID_KEYS = ('id', 'aml_id', 'move_line_id', 'line_id')


class PartnerLedgerCurrencyHandler(models.AbstractModel):
    _inherit = 'account.partner.ledger.report.handler'

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _plc_currency_from_value(self, value):
        """Resolve a currency from common SQL-result shapes."""
        if not value:
            return self.env['res.currency']

        # Normal SQL result: integer id.
        if isinstance(value, int):
            return self.env['res.currency'].browse(value).exists()

        # Defensive handling for tuple/list values such as (id, name).
        if isinstance(value, (tuple, list)) and value:
            if isinstance(value[0], int):
                return self.env['res.currency'].browse(value[0]).exists()

        # Already a recordset.
        if getattr(value, '_name', None) == 'res.currency':
            return value[:1]

        return self.env['res.currency']

    def _plc_resolve_currency(self, row):
        """Return (currency, original_amount, aml) for one report query row.

        We first use values supplied by the Partner Ledger SQL result. If the
        result does not contain enough information, we fall back to the
        account.move.line itself. This avoids extra SQL in the normal path.
        """
        currency = self.env['res.currency']
        amount = None
        aml = self.env['account.move.line']

        if isinstance(row, dict):
            currency = self._plc_currency_from_value(row.get('currency_id'))

            if row.get('amount_currency') not in (None, False, ''):
                amount = row['amount_currency']

            aml_id = next(
                (row.get(key) for key in AML_ID_KEYS if row.get(key)),
                None,
            )
            if aml_id:
                aml = self.env['account.move.line'].browse(aml_id).exists()

        if aml:
            if not currency:
                currency = aml.currency_id or aml.company_currency_id
            if amount is None:
                amount = aml.amount_currency

        if not currency and isinstance(row, dict):
            company_id = row.get('company_id')
            if company_id:
                company = self.env['res.company'].browse(company_id).exists()
                if company:
                    currency = company.currency_id

        if not currency:
            currency = self.env.company.currency_id

        if amount in (None, False, '') and aml:
            # Odoo commonly stores 0/False for company-currency Amount Currency
            # in report output even though the accounting amount exists in
            # balance. Use the journal item balance in that specific case.
            company_currency = aml.company_currency_id or aml.company_id.currency_id
            if currency == company_currency:
                amount = aml.balance

        return currency, amount, aml

    def _plc_patch_move_line(self, line, row):
        """Fill only the standard Amount Currency cell.

        No new report column is introduced. Therefore the Enterprise report
        engine remains completely unaware of any custom expression label.
        """
        cells = line.get('columns') or []
        options_columns = self.env.context.get('_plc_options_columns') or []

        if not cells or len(cells) != len(options_columns):
            return

        currency, amount, _aml = self._plc_resolve_currency(row)
        if not currency or amount is None:
            return

        for index, column in enumerate(options_columns):
            if column.get('expression_label') != 'amount_currency':
                continue

            cell = cells[index]
            cell['no_format'] = amount

            formatted = formatLang(
                self.env,
                amount,
                currency_obj=currency,
            )
            # Make the currency explicit without changing the report schema.
            cell['name'] = '%s %s' % (formatted, currency.name)

    # ------------------------------------------------------------------
    # Override
    # ------------------------------------------------------------------

    def _get_report_line_move_line(
        self,
        options,
        aml_query_result,
        partner_line_id,
        init_bal_by_col_group,
        level_shift=0,
    ):
        line = super()._get_report_line_move_line(
            options,
            aml_query_result,
            partner_line_id,
            init_bal_by_col_group,
            level_shift=level_shift,
        )

        try:
            # Pass the current report columns without changing the shared
            # environment for any unrelated report execution.
            self = self.with_context(
                _plc_options_columns=options.get('columns') or []
            )
            self._plc_patch_move_line(line, aml_query_result)
        except Exception:
            # Display enhancement must never break the accounting report.
            _logger.exception(
                'partner_ledger_currency: could not patch Partner Ledger line'
            )

        return line
