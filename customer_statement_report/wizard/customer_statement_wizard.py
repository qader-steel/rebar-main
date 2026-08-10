from odoo import models, fields, api
import logging

from odoo import models, api


_logger = logging.getLogger(__name__)

class CustomerStatementReport(models.AbstractModel):
    _name = 'report.customer_statement_report.statement'
    _description = 'Customer Statement Report'

    def _get_report_values(self, docids, data=None):
        wizard_id = data.get('wizard_id') if data else (docids[0] if docids else False)
        wizard = self.env['customer.statement.wizard'].browse(wizard_id)
        stmt = wizard._get_statement_lines()
        return {
            'doc_ids': [wizard.id],
            'doc_model': 'customer.statement.wizard',
            'docs': wizard,
            'wizard': wizard,
            'stmt': stmt,
        }



import logging

from odoo import models, api


_logger = logging.getLogger(__name__)


class CustomerStatementReport(models.AbstractModel):

    _name = 'report.customer_statement_report.from_lines'
    _description = 'Customer Statement Report'


    @api.model
    def _get_report_values(self, docids, data=None):


        _logger.warning(
            "========== CUSTOMER STATEMENT START =========="
        )

        _logger.warning(
            "DOCIDS: %s",
            docids
        )


        # =====================================================
        # Selected journal items
        # =====================================================

        selected_lines = self.env['account.move.line'].browse(docids)


        _logger.warning(
            "SELECTED COUNT: %s",
            len(selected_lines)
        )


        for l in selected_lines:

            _logger.warning(
                """
                SELECTED LINE
                ID=%s
                MOVE=%s
                TYPE=%s
                PARTNER=%s
                ACCOUNT=%s
                DEBIT=%s
                CREDIT=%s
                """,
                l.id,
                l.move_id.name,
                l.move_id.move_type,
                l.partner_id.name,
                l.account_id.code,
                l.debit,
                l.credit,
            )



        selected_lines = selected_lines.filtered(
            lambda l:
                l.partner_id
                and l.parent_state == 'posted'
                and l.account_id.account_type in (
                    'asset_receivable',
                    'liability_payable'
                )
        )


        if not selected_lines:

            _logger.warning(
                "NO VALID SELECTED LINES"
            )


            return {
                'doc_ids': docids,
                'doc_model': 'account.move.line',
                'docs': selected_lines,
                'statements': [],
                'date_from': False,
                'date_to': False,
            }



        partners = selected_lines.mapped('partner_id')


        _logger.warning(
            "PARTNERS: %s",
            partners.mapped('name')
        )


        # =====================================================
        # Date range from selected lines
        # =====================================================


        date_from = min(
            selected_lines.mapped('date')
        )

        date_to = max(
            selected_lines.mapped('date')
        )


        _logger.warning(
            "DATE RANGE %s -> %s",
            date_from,
            date_to
        )



        statements = []



        for partner in partners:


            _logger.warning(
                "PROCESS PARTNER %s",
                partner.name
            )


            account = (
                partner.property_account_receivable_id
                or partner.property_account_payable_id
            )


            if not account:

                _logger.warning(
                    "NO ACCOUNT FOR PARTNER %s",
                    partner.name
                )

                continue



            # =====================================================
            # Opening balance
            # =====================================================


            opening_lines = self.env['account.move.line'].search([

                ('partner_id','=',partner.id),

                ('account_id','=',account.id),

                ('parent_state','=','posted'),

                ('date','<',date_from),

            ])



            opening_balance = (
                sum(opening_lines.mapped('debit'))
                -
                sum(opening_lines.mapped('credit'))
            )


            _logger.warning(
                "OPENING BALANCE %s",
                opening_balance
            )



            # =====================================================
            # ALL customer transactions
            # =====================================================


            moves = self.env['account.move.line'].search([

                ('partner_id','=',partner.id),

                ('account_id','=',account.id),

                ('parent_state','=','posted'),

                ('date','>=',date_from),

                ('date','<=',date_to),

            ], order='date,id')



            _logger.warning(
                "MOVES COUNT %s",
                len(moves)
            )



            balance = opening_balance


            result_lines = []

            total_qty = 0.0
            total_debit = 0.0
            total_credit = 0.0



            for line in moves:


                move = line.move_id



                _logger.warning(
                    "PROCESS MOVE %s TYPE %s",
                    move.name,
                    move.move_type
                )



                # =================================================
                # Invoice
                # =================================================

                if move.move_type in (
                    'out_invoice',
                    'out_refund'
                ):



                    invoice_lines = move.invoice_line_ids.filtered(
                        lambda x:
                            not x.display_type
                            and x.product_id
                    )



                    _logger.warning(
                        "INVOICE %s PRODUCT LINES %s",
                        move.name,
                        len(invoice_lines)
                    )



                    for il in invoice_lines:



                        amount = il.price_subtotal



                        if move.move_type == 'out_invoice':

                            debit = amount
                            credit = 0.0

                        else:

                            debit = 0.0
                            credit = amount



                        balance += debit - credit



                        total_qty += il.quantity

                        total_debit += debit

                        total_credit += credit



                        result_lines.append({

                            'date':
                                line.date,


                            'transaction':
                                move.name,


                            'product':
                                il.product_id.display_name,


                            'quantity':
                                il.quantity,


                            'unit_price':
                                il.price_unit,


                            'debit':
                                debit,


                            'credit':
                                credit,


                            'balance':
                                balance,

                        })



                # =================================================
                # Payment / Journal
                # =================================================

                else:


                    debit = line.debit

                    credit = line.credit



                    balance += debit - credit



                    total_debit += debit

                    total_credit += credit



                    result_lines.append({

                        'date':
                            line.date,


                        'transaction':
                            move.name,


                        'product':
                            line.name or '',


                        'quantity':
                            None,


                        'unit_price':
                            None,


                        'debit':
                            debit,


                        'credit':
                            credit,


                        'balance':
                            balance,

                    })




            statements.append({

                'partner':
                    partner,


                'opening_balance':
                    opening_balance,


                'lines':
                    result_lines,


                'closing_balance':
                    balance,


                'total_qty':
                    total_qty,


                'total_debit':
                    total_debit,


                'total_credit':
                    total_credit,

            })



            _logger.warning(
                """
                RESULT
                PARTNER=%s
                LINES=%s
                DEBIT=%s
                CREDIT=%s
                BALANCE=%s
                """,
                partner.name,
                len(result_lines),
                total_debit,
                total_credit,
                balance
            )



        _logger.warning(
            "STATEMENTS COUNT %s",
            len(statements)
        )


        _logger.warning(
            "========== CUSTOMER STATEMENT END =========="
        )



        return {


            'doc_ids':
                docids,


            'doc_model':
                'account.move.line',


            'docs':
                selected_lines,


            'statements':
                statements,


            'date_from':
                date_from,


            'date_to':
                date_to,

        }


