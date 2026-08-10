from odoo import models, fields, api


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


class CustomerStatementReport(models.AbstractModel):

    _name = 'report.customer_statement_report.from_lines'
    _description = 'Customer Statement Report'


    @api.model
    def _get_report_values(self, docids, data=None):

        aml = self.env['account.move.line'].browse(docids)

        aml = aml.filtered(
            lambda l:
                l.partner_id
                and l.parent_state == 'posted'
                and l.account_id.account_type in (
                    'asset_receivable',
                    'liability_payable'
                )
        )

        partners = aml.mapped('partner_id')

        date_from = min(aml.mapped('date')) if aml else False
        date_to = max(aml.mapped('date')) if aml else False


        statements = []


        for partner in partners:

            account = (
                partner.property_account_receivable_id
                or partner.property_account_payable_id
            )


            moves = self.env['account.move.line'].search([
                ('partner_id','=',partner.id),
                ('account_id','=',account.id),
                ('parent_state','=','posted'),
                ('date','>=',date_from),
                ('date','<=',date_to),
            ], order='date,id')


            # ==========================
            # Opening Balance
            # ==========================

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


            balance = opening_balance


            result_lines = []

            total_qty = 0
            total_debit = 0
            total_credit = 0


            for line in moves:

                move = line.move_id


                # ==========================
                # Customer Invoice
                # ==========================

                if move.move_type in (
                    'out_invoice',
                    'out_refund'
                ):

                    invoice_lines = move.invoice_line_ids.filtered(
                        lambda x:
                            not x.display_type
                            and x.product_id
                    )


                    for il in invoice_lines:


                        amount = il.price_subtotal


                        if move.move_type == 'out_invoice':

                            debit = amount
                            credit = 0


                        else:

                            debit = 0
                            credit = amount



                        balance += debit - credit


                        total_qty += il.quantity
                        total_debit += debit
                        total_credit += credit


                        result_lines.append({

                            'date': line.date,

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


                # ==========================
                # Payment / Journal Entry
                # ==========================

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


        return {

            'doc_ids':
                docids,

            'doc_model':
                'account.move.line',

            'docs':
                aml,

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