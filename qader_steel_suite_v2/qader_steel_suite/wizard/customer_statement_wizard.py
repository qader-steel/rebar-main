# -*- coding: utf-8 -*-
"""
Customer / Vendor Statement Report - multi-currency engine.

Design notes
------------
Odoo stores every journal item twice:

    * ``debit`` / ``credit`` / ``balance``  -> always in the COMPANY currency
      (IQD here), converted at the rate of the entry date.
    * ``amount_currency`` + ``currency_id`` -> the ORIGINAL amount, in the
      currency the document was actually issued in (USD, IQD, ...).

The statement must never mix currencies inside a single running balance:
100 USD + 100 IQD is not 200 of anything.  So a statement is split into one
section per currency, each section carrying its own opening balance, its own
debit/credit totals and its own closing balance, expressed in that currency.

For management, a single consolidated figure is still produced, but it is
taken from ``debit`` / ``credit`` (company currency at the historical rate)
rather than by converting the per-currency closing balances at today's rate -
the former is the accounting-correct number.
"""

import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

CUSTOMER_MOVE_TYPES = ('out_invoice', 'out_refund')
VENDOR_MOVE_TYPES = ('in_invoice', 'in_refund')
INVOICE_MOVE_TYPES = CUSTOMER_MOVE_TYPES + VENDOR_MOVE_TYPES

PARTY_ACCOUNT_TYPE = {
    'customer': 'asset_receivable',
    'vendor': 'liability_payable',
}
PARTY_MOVE_TYPES = {
    'customer': CUSTOMER_MOVE_TYPES,
    'vendor': VENDOR_MOVE_TYPES,
}


