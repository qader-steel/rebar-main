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






# # -*- coding: utf-8 -*-
# import logging
# from odoo import api, models

# _logger = logging.getLogger(__name__)


# class CustomerStatementReport(models.AbstractModel):
#     _name = 'report.customer_statement_report.from_lines'
#     _description = 'Customer Statement Report'

#     @api.model
#     def _get_report_values(self, docids, data=None):

#         _logger.warning("")
#         _logger.warning("========== CUSTOMER STATEMENT START ==========")
#         _logger.warning("DOCIDS RAW = %s", docids)
#         _logger.warning("DATA PASSED = %s", data)

#         # ==========================================================
#         # 1. Selected Journal Items
#         # ==========================================================

#         all_selected = self.env['account.move.line'].browse(docids)

#         _logger.warning(
#             "BROWSED LINES (before filter) = %s -> %s",
#             len(all_selected),
#             all_selected.ids
#         )

#         selected_lines = all_selected.filtered(
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
#             "SELECTED RECEIVABLE/PAYABLE LINES (after filter) = %s -> %s",
#             len(selected_lines),
#             selected_lines.ids
#         )

#         # log rejected lines to know WHY they were dropped
#         rejected = all_selected - selected_lines
#         for rl in rejected:
#             _logger.warning(
#                 "REJECTED LINE id=%s exists=%s partner=%s state=%s acc_type=%s",
#                 rl.id,
#                 rl.exists(),
#                 rl.partner_id.name if rl.exists() and rl.partner_id else None,
#                 rl.parent_state if rl.exists() else None,
#                 rl.account_id.account_type if rl.exists() else None,
#             )

#         if not selected_lines:
#             _logger.warning("NO VALID SELECTED LINES - RETURNING EMPTY")
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
#             "PARTNERS (%s) = %s",
#             len(partners),
#             partners.mapped('name')
#         )

#         # ==========================================================
#         # 3. Date Range
#         #
#         # IMPORTANT:
#         # date_from / date_to are derived from the MIN/MAX date of the
#         # manually selected lines (docids). This is NOT necessarily the
#         # same date range the user sees/expects in the UI filter
#         # (e.g. wizard date_from/date_to). If the report balance looks
#         # wrong vs. the UI, check whether `data` should be used instead,
#         # e.g.:
#         #
#         #   date_from = data.get('date_from') if data else min(dates)
#         #   date_to   = data.get('date_to') if data else max(dates)
#         # ==========================================================

#         dates = selected_lines.mapped('date')

#         date_from = min(dates) if dates else False
#         date_to = max(dates) if dates else False

#         _logger.warning(
#             "DATE RANGE DERIVED FROM SELECTED LINES: %s -> %s",
#             date_from,
#             date_to
#         )

#         if data and data.get('date_from'):
#             _logger.warning(
#                 "NOTE: 'data' contains date_from=%s date_to=%s "
#                 "BUT CODE IS CURRENTLY USING MIN/MAX FROM SELECTED LINES INSTEAD. "
#                 "This may be the root cause of Initial Balance mismatch vs UI.",
#                 data.get('date_from'),
#                 data.get('date_to'),
#             )

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
#         ], order='date asc, move_name asc, id asc')

#         _logger.warning(
#             "ALL RECEIVABLE/PAYABLE LINES IN RANGE = %s -> ids=%s",
#             len(aml),
#             aml.ids
#         )

#         statements = []

#         # ==========================================================
#         # 5. Process each partner
#         # ==========================================================

#         for partner in partners:

#             _logger.warning("")
#             _logger.warning("---------------------------------------------")
#             _logger.warning("PROCESS PARTNER = %s (id=%s)", partner.name, partner.id)
#             _logger.warning("---------------------------------------------")

#             # ======================================================
#             # Customer Receivable Account
#             # ======================================================

#             account = partner.property_account_receivable_id

#             if not account:
#                 account = partner.property_account_payable_id

#             if not account:
#                 _logger.warning(
#                     "NO RECEIVABLE/PAYABLE ACCOUNT FOR PARTNER %s - SKIPPING",
#                     partner.name
#                 )
#                 continue

#             _logger.warning(
#                 "PARTNER DEFAULT ACCOUNT = %s / %s (id=%s)",
#                 account.code,
#                 account.name,
#                 account.id,
#             )

#             # ======================================================
#             # IMPORTANT CHECK:
#             # The partner may have historical AML posted against a
#             # DIFFERENT receivable/payable account than the current
#             # property_account_receivable_id (e.g. account changed
#             # over time, or partner used both receivable and payable
#             # accounts). Using only ONE fixed account here can silently
#             # drop lines that exist in the UI ledger (which usually
#             # shows ALL receivable/payable accounts for the partner).
#             # ======================================================

#             all_partner_accounts = aml.filtered(
#                 lambda l: l.partner_id == partner
#             ).mapped('account_id')

#             if len(all_partner_accounts) > 1 or (
#                 all_partner_accounts and account not in all_partner_accounts
#             ):
#                 _logger.warning(
#                     "WARNING: PARTNER %s HAS MOVES ON MULTIPLE/DIFFERENT ACCOUNTS "
#                     "IN THIS PERIOD: %s (code: %s) BUT REPORT ONLY USES %s. "
#                     "THIS CAN EXPLAIN A BALANCE MISMATCH VS THE UI LEDGER.",
#                     partner.name,
#                     all_partner_accounts.mapped('name'),
#                     all_partner_accounts.mapped('code'),
#                     account.code,
#                 )

#             # ======================================================
#             # 6. Partner Moves (only on the resolved account)
#             # ======================================================

#             moves = aml.filtered(
#                 lambda l:
#                     l.partner_id == partner
#                     and l.account_id == account
#             )

#             _logger.warning(
#                 "MOVES COUNT FOR PARTNER ON ACCOUNT %s = %s -> ids=%s",
#                 account.code,
#                 len(moves),
#                 moves.ids,
#             )

#             # ======================================================
#             # 7. Opening Balance
#             #
#             # Computed on the SAME account used above, for all posted
#             # lines strictly before date_from.
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
#                 "OPENING LINES COUNT = %s (before %s)",
#                 len(opening_lines),
#                 date_from,
#             )
#             _logger.warning(
#                 "OPENING DEBIT = %s | OPENING CREDIT = %s | OPENING BALANCE = %s",
#                 opening_debit,
#                 opening_credit,
#                 opening_balance,
#             )