class CustomerStatementWizard(models.TransientModel):
    _name = 'customer.statement.wizard'
    _description = 'Customer Statement Wizard'

    partner_id = fields.Many2one('res.partner', string='Partner Name', required=True)
    date_from = fields.Date(string='From', required=True)
    date_to = fields.Date(string='To', required=True)

    def action_print_report(self):
        self.ensure_one()
        data = {
            'wizard_id': self.id,
            'partner_id': self.partner_id.id,
            'date_from': str(self.date_from),
            'date_to': str(self.date_to),
        }
        return self.env.ref(
            'customer_statement_report.action_report_customer_statement'
        ).report_action(self, data=data)

    def _get_statement_lines(self):
        self.ensure_one()
        moves = self.env['account.move'].search([
            ('partner_id', '=', self.partner_id.id),
            ('state', '=', 'posted'),
            ('move_type', 'in', ['out_invoice', 'out_refund']),
            ('invoice_date', '>=', self.date_from),
            ('invoice_date', '<=', self.date_to),
        ], order='invoice_date asc, id asc')

        lines = []
        balance = 0.0

        opening_moves = self.env['account.move'].search([
            ('partner_id', '=', self.partner_id.id),
            ('state', '=', 'posted'),
            ('move_type', 'in', ['out_invoice', 'out_refund']),
            ('invoice_date', '<', self.date_from),
        ])
        for m in opening_moves:
            sign = 1 if m.move_type == 'out_invoice' else -1
            balance += sign * m.amount_total

        opening_balance = balance

        for move in moves:
            sign = 1 if move.move_type == 'out_invoice' else -1
            invoice_lines = move.invoice_line_ids.filtered(
                lambda l: not l.display_type and l.product_id
            )
            if not invoice_lines:
                debit = move.amount_total if sign > 0 else 0
                credit = move.amount_total if sign < 0 else 0
                balance += sign * move.amount_total
                lines.append({
                    'date': move.invoice_date,
                    'transaction': move.name,
                    'product': '',
                    'quantity': 0,
                    'unit_price': 0,
                    'debit': debit,
                    'credit': credit,
                    'balance': balance,
                })
            else:
                for line in invoice_lines:
                    amount = line.price_subtotal
                    debit = amount if sign > 0 else 0
                    credit = amount if sign < 0 else 0
                    balance += sign * amount
                    lines.append({
                        'date': move.invoice_date,
                        'transaction': move.name,
                        'product': line.product_id.display_name,
                        'quantity': line.quantity,
                        'unit_price': line.price_unit,
                        'debit': debit,
                        'credit': credit,
                        'balance': balance,
                    })

        return {
            'opening_balance': opening_balance,
            'lines': lines,
            'closing_balance': balance,
        }