class CustomerStatementEngine(models.AbstractModel):
    """Shared computation engine for every flavour of the statement report."""

    _name = 'customer.statement.engine'
    _description = 'Customer / Vendor Statement Engine'

    # ------------------------------------------------------------------
    # MOVE / LINE CLASSIFICATION
    # ------------------------------------------------------------------

    def _is_payment_move(self, move):
        """Real payment / cash / bank move (payments, POS, bank statements)."""
        if 'payment_id' in move._fields and move.payment_id:
            return True

        if 'statement_line_id' in move._fields and move.statement_line_id:
            return True

        if move.journal_id and move.journal_id.type in ('cash', 'bank'):
            return True

        return False

    def _is_invoice_move(self, move):
        """Invoice / Bill / Credit note document."""
        return move.move_type in INVOICE_MOVE_TYPES

    def _is_product_line(self, line):
        """Real product line of an invoice (not tax, section, note, ...)."""
        if not line.product_id:
            return False

        return line.display_type in (False, 'product')

    def _should_include_line(self, line, party_type):
        """Decide whether a journal item shows up as a statement row.

        For invoices we display the product detail lines (that is the whole
        point of this report); for everything else we display the
        receivable / payable counterpart.
        """
        move = line.move_id
        account_type = PARTY_ACCOUNT_TYPE[party_type]

        if self._is_invoice_move(move):
            return self._is_product_line(line)

        return line.account_id.account_type == account_type

    def _get_party_type(self, move):
        """Customer flow or vendor flow, so the right account type is used."""
        if move.move_type in VENDOR_MOVE_TYPES:
            return 'vendor'

        if move.move_type in CUSTOMER_MOVE_TYPES:
            return 'customer'

        payable = move.line_ids.filtered(
            lambda l: l.account_id.account_type == 'liability_payable'
        )
        if payable:
            return 'vendor'

        return 'customer'

    # ------------------------------------------------------------------
    # AMOUNTS
    # ------------------------------------------------------------------

    def _get_line_currency(self, line):
        """The currency the document was actually issued in."""
        return (
            line.currency_id
            or line.company_currency_id
            or line.company_id.currency_id
            or self.env.company.currency_id
        )

    def _get_line_amounts(self, line):
        """Return debit/credit both in document currency and company currency.

        ``amount_currency`` is signed: positive means debit, negative means
        credit.  Product lines of an invoice are flipped, because a customer
        invoice credits an income account while the statement must show the
        invoice as a debit on the customer.
        """
        move = line.move_id
        currency = self._get_line_currency(line)

        amount_currency = line.amount_currency or 0.0

        # Safety net: on entries posted in the company currency some flows
        # leave amount_currency at 0 while balance carries the value.
        if not amount_currency and currency == line.company_currency_id:
            amount_currency = line.balance or 0.0

        debit_cur = amount_currency if amount_currency > 0.0 else 0.0
        credit_cur = -amount_currency if amount_currency < 0.0 else 0.0

        debit_comp = line.debit or 0.0
        credit_comp = line.credit or 0.0

        if self._is_invoice_move(move) and self._is_product_line(line):
            debit_cur, credit_cur = credit_cur, debit_cur
            debit_comp, credit_comp = credit_comp, debit_comp

        return {
            'currency': currency,
            'debit': debit_cur,
            'credit': credit_cur,
            'debit_company': debit_comp,
            'credit_company': credit_comp,
        }

    def _get_line_label(self, line):
        move = line.move_id

        if line.product_id:
            return line.product_id.display_name

        return line.name or move.ref or move.payment_reference or move.name or ''

    def _get_move_kind(self, move):
        if self._is_invoice_move(move):
            return 'invoice'

        if self._is_payment_move(move):
            return 'payment'

        return 'other'

    # ------------------------------------------------------------------
    # DOMAINS
    # ------------------------------------------------------------------

    def _get_party_domain(self, partner, party_type):
        """Narrow domain that is a superset of what _should_include_line keeps.

        Included rows are either product lines of an invoice document, or
        receivable / payable lines.  Expressing that in SQL keeps the
        opening-balance search from scanning every journal item of the
        partner.
        """
        return [
            ('partner_id', '=', partner.id),
            ('parent_state', '=', 'posted'),
            '|',
            ('account_id.account_type', '=', PARTY_ACCOUNT_TYPE[party_type]),
            ('move_id.move_type', 'in', list(PARTY_MOVE_TYPES[party_type])),
        ]

    # ------------------------------------------------------------------
    # OPENING BALANCE (per currency)
    # ------------------------------------------------------------------

    def _compute_opening(self, partner, party_type, date_from, currency=None,
                         company=None):
        """Opening balances strictly before ``date_from``, keyed by currency id."""
        opening = {}

        if not date_from:
            return opening

        domain = self._get_party_domain(partner, party_type)
        domain += [('date', '<', date_from)]

        if currency:
            domain += [('currency_id', '=', currency.id)]

        if company:
            domain += [('company_id', '=', company.id)]

        lines = self.env['account.move.line'].search(domain)

        company_currency = self._get_company_currency(partner, company)

        for line in lines:
            if self._get_party_type(line.move_id) != party_type:
                continue

            if not self._should_include_line(line, party_type):
                continue

            amounts = self._get_line_amounts(line)
            line_currency = amounts['currency']

            bucket = opening.setdefault(line_currency.id, {
                'currency': line_currency,
                'debit': 0.0,
                'credit': 0.0,
                'debit_company': 0.0,
                'credit_company': 0.0,
            })

            bucket['debit'] += amounts['debit']
            bucket['credit'] += amounts['credit']
            bucket['debit_company'] += amounts['debit_company']
            bucket['credit_company'] += amounts['credit_company']

        for bucket in opening.values():
            bucket_currency = bucket['currency']
            bucket['balance'] = bucket_currency.round(
                bucket['debit'] - bucket['credit']
            )
            bucket['balance_company'] = company_currency.round(
                bucket['debit_company'] - bucket['credit_company']
            )

        return opening

    # ------------------------------------------------------------------
    # STATEMENT BUILDER
    # ------------------------------------------------------------------

    def _get_company_currency(self, partner=None, company=None):
        if company:
            return company.currency_id

        if partner and partner.company_id:
            return partner.company_id.currency_id

        return self.env.company.currency_id

    def _sort_currencies(self, currencies, company_currency):
        """Company currency first, then alphabetically - stable output."""
        return sorted(
            currencies,
            key=lambda c: (0 if c == company_currency else 1, c.name or ''),
        )

    def _build_statement(self, partner, lines, party_type, date_from, date_to,
                         currency_filter=None, company=None):
        """Build one statement dict for a partner / party type.

        ``lines`` are the already filtered & sorted journal items of the
        period.  The result carries one section per currency.
        """
        company_currency = self._get_company_currency(partner, company)

        opening = self._compute_opening(
            partner, party_type, date_from,
            currency=currency_filter, company=company,
        )

        # Every currency that has either a period line or an opening balance.
        currencies = self.env['res.currency']

        for line in lines:
            currencies |= self._get_line_currency(line)

        for bucket in opening.values():
            if not bucket['currency'].is_zero(bucket['balance']):
                currencies |= bucket['currency']

        if currency_filter:
            currencies = currencies.filtered(lambda c: c == currency_filter)

        groups = []

        for currency in self._sort_currencies(currencies, company_currency):

            currency_lines = lines.filtered(
                lambda l: self._get_line_currency(l) == currency
            )

            opening_bucket = opening.get(currency.id, {})
            opening_balance = opening_bucket.get('balance', 0.0)
            opening_balance_company = opening_bucket.get('balance_company', 0.0)

            balance = opening_balance
            balance_company = opening_balance_company

            result_lines = []

            total_qty = 0.0
            total_debit = 0.0
            total_credit = 0.0
            total_debit_company = 0.0
            total_credit_company = 0.0

            for line in currency_lines:
                move = line.move_id
                account = line.account_id

                amounts = self._get_line_amounts(line)

                debit = amounts['debit']
                credit = amounts['credit']
                debit_company = amounts['debit_company']
                credit_company = amounts['credit_company']

                quantity = (line.quantity or 0.0) if line.product_id else 0.0
                # price_unit lives in the document currency, exactly like the
                # debit / credit shown on this row - so the row is coherent.
                unit_price = (line.price_unit or 0.0) if line.product_id else 0.0

                balance = currency.round(balance + debit - credit)
                balance_company = company_currency.round(
                    balance_company + debit_company - credit_company
                )

                total_qty += quantity
                total_debit += debit
                total_credit += credit
                total_debit_company += debit_company
                total_credit_company += credit_company

                result_lines.append({
                    'aml_id': line.id,
                    'date': line.date,
                    'transaction': move.name,
                    'product': self._get_line_label(line),
                    'description': line.name or '',
                    'quantity': quantity,
                    'unit_price': unit_price,
                    'debit': debit,
                    'credit': credit,
                    'balance': balance,
                    'debit_company': debit_company,
                    'credit_company': credit_company,
                    'balance_company': balance_company,
                    'currency': currency,
                    'company_currency': company_currency,
                    'account_id': account.id if account else False,
                    'account_code': account.code if account else '',
                    'account_name': account.name if account else '',
                    'account_type': account.account_type if account else '',
                    'move_type': move.move_type,
                    'move_kind': self._get_move_kind(move),
                    'party_type': party_type,
                    'journal_name': move.journal_id.name if move.journal_id else '',
                })

            total_debit = currency.round(total_debit)
            total_credit = currency.round(total_credit)
            total_debit_company = company_currency.round(total_debit_company)
            total_credit_company = company_currency.round(total_credit_company)

            # Nothing at all to show for this currency.
            if not result_lines and currency.is_zero(opening_balance):
                continue

            expected_closing = currency.round(
                opening_balance + total_debit - total_credit
            )

            if not currency.is_zero(expected_closing - balance):
                _logger.error(
                    "STATEMENT BALANCE MISMATCH | partner=%s | type=%s | "
                    "currency=%s | expected=%s | actual=%s",
                    partner.id, party_type, currency.name,
                    expected_closing, balance,
                )

            groups.append({
                'currency': currency,
                'company_currency': company_currency,
                'is_company_currency': currency == company_currency,
                'opening_balance': opening_balance,
                'lines': result_lines,
                'closing_balance': balance,
                'total_qty': total_qty,
                'total_debit': total_debit,
                'total_credit': total_credit,
                'opening_balance_company': opening_balance_company,
                'closing_balance_company': balance_company,
                'total_debit_company': total_debit_company,
                'total_credit_company': total_credit_company,
            })

        statement = {
            'partner': partner,
            'party_type': party_type,
            'party_type_label': (
                _('Vendor') if party_type == 'vendor' else _('Customer')
            ),
            'company_currency': company_currency,
            'currency_groups': groups,
            'is_multi_currency': len(groups) > 1,
            'date_from': date_from,
            'date_to': date_to,
            'opening_balance_company': company_currency.round(
                sum(g['opening_balance_company'] for g in groups)
            ),
            'closing_balance_company': company_currency.round(
                sum(g['closing_balance_company'] for g in groups)
            ),
            'total_debit_company': company_currency.round(
                sum(g['total_debit_company'] for g in groups)
            ),
            'total_credit_company': company_currency.round(
                sum(g['total_credit_company'] for g in groups)
            ),
        }

        _logger.info(
            "STATEMENT | partner=%s(%s) | type=%s | currencies=%s | rows=%s",
            partner.name, partner.id, party_type,
            [g['currency'].name for g in groups],
            sum(len(g['lines']) for g in groups),
        )

        return statement