#             if opening_balance == 0 and len(opening_lines) == 0:
#                 _logger.warning(
#                     "OPENING BALANCE IS ZERO BECAUSE THERE ARE NO POSTED LINES "
#                     "STRICTLY BEFORE date_from=%s FOR ACCOUNT %s. "
#                     "IF THE UI SHOWS A NON-ZERO STARTING BALANCE, VERIFY THAT "
#                     "date_from USED HERE MATCHES THE DATE FILTER USED IN THE UI.",
#                     date_from,
#                     account.code,
#                 )

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
#                     "PROCESS MOVE=%s TYPE=%s AML_ID=%s AML_DEBIT=%s AML_CREDIT=%s",
#                     move.name,
#                     move.move_type,
#                     line.id,
#                     line.debit,
#                     line.credit,
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
#                     #     display_type = 'product'
#                     # Therefore DO NOT use `not x.display_type`.
#                     #
#                     # ALSO IMPORTANT (FIX):
#                     # invoice_line_ids has NO GUARANTEED ORDER matching
#                     # what the user sees on the invoice form. We MUST
#                     # sort explicitly by sequence, then id, otherwise
#                     # the running balance per product line will not
#                     # match the UI (this was the root cause of the
#                     # balance mismatch you observed).
#                     invoice_lines = move.invoice_line_ids.filtered(
#                         lambda x:
#                             x.display_type == 'product'
#                             and x.product_id
#                     ).sorted(key=lambda x: (x.sequence, x.id))

#                     _logger.warning(
#                         "INVOICE %s PRODUCT LINES = %s (order used: sequence,id) -> ids=%s seq=%s",
#                         move.name,
#                         len(invoice_lines),
#                         invoice_lines.ids,
#                         invoice_lines.mapped('sequence'),
#                     )

#                     # sanity check: does subtotal sum match the AML amount?
#                     lines_subtotal_sum = sum(invoice_lines.mapped('price_subtotal'))
#                     _logger.warning(
#                         "CHECK: SUM(invoice_lines.price_subtotal)=%s vs AML line.debit/credit=%s/%s "
#                         "(should be roughly equal, diff means product lines don't fully "
#                         "represent this AML)",
#                         lines_subtotal_sum,
#                         line.debit,
#                         line.credit,
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
#                             # Customer Invoice -> partner owes us -> Debit
#                             # Customer Refund  -> we owe partner   -> Credit
#                             # ------------------------------------------

#                             if move.move_type == 'out_invoice':
#                                 debit = amount
#                                 credit = 0.0
#                             else:
#                                 debit = 0.0
#                                 credit = amount

#                             balance += debit - credit

#                             total_qty += quantity
#                             total_debit += debit
#                             total_credit += credit

#                             _logger.warning(
#                                 "  PRODUCT LINE seq=%s move=%s aml=%s product=%s(id=%s) "
#                                 "qty=%s unit_price=%s subtotal=%s debit=%s credit=%s "
#                                 "running_balance=%s",
#                                 il.sequence,
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
#                                 'product': il.product_id.display_name,
#                                 'quantity': quantity,
#                                 'unit_price': unit_price,
#                                 'debit': debit,
#                                 'credit': credit,
#                                 'balance': balance,
#                             })

#                     # ==================================================
#                     # Invoice has no product lines -> fallback to AML
#                     # ==================================================

#                     else:

#                         debit = line.debit or 0.0
#                         credit = line.credit or 0.0

#                         balance += debit - credit

#                         total_debit += debit
#                         total_credit += credit

#                         _logger.warning(
#                             "  INVOICE WITHOUT PRODUCT LINES move=%s aml=%s name=%s "
#                             "debit=%s credit=%s running_balance=%s",
#                             move.name,
#                             line.id,
#                             line.name,
#                             debit,
#                             credit,
#                             balance,
#                         )

#                         result_lines.append({
#                             'date': line.date,
#                             'transaction': move.name,
#                             'product': line.name or move.ref or '',
#                             'quantity': None,
#                             'unit_price': None,
#                             'debit': debit,
#                             'credit': credit,
#                             'balance': balance,
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
#                         "  JOURNAL/PAYMENT LINE move=%s type=%s aml=%s name=%s "
#                         "debit=%s credit=%s running_balance=%s",
#                         move.name,
#                         move.move_type,
#                         line.id,
#                         line.name,
#                         debit,
#                         credit,
#                         balance,
#                     )

#                     result_lines.append({
#                         'date': line.date,
#                         'transaction': move.name,
#                         'product': line.name or move.ref or '',
#                         'quantity': None,
#                         'unit_price': None,
#                         'debit': debit,
#                         'credit': credit,
#                         'balance': balance,
#                     })

#             # ======================================================
#             # 9. Statement summary + reconciliation check
#             # ======================================================

#             expected_closing = opening_balance + total_debit - total_credit

#             _logger.warning("")
#             _logger.warning(
#                 "RESULT SUMMARY PARTNER=%s | LINES=%s | QTY=%s | "
#                 "DEBIT=%s | CREDIT=%s | OPENING=%s | FINAL_BALANCE=%s",
#                 partner.name,
#                 len(result_lines),
#                 total_qty,
#                 total_debit,
#                 total_credit,
#                 opening_balance,
#                 balance,
#             )

#             if round(expected_closing, 2) != round(balance, 2):
#                 _logger.warning(
#                     "MISMATCH!! expected_closing (opening+debit-credit)=%s "
#                     "!= actual running balance=%s. Check loop logic above.",
#                     expected_closing,
#                     balance,
#                 )

#             statements.append({
#                 'partner': partner,
#                 'opening_balance': opening_balance,
#                 'lines': result_lines,
#                 'closing_balance': balance,
#                 'total_qty': total_qty,
#                 'total_debit': total_debit,
#                 'total_credit': total_credit,
#             })

#         # ==========================================================
#         # 10. Final Debug Dump
#         # ==========================================================

#         _logger.warning("")
#         _logger.warning("STATEMENTS COUNT = %s", len(statements))

