from odoo import models, fields, api
from odoo.tools.float_utils import float_is_zero


class CustomerStatementReportFromLines(models.AbstractModel):
    _name = 'report.customer_statement_report.from_lines'
    _description = 'Customer Statement Report From Journal Items'

    def _get_report_values(self, docids, data=None):

        MoveLine = self.env['account.move.line']

        # =========================================================
        # 1. Journal Items التي قام المستخدم باختيارها
        # =========================================================

        selected_lines = MoveLine.browse(docids).exists()

        # فقط الحركات المالية الخاصة بالعملاء / الموردين
        lines = selected_lines.filtered(
            lambda l:
                l.partner_id
                and l.parent_state == 'posted'
                and l.account_id.account_type in (
                    'asset_receivable',
                    'liability_payable',
                )
        )

        if not lines:
            return {
                'doc_ids': docids,
                'doc_model': 'account.move.line',
                'docs': lines,
                'statements': [],
                'date_from': False,
                'date_to': False,
            }

        # =========================================================
        # 2. فترة التقرير
        # =========================================================

        date_from = min(lines.mapped('date'))
        date_to = max(lines.mapped('date'))

        # =========================================================
        # 3. العملاء
        # =========================================================

        partners = lines.mapped('partner_id')

        statements = []

        for partner in partners:

            # =====================================================
            # 4. حركات العميل داخل الفترة
            # =====================================================

            partner_lines = lines.filtered(
                lambda l: l.partner_id == partner
            ).sorted(
                key=lambda l: (l.date, l.id)
            )

            # =====================================================
            # 5. الرصيد الافتتاحي
            # =====================================================

            opening_lines = MoveLine.search([
                ('partner_id', '=', partner.id),
                ('parent_state', '=', 'posted'),
                (
                    'account_id.account_type',
                    'in',
                    (
                        'asset_receivable',
                        'liability_payable',
                    ),
                ),
                ('date', '<', date_from),
            ])

            opening_balance = sum(
                opening_lines.mapped('balance')
            )

            running_balance = opening_balance

            # =====================================================
            # 6. بيانات التقرير
            # =====================================================

            result_lines = []

            total_qty = 0.0
            total_debit = 0.0
            total_credit = 0.0

            # =====================================================
            # 7. معالجة كل حركة
            # =====================================================

            for line in partner_lines:

                move = line.move_id

                debit = line.debit or 0.0
                credit = line.credit or 0.0
                balance = line.balance or 0.0

                # =================================================
                # الفاتورة / مردود البيع
                # =================================================

                if move.move_type in (
                    'out_invoice',
                    'out_refund',
                ):

                    invoice_lines = move.invoice_line_ids.filtered(
                        lambda il:
                            not il.display_type
                            and il.product_id
                    )

                    # -------------------------------------------------
                    # المنتجات
                    # -------------------------------------------------

                    product_names = []
                    quantities = []
                    unit_prices = []

                    for invoice_line in invoice_lines:

                        if invoice_line.product_id:
                            product_names.append(
                                invoice_line.product_id.display_name
                            )

                        quantities.append(
                            invoice_line.quantity or 0.0
                        )

                        unit_prices.append(
                            invoice_line.price_unit or 0.0
                        )

                    # -------------------------------------------------
                    # Product / Description
                    #
                    # نعرض المنتجات فعلياً بدلاً من line.name
                    # -------------------------------------------------

                    if product_names:
                        product_description = '\n'.join(
                            product_names
                        )
                    else:
                        product_description = (
                            line.name or move.ref or ''
                        )

                    # -------------------------------------------------
                    # Quantity
                    #
                    # مجموع الكميات
                    # -------------------------------------------------

                    quantity = (
                        sum(quantities)
                        if quantities
                        else None
                    )

                    # -------------------------------------------------
                    # Unit Price
                    #
                    # إذا منتج واحد فقط:
                    # نعرض سعره.
                    #
                    # إذا عدة منتجات:
                    # نتركه فارغاً لأنه لا يوجد
                    # Unit Price واحد يمثل الفاتورة.
                    # -------------------------------------------------

                    if len(unit_prices) == 1:
                        unit_price = unit_prices[0]
                    else:
                        unit_price = None

                    # -------------------------------------------------
                    # الرصيد
                    #
                    # مهم جداً:
                    # نستخدم السطر المحاسبي وليس invoice total
                    # -------------------------------------------------

                    running_balance += balance

                    total_debit += debit
                    total_credit += credit

                    if quantity is not None:
                        total_qty += quantity

                    # -------------------------------------------------
                    # سطر الفاتورة
                    # -------------------------------------------------

                    result_lines.append({
                        'date': line.date,
                        'transaction': move.name,
                        'product': product_description,
                        'quantity': quantity,
                        'unit_price': unit_price,
                        'debit': debit,
                        'credit': credit,
                        'balance': running_balance,
                    })

                # =================================================
                # Payment / Entry / Receipt / Credit Note ...
                # =================================================

                else:

                    running_balance += balance

                    total_debit += debit
                    total_credit += credit

                    # -------------------------------------------------
                    # تحديد وصف أفضل للحركة
                    # -------------------------------------------------

                    payment = self.env['account.payment'].search([
                        ('move_id', '=', move.id),
                    ], limit=1)

                    if payment:
                        if payment.memo:
                            description = 'Payment - %s' % payment.memo
                        else:
                            description = 'Payment'
                    else:
                        description = (
                            line.name
                            or move.ref
                            or ''
                        )

                    result_lines.append({
                        'date': line.date,
                        'transaction': move.name,
                        'product': description,
                        'quantity': None,
                        'unit_price': None,
                        'debit': debit,
                        'credit': credit,
                        'balance': running_balance,
                    })

            # =====================================================
            # 8. كشف العميل
            # =====================================================

            statements.append({
                'partner': partner,
                'opening_balance': opening_balance,
                'lines': result_lines,
                'closing_balance': running_balance,
                'total_qty': total_qty,
                'total_debit': total_debit,
                'total_credit': total_credit,
            })

        # =========================================================
        # 9. QWeb values
        # =========================================================

        return {
            'doc_ids': docids,
            'doc_model': 'account.move.line',
            'docs': lines,
            'statements': statements,
            'date_from': date_from,
            'date_to': date_to,
        }



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