class CustomerStatementFromLines(models.AbstractModel):
    """Statement built from journal items selected in the list view."""

    _name = 'report.qader_steel_suite.from_lines'
    _inherit = 'customer.statement.engine'
    _description = 'Customer / Vendor Statement Report (from Journal Items)'

    @api.model
    def _get_report_values(self, docids, data=None):
        selected_lines = self.env['account.move.line'].browse(docids).exists()

        empty = {
            'doc_ids': docids,
            'doc_model': 'account.move.line',
            'docs': selected_lines,
            'statements': [],
            'date_from': False,
            'date_to': False,
            'currency_filter': False,
        }

        if not selected_lines:
            _logger.warning("STATEMENT | no journal item selected")
            return empty

        partners = selected_lines.mapped('partner_id')

        dates = [d for d in selected_lines.mapped('date') if d]

        date_from = (data or {}).get('date_from') or (min(dates) if dates else False)
        date_to = (data or {}).get('date_to') or (max(dates) if dates else False)

        if not partners:
            empty.update({'date_from': date_from, 'date_to': date_to})
            return empty

        # ---- classify every selected line once -------------------------
        line_party_type = {}
        included_lines = self.env['account.move.line']

        for line in selected_lines:
            party_type = self._get_party_type(line.move_id)
            line_party_type[line.id] = party_type

            if self._should_include_line(line, party_type):
                included_lines |= line

        _logger.info(
            "STATEMENT | selected=%s | included=%s | partners=%s",
            len(selected_lines), len(included_lines), len(partners),
        )

        # ---- build one statement per partner / party type --------------
        statements = []

        for partner in partners:
            partner_lines = included_lines.filtered(
                lambda l: l.partner_id == partner
            )

            party_types = sorted({
                line_party_type.get(l.id, 'customer') for l in partner_lines
            })

            for party_type in party_types:
                type_lines = partner_lines.filtered(
                    lambda l: line_party_type.get(l.id, 'customer') == party_type
                ).sorted(
                    key=lambda l: (l.date, l.move_id.id, l.sequence or 0, l.id)
                )

                statement = self._build_statement(
                    partner, type_lines, party_type, date_from, date_to,
                    company=type_lines[:1].company_id or None,
                )

                if statement['currency_groups']:
                    statements.append(statement)

        return {
            'doc_ids': docids,
            'doc_model': 'account.move.line',
            'docs': selected_lines,
            'statements': statements,
            'date_from': date_from,
            'date_to': date_to,
            'currency_filter': False,
        }