#         for statement in statements:
#             _logger.warning(
#                 "STATEMENT PARTNER=%s LINES=%s OPENING=%s CLOSING=%s",
#                 statement['partner'].name,
#                 len(statement['lines']),
#                 statement['opening_balance'],
#                 statement['closing_balance'],
#             )

#         _logger.warning("========== CUSTOMER STATEMENT END ==========")
#         _logger.warning("")

#         # ==========================================================
#         # 11. Report Values
#         # ==========================================================

#         return {
#             'doc_ids': docids,
#             'doc_model': 'account.move.line',
#             'docs': selected_lines,
#             'statements': statements,
#             'date_from': date_from,
#             'date_to': date_to,
#         }




# import logging

# from odoo import api, models


# _logger = logging.getLogger(__name__)


# class CustomerStatementReport(models.AbstractModel):
#     _name = 'report.customer_statement_report.from_lines'
#     _description = 'Customer Statement Report'

#     @api.model
#     def _get_report_values(self, docids, data=None):

#         _logger.warning("")
#         _logger.warning("=" * 80)
#         _logger.warning("CUSTOMER STATEMENT - RAW AML VERSION START")
#         _logger.warning("=" * 80)

#         # ==========================================================
#         # 1. GET EXACTLY THE SELECTED ACCOUNT MOVE LINES
#         # ==========================================================

#         selected_lines = self.env['account.move.line'].browse(docids).exists()

#         _logger.warning(
#             "DOCIDS COUNT = %s | IDS = %s",
#             len(selected_lines),
#             selected_lines.ids,
#         )

#         if not selected_lines:
#             _logger.warning("NO SELECTED ACCOUNT MOVE LINES")

#             return {
#                 'doc_ids': docids,
#                 'doc_model': 'account.move.line',
#                 'docs': selected_lines,
#                 'statements': [],
#                 'date_from': False,
#                 'date_to': False,
#             }

#         # ==========================================================
#         # 2. SHOW EVERY SELECTED AML
#         #
#         # IMPORTANT:
#         # DO NOT FILTER ONLY RECEIVABLE/PAYABLE.
#         #
#         # The user's UI contains:
#         #
#         # 100100 Main Cash Account      = 2
#         # 100201 Accounts Receivable    = 19
#         # 400101 Sales Account          = 34
#         #
#         # TOTAL = 55
#         #
#         # Therefore we must preserve ALL 55 lines.
#         # ==========================================================

#         for line in selected_lines.sorted(
#             key=lambda l: (l.date, l.move_id.id, l.sequence, l.id)
#         ):
#             _logger.warning(
#                 "SELECTED AML | id=%s | date=%s | move=%s | "
#                 "account=%s %s | partner=%s | "
#                 "display_type=%s | debit=%s | credit=%s | "
#                 "product=%s | qty=%s | price=%s",
#                 line.id,
#                 line.date,
#                 line.move_id.name,
#                 line.account_id.code if line.account_id else None,
#                 line.account_id.name if line.account_id else None,
#                 line.partner_id.name if line.partner_id else None,
#                 line.display_type,
#                 line.debit,
#                 line.credit,
#                 line.product_id.display_name if line.product_id else None,
#                 line.quantity,
#                 line.price_unit,
#             )

#         # ==========================================================
#         # 3. PARTNERS
#         # ==========================================================

#         partners = selected_lines.mapped('partner_id')

#         _logger.warning(
#             "PARTNERS = %s",
#             partners.mapped('name'),
#         )

#         if not partners:
#             _logger.warning("NO PARTNER FOUND")

#             return {
#                 'doc_ids': docids,
#                 'doc_model': 'account.move.line',
#                 'docs': selected_lines,
#                 'statements': [],
#                 'date_from': min(selected_lines.mapped('date')),
#                 'date_to': max(selected_lines.mapped('date')),
#             }

#         # ==========================================================
#         # 4. DATE RANGE
#         #
#         # Use data dates if wizard provides them.
#         # Otherwise use selected lines min/max.
#         # ==========================================================

#         dates = selected_lines.mapped('date')

#         date_from = False
#         date_to = False

#         if data:
#             date_from = data.get('date_from') or False
#             date_to = data.get('date_to') or False

#         if not date_from:
#             date_from = min(dates) if dates else False

#         if not date_to:
#             date_to = max(dates) if dates else False

#         _logger.warning(
#             "DATE RANGE = %s -> %s",
#             date_from,
#             date_to,
#         )

#         # ==========================================================
#         # 5. IMPORTANT ACCOUNT SUMMARY
#         #
#         # This is the part that was missing before.
#         # We explicitly verify ALL accounts.
#         # ==========================================================

#         account_groups = {}

#         for line in selected_lines:

#             account = line.account_id

#             if not account:
#                 continue

#             key = account.id

#             if key not in account_groups:
#                 account_groups[key] = {
#                     'account': account,
#                     'count': 0,
#                     'debit': 0.0,
#                     'credit': 0.0,
#                 }

#             account_groups[key]['count'] += 1
#             account_groups[key]['debit'] += line.debit or 0.0
#             account_groups[key]['credit'] += line.credit or 0.0

#         _logger.warning("")
#         _logger.warning("=" * 80)
#         _logger.warning("ACCOUNT SUMMARY")
#         _logger.warning("=" * 80)

#         for values in account_groups.values():

#             account = values['account']

#             _logger.warning(
#                 "ACCOUNT | code=%s | name=%s | count=%s | "
#                 "debit=%s | credit=%s | balance=%s",
#                 account.code,
#                 account.name,
#                 values['count'],
#                 values['debit'],
#                 values['credit'],
#                 values['debit'] - values['credit'],
#             )

#         # ==========================================================
#         # 6. OPENING BALANCE
#         #
#         # IMPORTANT:
#         # Opening balance is calculated across ALL accounts used
#         # by this partner, not one partner property account.
#         #
#         # This is critical when the customer has:
#         #   100100
#         #   100201
#         #   400101
#         # ==========================================================

#         statements = []

#         for partner in partners:

#             _logger.warning("")
#             _logger.warning("=" * 80)
#             _logger.warning(
#                 "PROCESS PARTNER = %s (ID=%s)",
#                 partner.name,
#                 partner.id,
#             )
#             _logger.warning("=" * 80)

