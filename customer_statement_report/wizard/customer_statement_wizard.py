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





# class CustomerStatementReport(models.AbstractModel):
#     _name = 'report.customer_statement_report.from_lines'
#     _description = 'Customer Statement Report'

#     @api.model
#     def _get_report_values(self, docids, data=None):

#         _logger.warning("")
#         _logger.warning("========== CUSTOMER STATEMENT START ==========")
#         _logger.warning("DOCIDS: %s", docids)

#         # ==========================================================
#         # 1. Selected Journal Items
#         # ==========================================================

#         selected_lines = self.env['account.move.line'].browse(docids).filtered(
#             lambda l:
#                 l.exists()
#                 and l.partner_id
#                 and l.parent_state == 'posted'
#                 and l.account_id.account_type in (
#                     'asset_receivable',
#                     'liability_payable',
#                 )
#         )

#         _logger.warning(
#             "SELECTED RECEIVABLE LINES = %s",
#             len(selected_lines)
#         )

#         if not selected_lines:
#             _logger.warning("NO VALID SELECTED LINES")

#             return {
#                 'doc_ids': docids,
#                 'doc_model': 'account.move.line',
#                 'docs': selected_lines,
#                 'statements': [],
#                 'date_from': False,
#                 'date_to': False,
#             }

#         # ==========================================================
#         # 2. Partners
#         # ==========================================================

#         partners = selected_lines.mapped('partner_id')

#         _logger.warning(
#             "PARTNERS: %s",
#             partners.mapped('name')
#         )

#         # ==========================================================
#         # 3. Date Range
#         # ==========================================================

#         dates = selected_lines.mapped('date')

#         date_from = min(dates) if dates else False
#         date_to = max(dates) if dates else False

#         _logger.warning(
#             "DATE RANGE %s -> %s",
#             date_from,
#             date_to
#         )

#         # ==========================================================
#         # 4. Load ALL receivable/payable lines for selected
#         #    partners and selected period
#         # ==========================================================

#         aml = self.env['account.move.line'].search([
#             ('partner_id', 'in', partners.ids),
#             ('parent_state', '=', 'posted'),
#             ('account_id.account_type', 'in', (
#                 'asset_receivable',
#                 'liability_payable',
#             )),
#             ('date', '>=', date_from),
#             ('date', '<=', date_to),
#         ], order='date,id')

#         _logger.warning(
#             "ALL RECEIVABLE/PAYABLE LINES = %s",
#             len(aml)
#         )

#         statements = []

#         # ==========================================================
#         # 5. Process each partner
#         # ==========================================================

#         for partner in partners:

#             _logger.warning("")
#             _logger.warning(
#                 "PROCESS PARTNER %s",
#                 partner.name
#             )

#             # ======================================================
#             # Customer Receivable Account
#             # ======================================================

#             account = partner.property_account_receivable_id

#             if not account:
#                 account = partner.property_account_payable_id

#             if not account:
#                 _logger.warning(
#                     "NO RECEIVABLE/PAYABLE ACCOUNT FOR PARTNER %s",
#                     partner.name
#                 )

#                 continue

#             _logger.warning(
#                 "PARTNER ACCOUNT = %s / %s",
#                 account.code,
#                 account.name
#             )

#             # ======================================================
#             # 6. Partner Moves
#             # ======================================================

#             moves = aml.filtered(
#                 lambda l:
#                     l.partner_id == partner
#                     and l.account_id == account
#             )

#             _logger.warning(
#                 "MOVES COUNT = %s",
#                 len(moves)
#             )

#             # ======================================================
#             # 7. Opening Balance
#             # ======================================================

#             opening_lines = self.env['account.move.line'].search([
#                 ('partner_id', '=', partner.id),
#                 ('account_id', '=', account.id),
#                 ('parent_state', '=', 'posted'),
#                 ('date', '<', date_from),
#             ])

#             opening_debit = sum(opening_lines.mapped('debit'))
#             opening_credit = sum(opening_lines.mapped('credit'))

