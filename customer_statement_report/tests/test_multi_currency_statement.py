# -*- coding: utf-8 -*-
"""
Real Odoo tests for the multi-currency statement.

Run them on Odoo.sh (they execute automatically on a staging build) or locally:

    odoo-bin -d <db> -i customer_statement_report --test-enable \\
             --test-tags /customer_statement_report --stop-after-init

The company is created with IQD as its main currency and USD as a second
currency at 1 USD = 1,310 IQD, which mirrors the client's setup.
"""

from odoo import Command, fields
from odoo.tests import tagged
from odoo.addons.account.tests.common import AccountTestInvoicingCommon

USD_PER_IQD = 1.0 / 1310.0


@tagged('post_install', '-at_install')
class TestMultiCurrencyStatement(AccountTestInvoicingCommon):

    # ------------------------------------------------------------------
    # SETUP
    # ------------------------------------------------------------------

    @classmethod
    def setup_independent_company(cls, **kwargs):
        """Main currency = IQD, exactly like the client's company."""
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

        cls.engine = cls.env['report.customer_statement_report.from_lines']
        cls.partner = cls.partner_a

        cls.date_from = fields.Date.to_date('2026-01-01')
        cls.date_to = fields.Date.to_date('2026-03-31')

        # ---- opening documents (before the period) -------------------
        cls._invoice('2025-11-05', cls.iqd, [(100, 5000.0)])          # 500,000 IQD
        cls._invoice('2025-11-20', cls.usd, [(4, 50.0)])              # 200 USD
        cls._payment('2025-12-01', cls.iqd, 200000.0)                 # -200,000 IQD

        # ---- period documents ---------------------------------------
        cls.inv_usd = cls._invoice(
            '2026-01-15', cls.usd, [(2, 50.0), (3, 50.0)],            # 250 USD
        )
        cls.inv_iqd = cls._invoice('2026-02-10', cls.iqd, [(150, 5000.0)])
        cls.pay_usd = cls._payment('2026-02-20', cls.usd, 120.0)
        cls.pay_iqd = cls._payment('2026-03-05', cls.iqd, 300000.0)

    # ------------------------------------------------------------------
    # HELPERS
    # ------------------------------------------------------------------

    @classmethod
    def _invoice(cls, date, currency, lines, move_type='out_invoice'):
        move = cls.env['account.move'].create({
            'move_type': move_type,
            'partner_id': cls.partner_a.id,
            'invoice_date': date,
            'date': date,
            'currency_id': currency.id,
            'invoice_line_ids': [
                Command.create({
                    'product_id': cls.product_a.id,
                    'quantity': quantity,
                    'price_unit': price,
                    'tax_ids': [Command.clear()],
                })
                for quantity, price in lines
            ],
        })
        move.action_post()
        return move

    @classmethod
    def _payment(cls, date, currency, amount):
        payment = cls.env['account.payment'].create({
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': cls.partner_a.id,
            'amount': amount,
            'currency_id': currency.id,
            'date': date,
            'journal_id': cls.company_data['default_journal_bank'].id,
        })
        payment.action_post()
        return payment

    def _period_lines(self):
        """Everything a user would select in the Journal Items list view."""
        return self.env['account.move.line'].search([
            ('partner_id', '=', self.partner.id),
            ('parent_state', '=', 'posted'),
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
        ])

    def _statement(self):
        values = self.engine._get_report_values(
            self._period_lines().ids,
            data={'date_from': self.date_from, 'date_to': self.date_to},
        )
        self.assertTrue(values['statements'], "no statement was produced")
        return values['statements'][0]

    def _groups(self, statement):
        return {g['currency'].name: g for g in statement['currency_groups']}

    # ------------------------------------------------------------------
    # TESTS
    # ------------------------------------------------------------------

    def test_01_company_is_iqd_with_usd_enabled(self):
        self.assertEqual(self.env.company.currency_id.name, 'IQD')
        self.assertEqual(self.usd.name, 'USD')
        self.assertTrue(self.usd.active)

    def test_02_amounts_are_read_in_the_document_currency(self):
        """A USD invoice line must report 100 USD, not 131,000 IQD."""
        line = self.inv_usd.invoice_line_ids.filtered(
            lambda l: l.quantity == 2
        )
        amounts = self.engine._get_line_amounts(line)

        self.assertEqual(amounts['currency'], self.usd)
        self.assertAlmostEqual(amounts['debit'], 100.0, places=2)
        self.assertAlmostEqual(amounts['credit'], 0.0, places=2)
        # the company-currency figure is still available for the consolidation
        self.assertAlmostEqual(amounts['debit_company'], 131000.0, delta=1.0)

    def test_03_one_section_per_currency(self):
        statement = self._statement()
        groups = self._groups(statement)

        self.assertEqual(sorted(groups), ['IQD', 'USD'])
        self.assertTrue(statement['is_multi_currency'])
        # company currency first
        self.assertEqual(
            statement['currency_groups'][0]['currency'], self.iqd,
        )

    def test_04_opening_balances_are_per_currency(self):
        opening = self.engine._compute_opening(
            self.partner, 'customer', self.date_from,
            company=self.env.company,
        )
        by_name = {b['currency'].name: b for b in opening.values()}

        self.assertAlmostEqual(by_name['IQD']['balance'], 300000.0, delta=1.0)
        self.assertAlmostEqual(by_name['USD']['balance'], 200.0, places=2)

    def test_05_closing_balances(self):
        groups = self._groups(self._statement())

        # IQD: 300,000 opening + 750,000 invoice - 300,000 payment
        self.assertAlmostEqual(
            groups['IQD']['closing_balance'], 750000.0, delta=1.0,
        )
        # USD: 200 opening + 250 invoice - 120 payment
        self.assertAlmostEqual(
            groups['USD']['closing_balance'], 330.0, places=2,
        )

    def test_06_no_currency_is_ever_mixed_into_a_running_balance(self):
        for group in self._statement()['currency_groups']:
            currency = group['currency']
            for line in group['lines']:
                self.assertEqual(
                    line['currency'], currency,
                    "a %s row leaked into the %s section"
                    % (line['currency'].name, currency.name),
                )

    def test_07_running_balance_is_consistent(self):
        for group in self._statement()['currency_groups']:
            currency = group['currency']
            running = group['opening_balance']
            for line in group['lines']:
                running = currency.round(
                    running + line['debit'] - line['credit']
                )
                self.assertAlmostEqual(
                    line['balance'], running,
                    delta=10 ** -currency.decimal_places,
                )
            self.assertAlmostEqual(
                group['closing_balance'],
                currency.round(
                    group['opening_balance']
                    + group['total_debit'] - group['total_credit']
                ),
                delta=10 ** -currency.decimal_places,
            )

    def test_08_unit_price_and_debit_share_one_currency(self):
        """The bug that used to put a USD unit price next to an IQD debit."""
        for group in self._statement()['currency_groups']:
            for line in group['lines']:
                if not line['quantity']:
                    continue
                self.assertAlmostEqual(
                    line['debit'],
                    line['quantity'] * line['unit_price'],
                    delta=10 ** -group['currency'].decimal_places,
                    msg="qty x unit price does not match the debit on %s"
                        % line['transaction'],
                )

    def test_09_consolidated_total_uses_historical_rates(self):
        statement = self._statement()
        groups = self._groups(statement)

        expected = (
            groups['IQD']['closing_balance_company']
            + groups['USD']['closing_balance_company']
        )
        self.assertAlmostEqual(
            statement['closing_balance_company'], expected, delta=1.0,
        )
        # USD 330 booked at 1,310 -> around 432,300 IQD
        self.assertAlmostEqual(
            groups['USD']['closing_balance_company'], 432300.0, delta=5.0,
        )

    def test_10_wizard_currency_filter(self):
        wizard = self.env['customer.statement.wizard'].create({
            'partner_id': self.partner.id,
            'date_from': self.date_from,
            'date_to': self.date_to,
            'party_type': 'customer',
        })

        both = wizard._build_statements()[0]
        self.assertEqual(
            sorted(g['currency'].name for g in both['currency_groups']),
            ['IQD', 'USD'],
        )

        wizard.currency_id = self.usd
        only_usd = wizard._build_statements()[0]
        self.assertEqual(
            [g['currency'].name for g in only_usd['currency_groups']], ['USD'],
        )
        self.assertAlmostEqual(
            only_usd['currency_groups'][0]['closing_balance'], 330.0, places=2,
        )
        self.assertFalse(only_usd['is_multi_currency'])

    def test_11_wizard_report_action(self):
        wizard = self.env['customer.statement.wizard'].create({
            'partner_id': self.partner.id,
            'date_from': self.date_from,
            'date_to': self.date_to,
            'party_type': 'customer',
        })
        action = wizard.action_print_report()
        self.assertEqual(action['type'], 'ir.actions.report')

    def test_12_templates_actually_render(self):
        """Renders both QWeb templates through the real Odoo engine."""
        html = self.env['ir.actions.report']._render_qweb_html(
            'customer_statement_report.from_lines',
            self._period_lines().ids,
            data={'date_from': self.date_from, 'date_to': self.date_to},
        )[0]
        body = html.decode() if isinstance(html, bytes) else html

        self.assertIn('Statement in USD', body)
        self.assertIn('Statement in IQD', body)
        self.assertIn('Debit (USD)', body)
        self.assertIn('Consolidated Total in IQD', body)

        wizard = self.env['customer.statement.wizard'].create({
            'partner_id': self.partner.id,
            'date_from': self.date_from,
            'date_to': self.date_to,
            'party_type': 'customer',
        })
        wizard_html = self.env['ir.actions.report']._render_qweb_html(
            'customer_statement_report.statement',
            wizard.ids,
            data={'wizard_id': wizard.id},
        )[0]
        wizard_body = (
            wizard_html.decode()
            if isinstance(wizard_html, bytes) else wizard_html
        )
        self.assertIn('Statement in USD', wizard_body)

    def test_13_empty_selection_does_not_crash(self):
        values = self.engine._get_report_values([], data=None)
        self.assertEqual(values['statements'], [])

    def test_14_vendor_bills_get_their_own_statement(self):
        bill = self._invoice(
            '2026-02-25', self.usd, [(2, 40.0)], move_type='in_invoice',
        )
        values = self.engine._get_report_values(
            (self._period_lines() | bill.line_ids).ids,
            data={'date_from': self.date_from, 'date_to': self.date_to},
        )
        party_types = sorted(s['party_type'] for s in values['statements'])
        self.assertEqual(party_types, ['customer', 'vendor'])

        vendor = next(
            s for s in values['statements'] if s['party_type'] == 'vendor'
        )
        vendor_groups = self._groups(vendor)
        self.assertEqual(sorted(vendor_groups), ['USD'])
        # debit-positive convention: what you owe is a credit
        self.assertAlmostEqual(
            vendor_groups['USD']['closing_balance'], -80.0, places=2,
        )