#             # ------------------------------------------------------
#             # Selected lines for this partner
#             # ------------------------------------------------------

#             partner_selected = selected_lines.filtered(
#                 lambda l: l.partner_id == partner
#             ).sorted(
#                 key=lambda l: (
#                     l.date,
#                     l.move_id.id,
#                     l.sequence,
#                     l.id,
#                 )
#             )

#             _logger.warning(
#                 "PARTNER SELECTED AML COUNT = %s | IDS=%s",
#                 len(partner_selected),
#                 partner_selected.ids,
#             )

#             # ------------------------------------------------------
#             # Accounts used by this partner
#             # ------------------------------------------------------

#             partner_accounts = partner_selected.mapped(
#                 'account_id'
#             )

#             _logger.warning(
#                 "PARTNER ACCOUNTS = %s",
#                 [
#                     "%s %s" % (a.code, a.name)
#                     for a in partner_accounts
#                 ],
#             )

#             # ------------------------------------------------------
#             # Opening lines
#             #
#             # ALL accounts, not one account.
#             # ------------------------------------------------------

#             opening_domain = [
#                 ('partner_id', '=', partner.id),
#                 ('parent_state', '=', 'posted'),
#                 ('date', '<', date_from),
#             ]

#             opening_lines = self.env['account.move.line'].search(
#                 opening_domain
#             )

#             opening_debit = sum(
#                 opening_lines.mapped('debit')
#             )

#             opening_credit = sum(
#                 opening_lines.mapped('credit')
#             )

#             opening_balance = opening_debit - opening_credit

#             _logger.warning(
#                 "OPENING | partner=%s | lines=%s | debit=%s | "
#                 "credit=%s | balance=%s",
#                 partner.name,
#                 len(opening_lines),
#                 opening_debit,
#                 opening_credit,
#                 opening_balance,
#             )

#             # ======================================================
#             # 7. RUNNING BALANCE
#             # ======================================================

#             balance = opening_balance

#             result_lines = []

#             total_qty = 0.0
#             total_debit = 0.0
#             total_credit = 0.0

#             # ======================================================
#             # 8. PROCESS EVERY AML EXACTLY ONCE
#             #
#             # NO grouping by move.
#             # NO invoice expansion.
#             # NO replacing AR line with invoice lines.
#             #
#             # This guarantees:
#             #
#             # selected AML = result rows
#             #
#             # 55 AML -> 55 result rows
#             # ======================================================

#             for line in partner_selected:

#                 move = line.move_id
#                 account = line.account_id

#                 debit = line.debit or 0.0
#                 credit = line.credit or 0.0

#                 # --------------------------------------------------
#                 # Account type
#                 # --------------------------------------------------

#                 account_type = (
#                     account.account_type
#                     if account
#                     else False
#                 )

#                 # --------------------------------------------------
#                 # Product
#                 #
#                 # For Sales Account lines, Odoo already has product_id
#                 # on the AML.
#                 #
#                 # For Receivable / Cash lines, product is usually empty.
#                 # We use the AML name / move ref instead.
#                 # --------------------------------------------------

#                 product = ''

#                 if line.product_id:
#                     product = line.product_id.display_name

#                 elif line.name:
#                     product = line.name

#                 elif move.ref:
#                     product = move.ref

#                 elif move.payment_reference:
#                     product = move.payment_reference

#                 else:
#                     product = move.name

#                 # --------------------------------------------------
#                 # Quantity
#                 # --------------------------------------------------

#                 quantity = 0.0

#                 if line.product_id:
#                     quantity = line.quantity or 0.0

#                 # --------------------------------------------------
#                 # Unit Price
#                 # --------------------------------------------------

#                 unit_price = 0.0

#                 if line.product_id:
#                     unit_price = line.price_unit or 0.0

#                 # --------------------------------------------------
#                 # Running balance
#                 # --------------------------------------------------

#                 balance += debit - credit

#                 total_qty += quantity
#                 total_debit += debit
#                 total_credit += credit

#                 # --------------------------------------------------
#                 # Detailed logging
#                 # --------------------------------------------------

#                 _logger.warning(
#                     "REPORT LINE | "
#                     "AML_ID=%s | DATE=%s | MOVE=%s | "
#                     "ACCOUNT=%s %s | TYPE=%s | "
#                     "PRODUCT=%s | QTY=%s | UNIT_PRICE=%s | "
#                     "DEBIT=%s | CREDIT=%s | BALANCE=%s",
#                     line.id,
#                     line.date,
#                     move.name,
#                     account.code if account else None,
#                     account.name if account else None,
#                     account_type,
#                     product,
#                     quantity,
#                     unit_price,
#                     debit,
#                     credit,
#                     balance,
#                 )

#                 # --------------------------------------------------
#                 # Add EXACTLY ONE report line for EXACTLY ONE AML
#                 # --------------------------------------------------

#                 result_lines.append({
#                     'aml_id': line.id,
#                     'date': line.date,
#                     'transaction': move.name,
#                     'product': product,
#                     'description': line.name or '',
#                     'quantity': quantity,
#                     'unit_price': unit_price,
#                     'debit': debit,
#                     'credit': credit,
#                     'balance': balance,

#                     # Extra information available to QWeb
#                     'account_id': account.id if account else False,
#                     'account_code': account.code if account else '',
#                     'account_name': account.name if account else '',
#                     'account_type': account_type or '',
#                     'move_type': move.move_type,
#                 })

#             # ======================================================
#             # 9. VALIDATION
#             # ======================================================

#             expected_closing = (
#                 opening_balance
#                 + total_debit
#                 - total_credit
#             )

#             _logger.warning("")
#             _logger.warning("=" * 80)
#             _logger.warning("FINAL PARTNER RESULT")
#             _logger.warning("=" * 80)

#             _logger.warning(
#                 "PARTNER = %s",
#                 partner.name,
#             )

#             _logger.warning(
#                 "SELECTED AML = %s",
#                 len(partner_selected),
#             )

#             _logger.warning(
#                 "RESULT LINES = %s",
#                 len(result_lines),
#             )

