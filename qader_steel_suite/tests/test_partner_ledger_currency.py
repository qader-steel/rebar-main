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

    def _currency_column(self):
        return self.report.column_ids.filtered(
            lambda c: c.expression_label == 'currency_name'
        )

    def test_01_currency_column_is_installed(self):
        """The optional "Currency" column.

        ``data/partner_ledger_columns.xml`` is commented out of the
        manifest by design (exactly as in the original module), so this
        column normally does not exist. The test therefore skips rather
        than failing every build - it only asserts the column is sane if
        somebody has enabled that data file.
        """
        column = self._currency_column()
        if not column:
            self.skipTest(
                "data/partner_ledger_columns.xml is disabled in the manifest, "
                "so the optional Currency column is not installed"
            )
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
        """Needs the optional Currency column to tell the rows apart."""
        if not self._currency_column():
            self.skipTest(
                "data/partner_ledger_columns.xml is disabled in the manifest, "
                "so rows cannot be keyed by currency name here - "
                "test_03b covers the amounts without it"
            )

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

    def test_03b_amount_currency_cell_is_filled_on_every_line(self):
        """The display half of the fix, without needing the optional column.

        Both documents must show a non-empty Amount Currency cell: 100 for
        the USD invoice and 10,000 for the IQD one (Odoo leaves the latter
        blank out of the box, because it stores the value in ``balance``).
        """
        options = self._options()
        lines = self._move_lines(options, self.report._get_lines(options))
        self.assertTrue(lines, "no journal item rows were produced")

        amounts = []
        for line in lines:
            cell = self._cell(options, line, 'amount_currency')
            self.assertIsNotNone(cell, "no amount_currency cell on a move line")
            amounts.append(float(cell['no_format'] or 0.0))

        self.assertIn(100.0, [round(a, 2) for a in amounts],
                      "the USD invoice should show its original 100")
        self.assertIn(10000.0, [round(a, 2) for a in amounts],
                      "the IQD invoice must not be blank")

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

    # ------------------------------------------------------------------
    # Regression tests for the per-currency total rows (19.0.1.3.0)
    # ------------------------------------------------------------------

    def _single_group(self, sums):
        """Unwrap a {column_group_key: {...}} result that has one group."""
        self.assertEqual(
            len(sums), 1,
            "expected exactly one column group, got %s" % list(sums),
        )
        return next(iter(sums.values()))

    def test_05_currency_sums_include_the_company_currency(self):
        """The bug this release fixes.

        Odoo leaves ``amount_currency`` at 0 on lines whose document
        currency IS the company currency - the value lives in ``balance``
        instead. The previous query summed ``amount_currency`` blindly, so
        the IQD total came out as 0 and was then dropped by the
        ``if not amount: continue`` guard: the accountant saw a USD total
        and no IQD total at all.
        """
        options = self._options()
        sums = self.report._compute_amount_currency_by_partner(options)
        by_partner = self._single_group(sums)

        partner_sums = by_partner.get(self.partner_a.id, {})
        self.assertTrue(partner_sums, "no currency totals were computed")

        self.assertIn(
            self.iqd.id, partner_sums,
            "the company currency (IQD) is missing from the totals - "
            "this is exactly the bug 19.0.1.3.0 fixes",
        )
        self.assertIn(self.usd.id, partner_sums, "USD is missing from the totals")

        # The USD document keeps its original 100, not the 155,000 conversion.
        self.assertAlmostEqual(partner_sums[self.usd.id], 100.0, places=2)
        # The IQD document must report 10,000 and not 0.
        self.assertAlmostEqual(partner_sums[self.iqd.id], 10000.0, places=2)

    def test_06_currency_sums_are_grouped_by_account_too(self):
        """The General Ledger reuses the same engine, grouped by account."""
        options = self._options()
        sums = self.report._compute_amount_currency_by_account(options)
        by_account = self._single_group(sums)

        self.assertTrue(by_account, "no per-account currency totals were computed")

        currencies_seen = set()
        for account_sums in by_account.values():
            currencies_seen |= set(account_sums)

        self.assertIn(
            self.iqd.id, currencies_seen,
            "IQD must appear in the per-account totals as well",
        )
        self.assertIn(self.usd.id, currencies_seen, "USD must appear too")

    def test_07_scoping_to_one_partner_matches_the_unscoped_result(self):
        """``groupby_ids`` is a performance filter, not a behaviour change."""
        options = self._options()

        unscoped = self._single_group(
            self.report._compute_amount_currency_by_partner(options)
        ).get(self.partner_a.id, {})

        scoped = self._single_group(
            self.report._compute_amount_currency_by_partner(
                options, groupby_ids=[self.partner_a.id],
            )
        ).get(self.partner_a.id, {})

        self.assertEqual(
            {k: round(v, 2) for k, v in unscoped.items()},
            {k: round(v, 2) for k, v in scoped.items()},
            "restricting the query to one partner changed its totals",
        )

    def test_08_comparison_periods_are_kept_apart(self):
        """Regression: column groups must never be summed together.

        With Comparison enabled Odoo splits the report into several column
        groups, each with its own date scope. An earlier version of this
        code merged every group into one bucket, so the row under the
        partner showed period A + period B added together - a figure that
        appears nowhere in the ledger and cannot be reconciled.
        """
        options = self.report.get_options({
            'selected_variant_id': self.report.id,
            'partner_ids': [self.partner_a.id],
            'unfold_all': True,
            'date': {
                'mode': 'range',
                'filter': 'custom',
                'date_from': '2026-01-01',
                'date_to': '2026-12-31',
            },
            'comparison': {
                'filter': 'previous_period',
                'number_period': 1,
            },
        })

        # Only meaningful if this Odoo build actually produced 2 groups.
        groups = {c.get('column_group_key') for c in options['columns']}
        if len(groups) < 2:
            self.skipTest("this build did not split the report into column groups")

        sums = self.report._compute_amount_currency_by_partner(
            options, groupby_ids=[self.partner_a.id],
        )

        self.assertGreaterEqual(
            len(sums), 2,
            "each column group must get its own bucket, got %s" % list(sums),
        )

        # The 2026 group holds the real figures; the 2025 comparison period
        # predates both invoices, so it must not carry their amounts.
        current = max(
            sums.values(),
            key=lambda g: g.get(self.partner_a.id, {}).get(self.iqd.id, 0.0),
        )
        self.assertAlmostEqual(
            current.get(self.partner_a.id, {}).get(self.iqd.id, 0.0),
            10000.0,
            places=2,
            msg="the current period's IQD total must be exactly the invoice "
                "amount, not the sum of both periods",
        )