#             opening_balance = opening_debit - opening_credit

#             _logger.warning(
#                 "OPENING BALANCE = %s",
#                 opening_balance
#             )

#             # ======================================================
#             # Running Balance
#             # ======================================================

#             balance = opening_balance

#             result_lines = []

#             total_qty = 0.0
#             total_debit = 0.0
#             total_credit = 0.0

#             # ======================================================
#             # 8. Process Journal Items
#             # ======================================================

#             for line in moves:

#                 move = line.move_id

#                 _logger.warning(
#                     "PROCESS MOVE %s TYPE %s AML=%s",
#                     move.name,
#                     move.move_type,
#                     line.id
#                 )

#                 # ==================================================
#                 # Customer Invoice / Refund
#                 # ==================================================

#                 if move.move_type in (
#                     'out_invoice',
#                     'out_refund',
#                 ):

#                     # IMPORTANT:
#                     # In this database product invoice lines have:
#                     #
#                     # display_type = 'product'
#                     #
#                     # Therefore DO NOT use:
#                     #
#                     #     not x.display_type
#                     #
#                     # because that removes all product lines.
#                     #
#                     invoice_lines = move.invoice_line_ids.filtered(
#                         lambda x:
#                             x.display_type == 'product'
#                             and x.product_id
#                     )

#                     _logger.warning(
#                         "INVOICE %s PRODUCT LINES = %s",
#                         move.name,
#                         len(invoice_lines)
#                     )

#                     # ==================================================
#                     # If invoice has product lines
#                     # ==================================================

#                     if invoice_lines:

#                         for il in invoice_lines:

#                             amount = il.price_subtotal or 0.0

#                             quantity = il.quantity or 0.0
#                             unit_price = il.price_unit or 0.0

#                             # ------------------------------------------
#                             # Customer Invoice
#                             # ------------------------------------------

#                             if move.move_type == 'out_invoice':

#                                 debit = amount
#                                 credit = 0.0

#                             # ------------------------------------------
#                             # Customer Refund
#                             # ------------------------------------------

#                             else:

#                                 debit = 0.0
#                                 credit = amount

#                             # ------------------------------------------
#                             # Running Balance
#                             # ------------------------------------------

#                             balance += debit - credit

#                             # ------------------------------------------
#                             # Totals
#                             # ------------------------------------------

#                             total_qty += quantity
#                             total_debit += debit
#                             total_credit += credit

#                             _logger.warning(
#                                 """
#                                 PRODUCT LINE
#                                 MOVE=%s
#                                 AML=%s
#                                 PRODUCT=%s
#                                 PRODUCT_ID=%s
#                                 QTY=%s
#                                 UNIT_PRICE=%s
#                                 SUBTOTAL=%s
#                                 DEBIT=%s
#                                 CREDIT=%s
#                                 BALANCE=%s
#                                 """,
#                                 move.name,
#                                 il.id,
#                                 il.product_id.display_name,
#                                 il.product_id.id,
#                                 quantity,
#                                 unit_price,
#                                 amount,
#                                 debit,
#                                 credit,
#                                 balance,
#                             )

#                             result_lines.append({
#                                 'date': line.date,

#                                 'transaction': move.name,

#                                 'product':
#                                     il.product_id.display_name,

#                                 'quantity':
#                                     quantity,

#                                 'unit_price':
#                                     unit_price,

#                                 'debit':
#                                     debit,

#                                 'credit':
#                                     credit,

#                                 'balance':
#                                     balance,
#                             })

#                     # ==================================================
#                     # Invoice has no product lines
#                     #
#                     # This can happen with manually created invoices
#                     # or invoices whose accounting entry has no
#                     # invoice_line_ids.
#                     #
#                     # In this case use the receivable AML itself.
#                     # ==================================================

#                     else:

#                         debit = line.debit or 0.0
#                         credit = line.credit or 0.0

#                         balance += debit - credit

#                         total_debit += debit
#                         total_credit += credit