#             _logger.warning(
#                 "TOTAL QTY = %s",
#                 total_qty,
#             )

#             _logger.warning(
#                 "TOTAL DEBIT = %s",
#                 total_debit,
#             )

#             _logger.warning(
#                 "TOTAL CREDIT = %s",
#                 total_credit,
#             )

#             _logger.warning(
#                 "OPENING = %s",
#                 opening_balance,
#             )

#             _logger.warning(
#                 "EXPECTED CLOSING = %s",
#                 expected_closing,
#             )

#             _logger.warning(
#                 "ACTUAL CLOSING = %s",
#                 balance,
#             )

#             # ------------------------------------------------------
#             # CRITICAL VALIDATION
#             # ------------------------------------------------------

#             if len(result_lines) != len(partner_selected):

#                 _logger.error(
#                     "!!!!!!!!!!!!! ROW COUNT MISMATCH !!!!!!!!!!!!!"
#                 )

#                 _logger.error(
#                     "SELECTED AML = %s",
#                     len(partner_selected),
#                 )

#                 _logger.error(
#                     "RESULT LINES = %s",
#                     len(result_lines),
#                 )

#             else:

#                 _logger.warning(
#                     "ROW COUNT OK: %s AML -> %s REPORT ROWS",
#                     len(partner_selected),
#                     len(result_lines),
#                 )

#             # ------------------------------------------------------
#             # Account count validation
#             # ------------------------------------------------------

#             result_account_counts = {}

#             for row in result_lines:

#                 code = row['account_code'] or 'NO_ACCOUNT'

#                 result_account_counts[code] = (
#                     result_account_counts.get(code, 0) + 1
#                 )

#             _logger.warning(
#                 "RESULT ACCOUNT COUNTS = %s",
#                 result_account_counts,
#             )

#             statements.append({
#                 'partner': partner,

#                 'opening_balance': opening_balance,

#                 'lines': result_lines,

#                 'closing_balance': balance,

#                 'total_qty': total_qty,

#                 'total_debit': total_debit,

#                 'total_credit': total_credit,

#                 # Useful if QWeb wants to display account summary
#                 'accounts': [
#                     {
#                         'account': values['account'],
#                         'count': values['count'],
#                         'debit': values['debit'],
#                         'credit': values['credit'],
#                         'balance': (
#                             values['debit']
#                             - values['credit']
#                         ),
#                     }
#                     for values in account_groups.values()
#                     if values['account'] in partner_accounts
#                 ],
#             })

#         # ==========================================================
#         # 10. GLOBAL VALIDATION
#         # ==========================================================

#         _logger.warning("")
#         _logger.warning("=" * 80)
#         _logger.warning("GLOBAL VALIDATION")
#         _logger.warning("=" * 80)

#         total_selected = len(selected_lines)

#         total_report_lines = sum(
#             len(statement['lines'])
#             for statement in statements
#         )

#         _logger.warning(
#             "TOTAL SELECTED AML = %s",
#             total_selected,
#         )

#         _logger.warning(
#             "TOTAL REPORT LINES = %s",
#             total_report_lines,
#         )

#         if total_selected != total_report_lines:

#             _logger.error(
#                 "!!!!!!!! FINAL ROW COUNT MISMATCH !!!!!!!!"
#             )

#             _logger.error(
#                 "SELECTED=%s | REPORT=%s",
#                 total_selected,
#                 total_report_lines,
#             )

#         else:

#             _logger.warning(
#                 "SUCCESS: EVERY SELECTED AML HAS ONE REPORT ROW"
#             )

#         _logger.warning("")
#         _logger.warning("=" * 80)
#         _logger.warning(
#             "CUSTOMER STATEMENT - RAW AML VERSION END"
#         )
#         _logger.warning("=" * 80)
#         _logger.warning("")

#         # ==========================================================
#         # 11. REPORT VALUES
#         # ==========================================================

#         return {
#             'doc_ids': docids,
#             'doc_model': 'account.move.line',

#             # Keep all selected records
#             'docs': selected_lines,

#             'statements': statements,

#             'date_from': date_from,
#             'date_to': date_to,
#         }



import logging

from odoo import api, models


_logger = logging.getLogger(__name__)