class CustomerStatementReport(models.AbstractModel):
    """Statement built from the wizard (partner + date range + currency)."""

    _name = 'report.qader_steel_suite.statement'
    _inherit = 'customer.statement.engine'
    _description = 'Customer / Vendor Statement Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        wizard_id = (data or {}).get('wizard_id') or (docids[0] if docids else False)
        wizard = self.env['customer.statement.wizard'].browse(wizard_id).exists()

        if not wizard:
            return {
                'doc_ids': docids,
                'doc_model': 'customer.statement.wizard',
                'docs': wizard,
                'wizard': wizard,
                'statements': [],
                'date_from': False,
                'date_to': False,
                'currency_filter': False,
            }

        statements = wizard._build_statements()

        return {
            'doc_ids': [wizard.id],
            'doc_model': 'customer.statement.wizard',
            'docs': wizard,
            'wizard': wizard,
            'statements': statements,
            'date_from': wizard.date_from,
            'date_to': wizard.date_to,
            'currency_filter': wizard.currency_id,
        }


class CustomerStatementWizard(models.TransientModel):
    _name = 'customer.statement.wizard'
    _description = 'Customer Statement Wizard'

    partner_id = fields.Many2one(
        'res.partner',
        string='Partner',
        required=True,
    )
    date_from = fields.Date(string='From', required=True)
    date_to = fields.Date(string='To', required=True)
    party_type = fields.Selection(
        selection=[
            ('customer', 'Customer'),
            ('vendor', 'Vendor'),
        ],
        string='Statement Type',
        default='customer',
        required=True,
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        domain="[('active', '=', True)]",
        help="Leave empty to print every currency, each in its own section. "
             "Pick one to restrict the statement to that currency only.",
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True,
    )

    # ------------------------------------------------------------------

    def action_print_report(self):
        self.ensure_one()

        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise UserError(_("The 'From' date must not be after the 'To' date."))

        data = {
            'wizard_id': self.id,
            'partner_id': self.partner_id.id,
            'date_from': str(self.date_from),
            'date_to': str(self.date_to),
            'party_type': self.party_type,
            'currency_id': self.currency_id.id,
        }

        return self.env.ref(
            'qader_steel_suite.action_report_customer_statement'
        ).report_action(self, data=data)

    # ------------------------------------------------------------------

    def _build_statements(self):
        """Collect the period lines and hand them to the shared engine."""
        self.ensure_one()

        engine = self.env['report.qader_steel_suite.statement']

        domain = engine._get_party_domain(self.partner_id, self.party_type)
        domain += [
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
            ('company_id', '=', self.company_id.id),
        ]

        if self.currency_id:
            domain += [('currency_id', '=', self.currency_id.id)]

        candidate_lines = self.env['account.move.line'].search(
            domain, order='date asc, move_id asc, sequence asc, id asc',
        )

        period_lines = candidate_lines.filtered(
            lambda l: engine._get_party_type(l.move_id) == self.party_type
            and engine._should_include_line(l, self.party_type)
        )

        statement = engine._build_statement(
            self.partner_id,
            period_lines,
            self.party_type,
            self.date_from,
            self.date_to,
            currency_filter=self.currency_id or None,
            company=self.company_id,
        )

        return [statement] if statement['currency_groups'] else []
