# -*- coding: utf-8 -*-
"""
Tests for the Partner Ledger currency columns.

Run on Odoo.sh (automatic on a staging build) or locally:

    odoo-bin -d <db> -i qader_steel_suite --test-enable \\
             --test-tags /qader_steel_suite --stop-after-init

Mirrors the client's setup: company currency IQD, USD enabled as a second
currency, one partner holding documents in both.
"""

from odoo import Command, fields
from odoo.tests import tagged
from odoo.addons.account.tests.common import AccountTestInvoicingCommon

# 1 IQD expressed in USD, i.e. 1 USD = 1,550 IQD (the rate seen in the
# client's own data: a 100 USD invoice booked at 155,000 IQD).
USD_PER_IQD = 1.0 / 1550.0


@tagged('post_install', '-at_install')
class TestPartnerLedgerCurrency(AccountTestInvoicingCommon):

    @classmethod
    def setup_independent_company(cls, **kwargs):
        iqd = cls.env['res.currency'].with_context(active_test=False).search(
            [('name', '=', 'IQD')], limit=1,
        )
        iqd.action_unarchive()
        return super().setup_independent_company(currency_id=iqd.id, **kwargs)

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.iqd = cls.env.company.currency_id
        cls.usd = cls.setup_other_currency(
            'USD', rates=[('2020-01-01', USD_PER_IQD)],
        )

        cls.report = cls.env.ref('account_reports.partner_ledger_report')
        cls.handler = cls.env[cls.report.custom_handler_model_name]

        cls.inv_iqd = cls._invoice('2026-01-10', cls.iqd, 10000.0)
        cls.inv_usd = cls._invoice('2026-01-20', cls.usd, 100.0)

    @classmethod
    def _invoice(cls, date, currency, amount):
        move = cls.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': cls.partner_a.id,
            'invoice_date': date,
            'date': date,
            'currency_id': currency.id,
            'invoice_line_ids': [Command.create({
                'product_id': cls.product_a.id,
                'quantity': 1,
                'price_unit': amount,
                'tax_ids': [Command.clear()],
            })],
        })
        move.action_post()
        return move

    # ------------------------------------------------------------------

    def _options(self):
        return self.report.get_options({
            'selected_variant_id': self.report.id,
            'partner_ids': [self.partner_a.id],
            'unfold_all': True,
            'date': {
                'mode': 'range',
                'filter': 'custom',
                'date_from': '2026-01-01',
                'date_to': '2026-12-31',
            },
        })

    def _cell(self, options, line, expression_label):
        for index, column in enumerate(options['columns']):
            if column.get('expression_label') == expression_label:
                return line['columns'][index]
        return None

    def _move_lines(self, options, lines):
        """Only the journal-item rows (they carry a journal code)."""
        out = []
        for line in lines:
            cell = self._cell(options, line, 'journal_code')
            if cell and cell.get('no_format'):
                out.append(line)
        return out

    # ------------------------------------------------------------------

    def test_01_currency_column_is_installed(self):
        column = self.report.column_ids.filtered(
            lambda c: c.expression_label == 'currency_name'
        )
        self.assertTrue(column, "the Currency column was not added")
        self.assertEqual(column.figure_type, 'string')
        self.assertEqual(column.name, 'Currency')

    def test_02_report_still_renders(self):
        """The most important test: adding a column must not break anything."""
        options = self._options()
        lines = self.report._get_lines(options)
        self.assertTrue(lines, "the Partner Ledger returned no lines")
        for line in lines:
            self.assertEqual(
                len(line['columns']), len(options['columns']),
                "line %r has the wrong number of cells" % line.get('name'),
            )

    def test_03_every_line_shows_its_own_currency(self):
        options = self._options()
        lines = self._move_lines(options, self.report._get_lines(options))
        self.assertTrue(lines, "no journal item rows were produced")

        seen = {}
        for line in lines:
            currency_cell = self._cell(options, line, 'currency_name')
            amount_cell = self._cell(options, line, 'amount_currency')
            self.assertIsNotNone(currency_cell)
            self.assertIsNotNone(amount_cell)
            seen[currency_cell['no_format']] = amount_cell['no_format']

        self.assertEqual(
            sorted(k for k in seen if k), ['IQD', 'USD'],
            "both currencies should appear, got %s" % sorted(seen),
        )

        # the USD document keeps its original 100, not the 155,000 conversion
        self.assertAlmostEqual(float(seen['USD']), 100.0, places=2)
        # the IQD document is no longer blank
        self.assertAlmostEqual(float(seen['IQD']), 10000.0, places=2)

    def test_04_debit_credit_stay_in_company_currency(self):
        """We must not disturb the ledger figures the accountants rely on."""
        options = self._options()
        lines = self._move_lines(options, self.report._get_lines(options))

        totals = 0.0
        for line in lines:
            debit = self._cell(options, line, 'debit')
            totals += float(debit['no_format'] or 0.0)

        # 10,000 IQD + (100 USD -> 155,000 IQD)
        self.assertAlmostEqual(totals, 165000.0, delta=50.0)