class CustomerStatementReport(models.AbstractModel):
    _name = 'report.customer_statement_report.from_lines'
    _description = 'Customer Statement Report'

    @api.model
    def _get_report_values(self, docids, data=None):

        _logger.warning("")
        _logger.warning("=" * 80)
        _logger.warning("CUSTOMER/VENDOR STATEMENT - RAW AML VERSION START")
        _logger.warning("=" * 80)

        # ==========================================================
        # 1. GET EXACTLY THE SELECTED ACCOUNT MOVE LINES
        # ==========================================================

        selected_lines = self.env['account.move.line'].browse(docids).exists()

        _logger.warning(
            "DOCIDS COUNT = %s | IDS = %s",
            len(selected_lines),
            selected_lines.ids,
        )

        if not selected_lines:
            _logger.warning("NO SELECTED ACCOUNT MOVE LINES")

            return {
                'doc_ids': docids,
                'doc_model': 'account.move.line',
                'docs': selected_lines,
                'statements': [],
                'date_from': False,
                'date_to': False,
            }

        # ==========================================================
        # 2. SHOW EVERY SELECTED AML
        # ==========================================================

        for line in selected_lines.sorted(
            key=lambda l: (
                l.date,
                l.move_id.id,
                l.sequence,
                l.id,
            )
        ):
            _logger.warning(
                "SELECTED AML | id=%s | date=%s | move=%s | "
                "account=%s %s | partner=%s | "
                "display_type=%s | debit=%s | credit=%s | "
                "product=%s | qty=%s | price=%s",
                line.id,
                line.date,
                line.move_id.name,
                line.account_id.code if line.account_id else None,
                line.account_id.name if line.account_id else None,
                line.partner_id.name if line.partner_id else None,
                line.display_type,
                line.debit,
                line.credit,
                line.product_id.display_name
                if line.product_id else None,
                line.quantity,
                line.price_unit,
            )

        # ==========================================================
        # 3. PARTNERS
        # ==========================================================

        partners = selected_lines.mapped('partner_id')

        _logger.warning(
            "PARTNERS = %s",
            partners.mapped('name'),
        )

        if not partners:
            _logger.warning("NO PARTNER FOUND")

            dates = selected_lines.mapped('date')

            return {
                'doc_ids': docids,
                'doc_model': 'account.move.line',
                'docs': selected_lines,
                'statements': [],
                'date_from': min(dates) if dates else False,
                'date_to': max(dates) if dates else False,
            }

        # ==========================================================
        # 4. DATE RANGE
        # ==========================================================

        dates = selected_lines.mapped('date')

        date_from = False
        date_to = False

        if data:
            date_from = data.get('date_from') or False
            date_to = data.get('date_to') or False

        if not date_from:
            date_from = min(dates) if dates else False

        if not date_to:
            date_to = max(dates) if dates else False

        _logger.warning(
            "DATE RANGE = %s -> %s",
            date_from,
            date_to,
        )

        # ==========================================================
        # 5. ACCOUNT SUMMARY
        # ==========================================================

        account_groups = {}

        for line in selected_lines:

            account = line.account_id

            if not account:
                continue

            key = account.id

            if key not in account_groups:
                account_groups[key] = {
                    'account': account,
                    'count': 0,
                    'debit': 0.0,
                    'credit': 0.0,
                }

            account_groups[key]['count'] += 1
            account_groups[key]['debit'] += line.debit or 0.0
            account_groups[key]['credit'] += line.credit or 0.0

        _logger.warning("")
        _logger.warning("=" * 80)
        _logger.warning("ACCOUNT SUMMARY")
        _logger.warning("=" * 80)

        for values in account_groups.values():

            account = values['account']

            _logger.warning(
                "ACCOUNT | code=%s | name=%s | count=%s | "
                "debit=%s | credit=%s | debit-credit=%s",
                account.code,
                account.name,
                values['count'],
                values['debit'],
                values['credit'],
                values['debit'] - values['credit'],
            )

        # ==========================================================
        # 6. HELPER:
        #    DETERMINE CUSTOMER / VENDOR
        # ==========================================================

        def get_partner_kind(partner):

            # ------------------------------------------------------
            # Prefer the actual selected AML account types.
            # This is safer when a partner has both customer/vendor
            # activity.
            # ------------------------------------------------------

            partner_lines = selected_lines.filtered(
                lambda l: l.partner_id == partner
            )

            account_types = set(
                partner_lines.mapped('account_id.account_type')
            )

            if 'liability_payable' in account_types:
                return 'vendor'

            if 'asset_receivable' in account_types:
                return 'customer'

            # ------------------------------------------------------
            # Fallback to partner ranks.
            # ------------------------------------------------------

            if getattr(partner, 'supplier_rank', 0) > 0:
                return 'vendor'

            if getattr(partner, 'customer_rank', 0) > 0:
                return 'customer'

            return 'customer'

        # ==========================================================
        # 7. HELPER:
        #    FIND CONTROL ACCOUNT
        #
        # Customer:
        #     asset_receivable
        #
        # Vendor:
        #     liability_payable
        # ==========================================================

        def get_control_account(partner_selected, partner_kind):

            if partner_kind == 'vendor':

                payable_lines = partner_selected.filtered(
                    lambda l: l.account_id
                    and l.account_id.account_type
                    == 'liability_payable'
                )

                if payable_lines:
                    accounts = payable_lines.mapped('account_id')

                    # Usually there is one payable account.
                    # If multiple exist, use the first one that
                    # actually appears in the selected lines.
                    return accounts[0]

            else:

                receivable_lines = partner_selected.filtered(
                    lambda l: l.account_id
                    and l.account_id.account_type
                    == 'asset_receivable'
                )

                if receivable_lines:
                    accounts = receivable_lines.mapped('account_id')

                    return accounts[0]

            return self.env['account.account']

        # ==========================================================
        # 8. HELPER:
        #    PRODUCT / DESCRIPTION
        # ==========================================================

        def get_product_info(line):

            move = line.move_id

            product = ''
            quantity = 0.0
            unit_price = 0.0

            # ------------------------------------------------------
            # First source: actual AML
            # ------------------------------------------------------

            if line.product_id:

                product = line.product_id.display_name

                quantity = line.quantity or 0.0

                unit_price = line.price_unit or 0.0

            # ------------------------------------------------------
            # Second source:
            # invoice lines belonging to the move.
            #
            # This is important for vendor bills where the selected
            # AML may contain incomplete quantity/price information.
            # ------------------------------------------------------

            if move and move.is_invoice():

                invoice_lines = move.invoice_line_ids

                # Try exact product first.
                if line.product_id:

                    matching_lines = invoice_lines.filtered(
                        lambda inv_line:
                        inv_line.product_id
                        and inv_line.product_id.id
                        == line.product_id.id
                    )

                else:
                    matching_lines = invoice_lines.filtered(
                        lambda inv_line:
                        inv_line.account_id
                        and line.account_id
                        and inv_line.account_id.id
                        == line.account_id.id
                    )

                # --------------------------------------------------
                # Only use invoice-line data when AML data is empty.
                # This prevents replacing correct AML values.
                # --------------------------------------------------

                if matching_lines:

                    invoice_line = matching_lines[0]

                    if not product and invoice_line.product_id:
                        product = invoice_line.product_id.display_name

                    if not quantity:
                        quantity = invoice_line.quantity or 0.0

                    if not unit_price:
                        unit_price = invoice_line.price_unit or 0.0

            # ------------------------------------------------------
            # Description fallback
            # ------------------------------------------------------

            if not product:

                if line.name:
                    product = line.name

                elif move and move.ref:
                    product = move.ref

                elif move and move.payment_reference:
                    product = move.payment_reference

                elif move:
                    product = move.name

            return product, quantity, unit_price

        # ==========================================================
        # 9. HELPER:
        #    CALCULATE BALANCE EFFECT
        #
        # Customer:
        #     debit  -> increases receivable
        #     credit -> decreases receivable
        #
        # Vendor:
        #     credit -> increases payable
        #     debit  -> decreases payable
        # ==========================================================

        def get_balance_effect(line, partner_kind, control_account):

            if not control_account:
                return 0.0

            if line.account_id != control_account:
                return 0.0

            debit = line.debit or 0.0
            credit = line.credit or 0.0

            if partner_kind == 'vendor':

                return credit - debit

            return debit - credit

        # ==========================================================
        # 10. PROCESS PARTNERS
        # ==========================================================

        statements = []

        for partner in partners:

            _logger.warning("")
            _logger.warning("=" * 80)
            _logger.warning(
                "PROCESS PARTNER = %s (ID=%s)",
                partner.name,
                partner.id,
            )
            _logger.warning("=" * 80)

            # ------------------------------------------------------
            # Selected lines for this partner
            # ------------------------------------------------------

            partner_selected = selected_lines.filtered(
                lambda l: l.partner_id == partner
            ).sorted(
                key=lambda l: (
                    l.date,
                    l.move_id.id,
                    l.sequence,
                    l.id,
                )
            )

            _logger.warning(
                "PARTNER SELECTED AML COUNT = %s | IDS=%s",
                len(partner_selected),
                partner_selected.ids,
            )

            # ------------------------------------------------------
            # Determine customer/vendor
            # ------------------------------------------------------

            partner_kind = get_partner_kind(partner)

            _logger.warning(
                "PARTNER KIND = %s",
                partner_kind,
            )

            # ------------------------------------------------------
            # Accounts used by this partner
            # ------------------------------------------------------

            partner_accounts = partner_selected.mapped(
                'account_id'
            )

            _logger.warning(
                "PARTNER ACCOUNTS = %s",
                [
                    "%s %s" % (a.code, a.name)
                    for a in partner_accounts
                ],
            )

            # ------------------------------------------------------
            # Control account
            # ------------------------------------------------------

            control_account = get_control_account(
                partner_selected,
                partner_kind,
            )

            if control_account:

                _logger.warning(
                    "CONTROL ACCOUNT = %s %s | TYPE=%s",
                    control_account.code,
                    control_account.name,
                    control_account.account_type,
                )

            else:

                _logger.warning(
                    "CONTROL ACCOUNT = NOT FOUND"
                )

            # ======================================================
            # 11. OPENING BALANCE
            #
            # VERY IMPORTANT:
            #
            # Opening is calculated ONLY from the partner control
            # account.
            #
            # Do NOT include:
            #     Sales
            #     COGS
            #     Cash
            #     Inventory
            #
            # Otherwise the statement double-counts journal entries.
            # ======================================================

            opening_debit = 0.0
            opening_credit = 0.0
            opening_balance = 0.0

            opening_lines = self.env['account.move.line']

            if control_account:

                opening_domain = [
                    ('partner_id', '=', partner.id),
                    ('account_id', '=', control_account.id),
                    ('parent_state', '=', 'posted'),
                    ('date', '<', date_from),
                ]

                opening_lines = self.env[
                    'account.move.line'
                ].search(opening_domain)

                opening_debit = sum(
                    opening_lines.mapped('debit')
                )

                opening_credit = sum(
                    opening_lines.mapped('credit')
                )

                if partner_kind == 'vendor':

                    opening_balance = (
                        opening_credit
                        - opening_debit
                    )

                else:

                    opening_balance = (
                        opening_debit
                        - opening_credit
                    )

            _logger.warning(
                "OPENING | partner=%s | kind=%s | account=%s | "
                "lines=%s | debit=%s | credit=%s | balance=%s",
                partner.name,
                partner_kind,
                (
                    control_account.code
                    if control_account else None
                ),
                len(opening_lines),
                opening_debit,
                opening_credit,
                opening_balance,
            )

            # ======================================================
            # 12. RUNNING BALANCE
            # ======================================================

            balance = opening_balance

            result_lines = []

            total_qty = 0.0

            # These totals represent ALL selected AMLs because the
            # report currently displays all selected accounting lines.
            total_debit = 0.0
            total_credit = 0.0

            # These are the actual statement totals affecting the
            # partner balance.
            statement_debit = 0.0
            statement_credit = 0.0

            # ======================================================
            # 13. PROCESS EVERY AML EXACTLY ONCE
            # ======================================================

            for line in partner_selected:

                move = line.move_id
                account = line.account_id

                debit = line.debit or 0.0
                credit = line.credit or 0.0

                total_debit += debit
                total_credit += credit

                # --------------------------------------------------
                # Account type
                # --------------------------------------------------

                account_type = (
                    account.account_type
                    if account
                    else False
                )

                # --------------------------------------------------
                # Product / Quantity / Price
                # --------------------------------------------------

                product, quantity, unit_price = get_product_info(
                    line
                )

                # --------------------------------------------------
                # IMPORTANT:
                #
                # Only the partner control account affects running
                # balance.
                # --------------------------------------------------

                balance_effect = get_balance_effect(
                    line,
                    partner_kind,
                    control_account,
                )

                balance += balance_effect

                # --------------------------------------------------
                # Statement debit/credit
                #
                # For vendor, display debit/credit as actual AML
                # values, but statement balance uses the payable
                # orientation.
                # --------------------------------------------------

                if control_account and line.account_id == control_account:

                    statement_debit += debit
                    statement_credit += credit

                total_qty += quantity

                # --------------------------------------------------
                # Detailed logging
                # --------------------------------------------------

                _logger.warning(
                    "REPORT LINE | "
                    "AML_ID=%s | DATE=%s | MOVE=%s | "
                    "ACCOUNT=%s %s | TYPE=%s | "
                    "PARTNER_KIND=%s | CONTROL=%s | "
                    "PRODUCT=%s | QTY=%s | UNIT_PRICE=%s | "
                    "DEBIT=%s | CREDIT=%s | "
                    "BALANCE_EFFECT=%s | BALANCE=%s",
                    line.id,
                    line.date,
                    move.name,
                    account.code if account else None,
                    account.name if account else None,
                    account_type,
                    partner_kind,
                    (
                        control_account.code
                        if control_account else None
                    ),
                    product,
                    quantity,
                    unit_price,
                    debit,
                    credit,
                    balance_effect,
                    balance,
                )

                # --------------------------------------------------
                # EXACTLY ONE REPORT ROW PER AML
                # --------------------------------------------------

                result_lines.append({
                    'aml_id': line.id,

                    'date': line.date,

                    'transaction': move.name,

                    'product': product,

                    'description': line.name or '',

                    'quantity': quantity,

                    'unit_price': unit_price,

                    'debit': debit,

                    'credit': credit,

                    'balance': balance,

                    # Extra information
                    'account_id': (
                        account.id
                        if account else False
                    ),

                    'account_code': (
                        account.code
                        if account else ''
                    ),

                    'account_name': (
                        account.name
                        if account else ''
                    ),

                    'account_type': account_type or '',

                    'move_type': move.move_type,

                    'partner_kind': partner_kind,

                    'is_control_account': (
                        bool(
                            control_account
                            and account
                            and account.id
                            == control_account.id
                        )
                    ),

                    'balance_effect': balance_effect,
                })

            # ======================================================
            # 14. VALIDATION
            # ======================================================

            expected_closing = (
                opening_balance
                + sum(
                    row['balance_effect']
                    for row in result_lines
                )
            )

            _logger.warning("")
            _logger.warning("=" * 80)
            _logger.warning("FINAL PARTNER RESULT")
            _logger.warning("=" * 80)

            _logger.warning(
                "PARTNER = %s",
                partner.name,
            )

            _logger.warning(
                "PARTNER KIND = %s",
                partner_kind,
            )

            _logger.warning(
                "CONTROL ACCOUNT = %s",
                (
                    control_account.code
                    if control_account else None
                ),
            )

            _logger.warning(
                "SELECTED AML = %s",
                len(partner_selected),
            )

            _logger.warning(
                "RESULT LINES = %s",
                len(result_lines),
            )

            _logger.warning(
                "TOTAL QTY = %s",
                total_qty,
            )

            _logger.warning(
                "TOTAL ALL AML DEBIT = %s",
                total_debit,
            )

            _logger.warning(
                "TOTAL ALL AML CREDIT = %s",
                total_credit,
            )

            _logger.warning(
                "STATEMENT CONTROL DEBIT = %s",
                statement_debit,
            )

            _logger.warning(
                "STATEMENT CONTROL CREDIT = %s",
                statement_credit,
            )

            _logger.warning(
                "OPENING = %s",
                opening_balance,
            )

            _logger.warning(
                "EXPECTED CLOSING = %s",
                expected_closing,
            )

            _logger.warning(
                "ACTUAL CLOSING = %s",
                balance,
            )

            # ------------------------------------------------------
            # Row count validation
            # ------------------------------------------------------

            if len(result_lines) != len(partner_selected):

                _logger.error(
                    "!!!!!!!!!!!!! ROW COUNT MISMATCH !!!!!!!!!!!!!"
                )

                _logger.error(
                    "SELECTED AML = %s",
                    len(partner_selected),
                )

                _logger.error(
                    "RESULT LINES = %s",
                    len(result_lines),
                )

            else:

                _logger.warning(
                    "ROW COUNT OK: %s AML -> %s REPORT ROWS",
                    len(partner_selected),
                    len(result_lines),
                )

            # ------------------------------------------------------
            # Account count validation
            # ------------------------------------------------------

            result_account_counts = {}

            for row in result_lines:

                code = row['account_code'] or 'NO_ACCOUNT'

                result_account_counts[code] = (
                    result_account_counts.get(code, 0)
                    + 1
                )

            _logger.warning(
                "RESULT ACCOUNT COUNTS = %s",
                result_account_counts,
            )

            # ======================================================
            # 15. STATEMENT
            # ======================================================

            statements.append({
                'partner': partner,

                'partner_kind': partner_kind,

                'is_vendor': partner_kind == 'vendor',

                'is_customer': partner_kind == 'customer',

                'control_account': control_account,

                'control_account_id': (
                    control_account.id
                    if control_account
                    else False
                ),

                'control_account_code': (
                    control_account.code
                    if control_account
                    else ''
                ),

                'control_account_name': (
                    control_account.name
                    if control_account
                    else ''
                ),

                'opening_balance': opening_balance,

                'opening_debit': opening_debit,

                'opening_credit': opening_credit,

                'lines': result_lines,

                'closing_balance': balance,

                # All AML totals
                'total_qty': total_qty,

                'total_debit': total_debit,

                'total_credit': total_credit,

                # Actual statement/control-account totals
                'statement_debit': statement_debit,

                'statement_credit': statement_credit,

                # Useful account summary
                'accounts': [
                    {
                        'account': values['account'],

                        'count': values['count'],

                        'debit': values['debit'],

                        'credit': values['credit'],

                        'balance': (
                            values['credit']
                            - values['debit']
                            if partner_kind == 'vendor'
                            else
                            values['debit']
                            - values['credit']
                        ),
                    }

                    for values in account_groups.values()

                    if values['account'] in partner_accounts
                ],
            })

        # ==========================================================
        # 16. GLOBAL VALIDATION
        # ==========================================================

        _logger.warning("")
        _logger.warning("=" * 80)
        _logger.warning("GLOBAL VALIDATION")
        _logger.warning("=" * 80)

        total_selected = len(selected_lines)

        total_report_lines = sum(
            len(statement['lines'])
            for statement in statements
        )

        _logger.warning(
            "TOTAL SELECTED AML = %s",
            total_selected,
        )

        _logger.warning(
            "TOTAL REPORT LINES = %s",
            total_report_lines,
        )

        if total_selected != total_report_lines:

            _logger.error(
                "!!!!!!!! FINAL ROW COUNT MISMATCH !!!!!!!!"
            )

            _logger.error(
                "SELECTED=%s | REPORT=%s",
                total_selected,
                total_report_lines,
            )

        else:

            _logger.warning(
                "SUCCESS: EVERY SELECTED AML HAS ONE REPORT ROW"
            )

        _logger.warning("")
        _logger.warning("=" * 80)
        _logger.warning(
            "CUSTOMER/VENDOR STATEMENT - RAW AML VERSION END"
        )
        _logger.warning("=" * 80)
        _logger.warning("")

        # ==========================================================
        # 17. REPORT VALUES
        # ==========================================================

        return {
            'doc_ids': docids,

            'doc_model': 'account.move.line',

            'docs': selected_lines,

            'statements': statements,

            'date_from': date_from,

            'date_to': date_to,
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