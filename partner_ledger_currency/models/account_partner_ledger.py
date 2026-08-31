# -*- coding: utf-8 -*-
"""Per-currency display and per-partner currency totals for Odoo 19 Partner Ledger."""

import logging

from odoo import models, _
from odoo.tools import SQL
from odoo.tools.misc import formatLang

_logger = logging.getLogger(__name__)

AML_ID_KEYS = ('id', 'aml_id', 'move_line_id', 'line_id')


class PartnerLedgerCurrencyHandler(models.AbstractModel):
    _inherit = 'account.partner.ledger.report.handler'

    # ------------------------------------------------------------------
    # Helpers: line currency / amount
    # ------------------------------------------------------------------

    def _plc_currency_from_value(self, value):
        """Resolve a currency record from common SQL-result shapes."""
        if not value:
            return self.env['res.currency']

        if isinstance(value, int):
            return self.env['res.currency'].browse(value).exists()

        if isinstance(value, (tuple, list)) and value and isinstance(value[0], int):
            return self.env['res.currency'].browse(value[0]).exists()

        if getattr(value, '_name', None) == 'res.currency':
            return value[:1]

        return self.env['res.currency']

    def _plc_resolve_currency(self, row):
        """Return (currency, original_amount, aml) for one Partner Ledger AML row."""
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

        # For company-currency lines Odoo may return an empty Amount Currency
        # cell even though the accounting amount is present in balance.
        if amount in (None, False, '') and aml:
            company_currency = aml.company_currency_id or aml.company_id.currency_id
            if currency == company_currency:
                amount = aml.balance

        return currency, amount, aml

    def _plc_format_currency_amount(self, amount, currency):
        """Format the amount WITHOUT the currency symbol.

        The currency code is appended explicitly, so the result is e.g.
        ``100.00 USD`` or ``10,000.000 IQD`` instead of ``$ 100.00 USD`` or
        ``10,000.000 ع.د IQD``.
        """
        return '%s %s' % (
            formatLang(
                self.env,
                amount,
                digits=currency.decimal_places,
                monetary=False,
            ),
            currency.name,
        )

    def _plc_patch_move_line(self, options, line, row):
        """Fill the standard Amount Currency cell without changing the report schema."""
        cells = line.get('columns') or []
        option_columns = options.get('columns') or []

        if not cells or len(cells) != len(option_columns):
            return

        currency, amount, _aml = self._plc_resolve_currency(row)
        if not currency or amount is None:
            return

        for index, column in enumerate(option_columns):
            if column.get('expression_label') != 'amount_currency':
                continue

            cell = cells[index]
            cell['no_format'] = amount
            cell['name'] = self._plc_format_currency_amount(amount, currency)

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
            self._plc_patch_move_line(options, line, aml_query_result)
        except Exception:
            # This is display-only enhancement; never break the accounting report.
            _logger.exception(
                'partner_ledger_currency: could not patch Partner Ledger line'
            )

        return line

    # ------------------------------------------------------------------
    # Per-partner currency totals
    # ------------------------------------------------------------------

    def _report_expand_unfoldable_line_partner_ledger(
        self,
        line_dict_id,
        groupby,
        options,
        progress,
        offset,
        unfold_all_batch_data=None,
    ):
        """Append one Amount Currency total row per currency for each partner."""
        result = super()._report_expand_unfoldable_line_partner_ledger(
            line_dict_id,
            groupby,
            options,
            progress,
            offset,
            unfold_all_batch_data=unfold_all_batch_data,
        )

        try:
            report = self.env['account.report'].browse(options['report_id'])
            parsed = report._parse_line_id(line_dict_id)
            if not parsed:
                return result

            _markup, _model, partner_id = parsed[-1]

            # Only add totals once the normal AML expansion for this partner is
            # complete. Otherwise pagination could duplicate the subtotal.
            if result.get('has_more'):
                return result

            with self.env.cr.savepoint():
                currency_data = report._compute_amount_currency_by_partner(options)

            partner_currency_data = currency_data.get(partner_id, {})

            for currency_id, amount in sorted(partner_currency_data.items()):
                if not amount:
                    continue

                currency = self.env['res.currency'].browse(currency_id).exists()
                if not currency:
                    continue

                columns = []
                for col in options.get('columns', []):
                    expression_label = col.get('expression_label')

                    if expression_label == 'amount_currency':
                        columns.append({
                            'name': self._plc_format_currency_amount(amount, currency),
                            'no_format': amount,
                            'expression_label': 'amount_currency',
                            'figure_type': 'string',
                            'class': 'number',
                        })
                    else:
                        columns.append({
                            'name': '',
                            'no_format': None,
                            'expression_label': expression_label,
                            'figure_type': 'string',
                        })

                result.setdefault('lines', []).append({
                    'id': report._get_generic_line_id(
                        None,
                        None,
                        parent_line_id=line_dict_id,
                        markup='currency_total_%s' % currency_id,
                    ),
                    'name': _('%s Total') % currency.name,
                    'level': 3,
                    'columns': columns,
                    'class': 'o_account_report_total custom-currency-total',
                })

        except Exception:
            # A subtotal is non-critical. The savepoint above prevents a failed
            # aggregation query from leaving the outer Odoo transaction aborted.
            _logger.exception(
                'partner_ledger_currency: could not append currency totals'
            )

        return result


class AccountReportCurrencyTotals(models.Model):
    _inherit = 'account.report'

    def _get_query_amount_currency_sums(self, options) -> SQL:
        """Build the currency-total query using the Partner Ledger report domain."""
        queries = []

        for column_group_key, column_group_options in self._split_options_per_column_group(options).items():
            query = self._get_report_query(column_group_options, 'from_beginning')
            queries.append(SQL(
                """
                SELECT
                    account_move_line.partner_id AS groupby,
                    account_move_line.currency_id AS currency_id,
                    %s AS column_group_key,
                    COALESCE(SUM(account_move_line.amount_currency), 0.0) AS amount_currency
                FROM %s
                WHERE %s
                  AND account_move_line.partner_id IS NOT NULL
                  AND account_move_line.currency_id IS NOT NULL
                GROUP BY account_move_line.partner_id, account_move_line.currency_id
                """,
                column_group_key,
                query.from_clause,
                query.where_clause,
            ))

        return SQL(' UNION ALL ').join(queries)

    def _compute_amount_currency_by_partner(self, options):
        """Return {partner_id: {currency_id: amount}} for the report scope."""
        query = self._get_query_amount_currency_sums(options)
        self.env.cr.execute(query)
        rows = self.env.cr.dictfetchall()

        data = {}
        for row in rows:
            partner_id = row.get('groupby')
            currency_id = row.get('currency_id')
            amount = float(row.get('amount_currency') or 0.0)
            if not partner_id or not currency_id:
                continue
            data.setdefault(partner_id, {})
            data[partner_id][currency_id] = (
                data[partner_id].get(currency_id, 0.0) + amount
            )

        return data