#                         _logger.warning(
#                             """
#                             INVOICE WITHOUT PRODUCT LINES
#                             MOVE=%s
#                             AML=%s
#                             NAME=%s
#                             DEBIT=%s
#                             CREDIT=%s
#                             BALANCE=%s
#                             """,
#                             move.name,
#                             line.id,
#                             line.name,
#                             debit,
#                             credit,
#                             balance,
#                         )

#                         result_lines.append({
#                             'date':
#                                 line.date,

#                             'transaction':
#                                 move.name,

#                             'product':
#                                 line.name or move.ref or '',

#                             'quantity':
#                                 None,

#                             'unit_price':
#                                 None,

#                             'debit':
#                                 debit,

#                             'credit':
#                                 credit,

#                             'balance':
#                                 balance,
#                         })

#                 # ==================================================
#                 # Payment / Journal Entry / Other
#                 # ==================================================

#                 else:

#                     debit = line.debit or 0.0
#                     credit = line.credit or 0.0

#                     balance += debit - credit

#                     total_debit += debit
#                     total_credit += credit

#                     _logger.warning(
#                         """
#                         JOURNAL/PAYMENT LINE
#                         MOVE=%s
#                         AML=%s
#                         NAME=%s
#                         DEBIT=%s
#                         CREDIT=%s
#                         BALANCE=%s
#                         """,
#                         move.name,
#                         line.id,
#                         line.name,
#                         debit,
#                         credit,
#                         balance,
#                     )

#                     result_lines.append({
#                         'date':
#                             line.date,

#                         'transaction':
#                             move.name,

#                         'product':
#                             line.name or move.ref or '',

#                         'quantity':
#                             None,

#                         'unit_price':
#                             None,

#                         'debit':
#                             debit,

#                         'credit':
#                             credit,

#                         'balance':
#                             balance,
#                     })

#             # ======================================================
#             # 9. Statement
#             # ======================================================

#             _logger.warning(
#                 """
#                 RESULT
#                 PARTNER=%s
#                 LINES=%s
#                 QTY=%s
#                 DEBIT=%s
#                 CREDIT=%s
#                 OPENING=%s
#                 BALANCE=%s
#                 """,
#                 partner.name,
#                 len(result_lines),
#                 total_qty,
#                 total_debit,
#                 total_credit,
#                 opening_balance,
#                 balance,
#             )

#             statements.append({
#                 'partner':
#                     partner,

#                 'opening_balance':
#                     opening_balance,

#                 'lines':
#                     result_lines,

#                 'closing_balance':
#                     balance,

#                 'total_qty':
#                     total_qty,

#                 'total_debit':
#                     total_debit,

#                 'total_credit':
#                     total_credit,
#             })

#         # ==========================================================
#         # 10. Final Debug
#         # ==========================================================

#         _logger.warning(
#             "STATEMENTS COUNT = %s",
#             len(statements)
#         )

#         for statement in statements:

#             _logger.warning(
#                 "STATEMENT PARTNER=%s LINES=%s",
#                 statement['partner'].name,
#                 len(statement['lines'])
#             )

#             for report_line in statement['lines']:

#                 _logger.warning(
#                     """
#                     REPORT LINE
#                     DATE=%s
#                     TRANSACTION=%s
#                     PRODUCT=%s
#                     QTY=%s
#                     PRICE=%s
#                     DEBIT=%s
#                     CREDIT=%s
#                     BALANCE=%s
#                     """,
#                     report_line['date'],
#                     report_line['transaction'],
#                     report_line['product'],
#                     report_line['quantity'],
#                     report_line['unit_price'],
#                     report_line['debit'],
#                     report_line['credit'],
#                     report_line['balance'],
#                 )

#         _logger.warning(
#             "========== CUSTOMER STATEMENT END =========="
#         )
#         _logger.warning("")

#         # ==========================================================
#         # 11. Report Values
#         # ==========================================================

#         return {
#             'doc_ids':
#                 docids,

#             'doc_model':
#                 'account.move.line',

#             'docs':
#                 selected_lines,

