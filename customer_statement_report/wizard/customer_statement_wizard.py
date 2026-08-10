from odoo import models, fields, api




class CustomerStatementReportFromLines(models.AbstractModel):
    _name = 'report.customer_statement_report.from_lines'
    _description = 'Customer Statement Report From Journal Items'

    def _get_report_values(self, docids, data=None):
        MoveLine = self.env['account.move.line']

        # ---------------------------------------------------------
        # 1) السطور التي تم اختيارها من Journal Items
        # ---------------------------------------------------------
        selected_lines = MoveLine.browse(docids).exists()

        # نحتاج فقط إلى سطور العملاء:
        # Receivable / Payable
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

        # ---------------------------------------------------------
        # 2) الفترة الزمنية للتقرير
        # ---------------------------------------------------------
        date_from = min(lines.mapped('date'))
        date_to = max(lines.mapped('date'))

        # ---------------------------------------------------------
        # 3) العملاء
        # ---------------------------------------------------------
        partners = lines.mapped('partner_id')

        statements = []

        for partner in partners:

            # -----------------------------------------------------
            # 4) حركات العميل ضمن الفترة
            # -----------------------------------------------------
            partner_lines = lines.filtered(
                lambda l: l.partner_id == partner
            ).sorted(
                key=lambda l: (l.date, l.id)
            )

            # -----------------------------------------------------
            # 5) الرصيد الافتتاحي
            #
            # كل حركات العميل قبل date_from
            # -----------------------------------------------------
            opening_lines = MoveLine.search([
                ('partner_id', '=', partner.id),
                ('parent_state', '=', 'posted'),
                (
                    'account_id.account_type',
                    'in',
                    ('asset_receivable', 'liability_payable'),
                ),
                ('date', '<', date_from),
            ])

            opening_balance = sum(opening_lines.mapped('balance'))

            # الرصيد الجاري يبدأ من الرصيد الافتتاحي
            running_balance = opening_balance

            # -----------------------------------------------------
            # 6) بيانات التقرير
            # -----------------------------------------------------
            result_lines = []

            total_qty = 0.0
            total_debit = 0.0
            total_credit = 0.0

            # -----------------------------------------------------
            # 7) معالجة كل حركة
            # -----------------------------------------------------
            for line in partner_lines:

                move = line.move_id

                # =================================================
                # الحالة الأولى:
                # فاتورة بيع / مردود بيع
                # =================================================
                if move.move_type in ('out_invoice', 'out_refund'):

                    invoice_lines = move.invoice_line_ids.filtered(
                        lambda il:
                            not il.display_type
                            and il.product_id
                    )

                    # -------------------------------------------------
                    # نريد هنا "حركة العميل" نفسها وليس Sales Account.
                    #
                    # مثال:
                    #
                    # INV/2026/00044
                    # Accounts Receivable
                    # Debit = 39,424,000
                    #
                    # لذلك نستخدم line.debit / line.credit
                    # وليس il.price_subtotal.
                    # -------------------------------------------------

                    if invoice_lines:

                        # الوصف الذي يظهر في كشف المدير:
                        # S00072 - INV/2026/00044
                        description = line.name or ''

                        # الحركة المحاسبية الفعلية للعميل
                        debit = line.debit
                        credit = line.credit

                        # تحديث الرصيد
                        running_balance += line.balance

                        total_debit += debit
                        total_credit += credit

                        # -------------------------------------------------
                        # الكمية:
                        #
                        # إذا كانت الفاتورة تحتوي أكثر من منتج،
                        # لا نكرر المبلغ المحاسبي لكل منتج.
                        #
                        # التقرير الحالي المطلوب يشبه كشف الحساب
                        # وليس فاتورة تفصيلية.
                        # لذلك نجمع الكمية فقط.
                        # -------------------------------------------------
                        quantity = sum(
                            invoice_lines.mapped('quantity')
                        )

                        total_qty += quantity

                        # -------------------------------------------------
                        # سعر الوحدة:
                        #
                        # إذا كان هناك منتج واحد فقط نعرض سعره.
                        # إذا كانت عدة منتجات نتركه فارغًا لأن
                        # وضع سعر واحد سيكون مضللًا.
                        # -------------------------------------------------
                        unit_price = (
                            invoice_lines[0].price_unit
                            if len(invoice_lines) == 1
                            else None
                        )

                        # -------------------------------------------------
                        # اسم المنتج:
                        #
                        # في التقرير الذي طلبته أنت:
                        #
                        # S00072 - INV/2026/00044
                        #
                        # وليس اسم المنتج.
                        # -------------------------------------------------
                        product_description = description

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

                    else:
                        # فاتورة بدون Product Line
                        running_balance += line.balance

                        total_debit += line.debit
                        total_credit += line.credit

                        result_lines.append({
                            'date': line.date,
                            'transaction': move.name,
                            'product': line.name or '',
                            'quantity': None,
                            'unit_price': None,
                            'debit': line.debit,
                            'credit': line.credit,
                            'balance': running_balance,
                        })

                # =================================================
                # الحالة الثانية:
                # أي حركة أخرى:
                #
                # Payment
                # Receipt
                # Manual Entry
                # Credit Note
                # إلخ
                # =================================================
                else:

                    running_balance += line.balance

                    total_debit += line.debit
                    total_credit += line.credit

                    result_lines.append({
                        'date': line.date,
                        'transaction': move.name,
                        'product': line.name or '',
                        'quantity': None,
                        'unit_price': None,
                        'debit': line.debit,
                        'credit': line.credit,
                        'balance': running_balance,
                    })

            # -----------------------------------------------------
            # 8) إضافة كشف العميل
            # -----------------------------------------------------
            statements.append({
                'partner': partner,
                'opening_balance': opening_balance,
                'lines': result_lines,
                'closing_balance': running_balance,
                'total_qty': total_qty,
                'total_debit': total_debit,
                'total_credit': total_credit,
            })

        # ---------------------------------------------------------
        # 9) البيانات التي تصل إلى QWeb
        # ---------------------------------------------------------
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