#             'statements':
#                 statements,

#             'date_from':
#                 date_from,

#             'date_to':
#                 date_to,
#         }



from odoo import api, models
import logging


_logger = logging.getLogger(__name__)


class CustomerStatementReport(models.AbstractModel):
    _name = 'report.customer_statement_report.from_lines'
    _description = 'Customer Statement Report'

    @api.model
    def _get_report_values(self, docids, data=None):

        _logger.info("")
        _logger.info("========== CUSTOMER STATEMENT START ==========")
        _logger.info("DOCIDS: %s", docids)

        # ==========================================================
        # 1. Selected Journal Items
        # ==========================================================

        selected_lines = self.env['account.move.line'].browse(docids).filtered(
            lambda l:
                l.exists()
                and l.partner_id
                and l.parent_state == 'posted'
                and l.account_id.account_type in (
                    'asset_receivable',
                    'liability_payable',
                )
        )

        _logger.info(
            "SELECTED RECEIVABLE/PAYABLE LINES = %s",
            len(selected_lines)
        )

        if not selected_lines:
            _logger.warning("NO VALID SELECTED LINES")

            return {
                'doc_ids': docids,
                'doc_model': 'account.move.line',
                'docs': selected_lines,
                'statements': [],
                'date_from': False,
                'date_to': False,
            }

        # ==========================================================
        # 2. Partners
        # ==========================================================

        partners = selected_lines.mapped('partner_id')

        _logger.info(
            "PARTNERS: %s",
            partners.mapped('name')
        )

        # ==========================================================
        # 3. Date Range
        # ==========================================================

        dates = selected_lines.mapped('date')

        date_from = min(dates) if dates else False
        date_to = max(dates) if dates else False

        _logger.info(
            "DATE RANGE: %s -> %s",
            date_from,
            date_to
        )

        # ==========================================================
        # 4. Statements
        # ==========================================================

        statements = []

        # ==========================================================
        # 5. Process each partner
        # ==========================================================

        for partner in partners:

            _logger.info("")
            _logger.info(
                "=================================================="
            )
            _logger.info(
                "PROCESS PARTNER: %s (%s)",
                partner.name,
                partner.id
            )
            _logger.info(
                "=================================================="
            )

            # ======================================================
            # 5.1 Determine company
            # ======================================================

            partner_lines = selected_lines.filtered(
                lambda l: l.partner_id == partner
            )

            company = (
                partner_lines[:1].company_id
                or self.env.company
            )

            _logger.info(
                "COMPANY: %s (%s)",
                company.name,
                company.id
            )

            # ======================================================
            # 5.2 Determine Partner Account
            # ======================================================

            partner_company = partner.with_company(company)

            receivable_account = (
                partner_company.property_account_receivable_id
            )

            payable_account = (
                partner_company.property_account_payable_id
            )

            # ------------------------------------------------------
            # Select the account according to the selected lines
            # ------------------------------------------------------

            selected_accounts = partner_lines.mapped('account_id')

            account = selected_accounts.filtered(
                lambda a:
                    a.account_type in (
                        'asset_receivable',
                        'liability_payable',
                    )
            )[:1]

            if not account:
                account = (
                    receivable_account
                    or payable_account
                )

            if not account:
                _logger.warning(
                    "NO RECEIVABLE/PAYABLE ACCOUNT FOR PARTNER %s",
                    partner.name
                )
                continue

            _logger.info(
                "PARTNER ACCOUNT: %s / %s / TYPE=%s",
                account.code,
                account.name,
                account.account_type
            )

            # ======================================================
            # 6. Load ALL partner lines before/current period
            #
            # We need:
            #
            #     Before date_from -> Opening Balance
            #
            #     date_from -> date_to -> Current Statement
            #
            # ======================================================

            opening_lines = self.env['account.move.line'].search([
                ('partner_id', '=', partner.id),
                ('company_id', '=', company.id),
                ('account_id', '=', account.id),
                ('parent_state', '=', 'posted'),
                ('date', '<', date_from),
            ])

            moves = self.env['account.move.line'].search([
                ('partner_id', '=', partner.id),
                ('company_id', '=', company.id),
                ('account_id', '=', account.id),
                ('parent_state', '=', 'posted'),
                ('date', '>=', date_from),
                ('date', '<=', date_to),
            ], order='date asc, id asc')

            _logger.info(
                "OPENING LINES: %s",
                len(opening_lines)
            )

            _logger.info(
                "PERIOD LINES: %s",
                len(moves)
            )

            # ======================================================
            # 7. Opening Balance
            # ======================================================

            opening_debit = sum(
                opening_lines.mapped('debit')
            )

            opening_credit = sum(
                opening_lines.mapped('credit')
            )

            # ------------------------------------------------------
            # Accounting formula:
            #
            # Receivable:
            #
            # Debit  = Customer owes more
            # Credit = Customer paid / owes less
            #
            # Balance = Debit - Credit
            # ------------------------------------------------------

            if account.account_type == 'asset_receivable':

                opening_balance = (
                    opening_debit
                    - opening_credit
                )

            # ------------------------------------------------------
            # Payable:
            #
            # For a supplier account the natural balance is:
            #
            # Credit - Debit
            #
            # This makes positive balance mean:
            # "We owe the supplier"
            # ------------------------------------------------------

            else:

                opening_balance = (
                    opening_credit
                    - opening_debit
                )

            _logger.info(
                "OPENING DEBIT  = %s",
                opening_debit
            )

            _logger.info(
                "OPENING CREDIT = %s",
                opening_credit
            )

            _logger.info(
                "OPENING BALANCE = %s",
                opening_balance
            )

            # ======================================================
            # 8. Running Balance
            # ======================================================

            balance = opening_balance

            result_lines = []

            total_qty = 0.0
            total_debit = 0.0
            total_credit = 0.0

            # ======================================================
            # 9. Process Journal Items
            # ======================================================

            for line in moves:

                move = line.move_id

                # ==================================================
                # REAL ACCOUNTING VALUES
                #
                # IMPORTANT:
                #
                # Debit/Credit MUST come from account.move.line.
                #
                # DO NOT use invoice line price_subtotal here.
                # ==================================================

                debit = line.debit or 0.0
                credit = line.credit or 0.0

                # ==================================================
                # Calculate movement
                # ==================================================

                if account.account_type == 'asset_receivable':

                    movement = debit - credit

                else:

                    movement = credit - debit

                balance += movement

                total_debit += debit
                total_credit += credit

                # ==================================================
                # Basic transaction information
                # ==================================================

                transaction = (
                    move.name
                    or line.move_name
                    or ''
                )

                # ==================================================
                # Default description
                # ==================================================

                description = (
                    line.name
                    or move.ref
                    or move.name
                    or ''
                )

                quantity = None
                unit_price = None

                # ==================================================
                # Invoice / Refund
                # ==================================================

                if move.move_type in (
                    'out_invoice',
                    'out_refund',
                    'in_invoice',
                    'in_refund',
                ):

                    invoice_lines = move.invoice_line_ids.filtered(
                        lambda x:
                            x.display_type == 'product'
                            and x.product_id
                    )

                    _logger.info(
                        "MOVE %s PRODUCT LINES = %s",
                        move.name,
                        len(invoice_lines)
                    )

                    if invoice_lines:

                        # --------------------------------------------------
                        # IMPORTANT:
                        #
                        # The accounting amount remains:
                        #
                        #       line.debit
                        #       line.credit
                        #
                        # Product data is informational only.
                        # --------------------------------------------------

                        if len(invoice_lines) == 1:

                            invoice_line = invoice_lines[0]

                            description = (
                                invoice_line.product_id.display_name
                            )

                            quantity = (
                                invoice_line.quantity or 0.0
                            )

                            unit_price = (
                                invoice_line.price_unit or 0.0
                            )

                        else:

                            # --------------------------------------------------
                            # Multiple products
                            #
                            # Since this AML represents ONE accounting
                            # movement, we don't create multiple accounting
                            # movements from price_subtotal.
                            #
                            # Instead we show the products as description.
                            # --------------------------------------------------

                            product_names = invoice_lines.mapped(
                                'product_id.display_name'
                            )

                            description = '\n'.join(
                                product_names
                            )

                            quantity = sum(
                                invoice_lines.mapped('quantity')
                            )

                            # Do not show a misleading unit price
                            unit_price = None

                        # --------------------------------------------------
                        # Quantity is informational only.
                        # --------------------------------------------------

                        total_qty += quantity or 0.0

                    else:

                        description = (
                            line.name
                            or move.ref
                            or move.name
                            or ''
                        )

                # ==================================================
                # Payment / Journal Entry / Other
                #
                # DO NOT use:
                #
                #     move.payment_id
                #
                # because account.move has no such field in Odoo 19.
                #
                # The accounting AML itself is enough.
                # ==================================================

                else:

                    description = (
                        line.name
                        or move.ref
                        or move.name
                        or ''
                    )

                # ==================================================
                # Logging
                # ==================================================

                _logger.info(
                    """
                    REPORT LINE

                    PARTNER       = %s
                    DATE          = %s
                    MOVE          = %s
                    MOVE TYPE     = %s
                    AML ID        = %s

                    ACCOUNT       = %s
                    ACCOUNT TYPE  = %s

                    DEBIT         = %s
                    CREDIT        = %s
                    MOVEMENT      = %s
                    BALANCE       = %s

                    DESCRIPTION   = %s
                    QTY           = %s
                    UNIT PRICE    = %s
                    """,
                    partner.name,
                    line.date,
                    move.name,
                    move.move_type,
                    line.id,

                    line.account_id.code,
                    line.account_id.account_type,

                    debit,
                    credit,
                    movement,
                    balance,

                    description,
                    quantity,
                    unit_price,
                )

                # ==================================================
                # Add Report Line
                # ==================================================

                result_lines.append({

                    'date':
                        line.date,

                    'transaction':
                        transaction,

                    'product':
                        description,

                    'quantity':
                        quantity,

                    'unit_price':
                        unit_price,

                    'debit':
                        debit,

                    'credit':
                        credit,

                    'balance':
                        balance,

                })

            # ======================================================
            # 10. Final Totals
            # ======================================================

            _logger.info("")
            _logger.info(
                "========== PARTNER RESULT =========="
            )

            _logger.info(
                "PARTNER        = %s",
                partner.name
            )

            _logger.info(
                "LINES          = %s",
                len(result_lines)
            )

            _logger.info(
                "TOTAL QTY      = %s",
                total_qty
            )

            _logger.info(
                "TOTAL DEBIT    = %s",
                total_debit
            )

            _logger.info(
                "TOTAL CREDIT   = %s",
                total_credit
            )

            _logger.info(
                "OPENING        = %s",
                opening_balance
            )

            _logger.info(
                "CLOSING        = %s",
                balance
            )

            # ======================================================
            # 11. Statement
            # ======================================================

            statements.append({

                'partner':
                    partner,

                'company':
                    company,

                'account':
                    account,

                'opening_balance':
                    opening_balance,

                'opening_debit':
                    opening_debit,

                'opening_credit':
                    opening_credit,

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

        # ==========================================================
        # 12. Final Debug
        # ==========================================================

        _logger.info("")
        _logger.info(
            "========== CUSTOMER STATEMENT END =========="
        )

        _logger.info(
            "STATEMENTS COUNT = %s",
            len(statements)
        )

        for statement in statements:

            _logger.info(
                "PARTNER=%s | OPENING=%s | DEBIT=%s | CREDIT=%s | CLOSING=%s",
                statement['partner'].name,
                statement['opening_balance'],
                statement['total_debit'],
                statement['total_credit'],
                statement['closing_balance'],
            )

        # ==========================================================
        # 13. Report Values
        # ==========================================================

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