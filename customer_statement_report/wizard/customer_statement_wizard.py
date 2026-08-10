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

    # ==========================================================
    # HELPERS
    # ==========================================================

    def _is_payment_move(self, move):
        """
        Detect real payment / cash / bank moves.

        Payment moves are normally account.move entries.
        We also consider cash/bank journal moves as payment-like
        movements because the user wants those movements fully shown.
        """

        # Real payment linked to account.payment
        if 'payment_id' in move._fields and move.payment_id:
            return True

        # Payment method / statement related moves
        if 'statement_line_id' in move._fields and move.statement_line_id:
            return True

        # Cash / Bank journal movements
        if move.journal_id and move.journal_id.type in ('cash', 'bank'):
            return True

        return False

    def _is_invoice_move(self, move):
        """
        Invoice / Bill / Refund documents.

        These must NOT expose their receivable/payable line
        as an independent report row.

        Only product invoice lines are displayed.
        """

        return move.move_type in (
            'out_invoice',
            'in_invoice',
            'out_refund',
            'in_refund',
        )

    def _is_product_line(self, line):
        """
        A real product invoice line.

        We require product_id.

        display_type is also checked so sections/notes are excluded.
        """

        if not line.product_id:
            return False

        if line.display_type not in (False, 'product'):
            return False

        return True

    def _should_include_line(self, line):
        """
        MAIN BUSINESS RULE.

        1. Invoice / Bill / Refund:
           -> ONLY product lines.

        2. Payment / Cash / Bank:
           -> ALL lines.

        3. Other journal entries:
           -> Only lines that have a product.

        This prevents the invoice receivable/payable line
        from appearing as an additional transaction.
        """

        move = line.move_id

        # ------------------------------------------------------
        # INVOICE / BILL / REFUND
        # ------------------------------------------------------

        if self._is_invoice_move(move):
            return self._is_product_line(line)

        # ------------------------------------------------------
        # PAYMENT / CASH / BANK
        # ------------------------------------------------------

        if self._is_payment_move(move):
            return True

        # ------------------------------------------------------
        # OTHER JOURNAL ENTRIES
        #
        # Do not pull pure accounting counterpart lines.
        # Only product lines are relevant to the statement.
        # ------------------------------------------------------

        return self._is_product_line(line)

    # ==========================================================
    # MAIN REPORT
    # ==========================================================

    @api.model
    def _get_report_values(self, docids, data=None):

        _logger.warning("")
        _logger.warning("=" * 90)
        _logger.warning("CUSTOMER STATEMENT - PRODUCT/PAYMENT FILTER VERSION START")
        _logger.warning("=" * 90)

        # ======================================================
        # 1. SELECTED AML
        # ======================================================

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

        # ======================================================
        # 2. PARTNERS
        # ======================================================

        partners = selected_lines.mapped('partner_id')

        _logger.warning(
            "PARTNERS = %s",
            partners.mapped('name'),
        )

        if not partners:

            dates = selected_lines.mapped('date')

            return {
                'doc_ids': docids,
                'doc_model': 'account.move.line',
                'docs': selected_lines,
                'statements': [],
                'date_from': min(dates) if dates else False,
                'date_to': max(dates) if dates else False,
            }

        # ======================================================
        # 3. DATE RANGE
        # ======================================================

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

        # ======================================================
        # 4. FILTER SELECTED LINES
        #
        # THIS IS THE IMPORTANT PART.
        # ======================================================

        included_lines = self.env['account.move.line']

        excluded_lines = self.env['account.move.line']

        for line in selected_lines:

            move = line.move_id

            include = self._should_include_line(line)

            move_kind = 'OTHER'

            if self._is_invoice_move(move):
                move_kind = 'INVOICE/BILL/REFUND'

            elif self._is_payment_move(move):
                move_kind = 'PAYMENT/CASH/BANK'

            # --------------------------------------------------
            # LOG DECISION
            # --------------------------------------------------

            _logger.warning(
                "FILTER DECISION | "
                "AML=%s | MOVE=%s | MOVE_TYPE=%s | JOURNAL=%s | "
                "ACCOUNT=%s %s | PRODUCT=%s | QTY=%s | "
                "KIND=%s | INCLUDE=%s",
                line.id,
                move.name,
                move.move_type,
                move.journal_id.name if move.journal_id else None,
                line.account_id.code if line.account_id else None,
                line.account_id.name if line.account_id else None,
                line.product_id.display_name if line.product_id else None,
                line.quantity,
                move_kind,
                include,
            )

            if include:
                included_lines |= line
            else:
                excluded_lines |= line

        # ======================================================
        # 5. FILTER SUMMARY
        # ======================================================

        _logger.warning("")
        _logger.warning("=" * 90)
        _logger.warning("FILTER SUMMARY")
        _logger.warning("=" * 90)

        _logger.warning(
            "ORIGINAL SELECTED AML = %s",
            len(selected_lines),
        )

        _logger.warning(
            "INCLUDED AML = %s",
            len(included_lines),
        )

        _logger.warning(
            "EXCLUDED AML = %s",
            len(excluded_lines),
        )

        _logger.warning(
            "INCLUDED IDS = %s",
            included_lines.ids,
        )

        _logger.warning(
            "EXCLUDED IDS = %s",
            excluded_lines.ids,
        )

        # ======================================================
        # 6. LOG EXCLUDED LINES
        # ======================================================

        for line in excluded_lines.sorted(
            key=lambda l: (l.date, l.move_id.id, l.sequence, l.id)
        ):

            _logger.warning(
                "EXCLUDED | AML=%s | DATE=%s | MOVE=%s | "
                "TYPE=%s | ACCOUNT=%s %s | PRODUCT=%s | "
                "DEBIT=%s | CREDIT=%s | NAME=%s",
                line.id,
                line.date,
                line.move_id.name,
                line.move_id.move_type,
                line.account_id.code if line.account_id else None,
                line.account_id.name if line.account_id else None,
                line.product_id.display_name if line.product_id else None,
                line.debit,
                line.credit,
                line.name,
            )

        # ======================================================
        # 7. OPENING BALANCE
        #
        # IMPORTANT:
        # Opening balance should represent actual customer
        # financial balance, therefore we still calculate it
        # from accounting lines.
        #
        # We do NOT use the filtered product rows for opening.
        # ======================================================

        statements = []

        for partner in partners:

            _logger.warning("")
            _logger.warning("=" * 90)
            _logger.warning(
                "PROCESS PARTNER = %s (ID=%s)",
                partner.name,
                partner.id,
            )
            _logger.warning("=" * 90)

            # --------------------------------------------------
            # Selected INCLUDED lines for this partner
            # --------------------------------------------------

            partner_selected = included_lines.filtered(
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
                "PARTNER INCLUDED AML COUNT = %s | IDS=%s",
                len(partner_selected),
                partner_selected.ids,
            )

            # --------------------------------------------------
            # Opening accounting balance
            # --------------------------------------------------

            opening_domain = [
                ('partner_id', '=', partner.id),
                ('parent_state', '=', 'posted'),
                ('date', '<', date_from),
            ]

            opening_lines = self.env['account.move.line'].search(
                opening_domain
            )

            opening_debit = sum(
                opening_lines.mapped('debit')
            )

            opening_credit = sum(
                opening_lines.mapped('credit')
            )

            opening_balance = (
                opening_debit - opening_credit
            )

            _logger.warning(
                "OPENING | partner=%s | lines=%s | "
                "debit=%s | credit=%s | balance=%s",
                partner.name,
                len(opening_lines),
                opening_debit,
                opening_credit,
                opening_balance,
            )

            # ==================================================
            # 8. RUNNING BALANCE
            # ==================================================

            balance = opening_balance

            result_lines = []

            total_qty = 0.0
            total_debit = 0.0
            total_credit = 0.0

            # ==================================================
            # 9. PROCESS INCLUDED LINES
            # ==================================================

            for line in partner_selected:

                move = line.move_id
                account = line.account_id

                debit = line.debit or 0.0
                credit = line.credit or 0.0

                # ------------------------------------------------
                # PRODUCT
                # ------------------------------------------------

                product = ''

                if line.product_id:
                    product = line.product_id.display_name

                elif line.name:
                    product = line.name

                elif move.ref:
                    product = move.ref

                elif move.payment_reference:
                    product = move.payment_reference

                else:
                    product = move.name

                # ------------------------------------------------
                # QUANTITY
                # ------------------------------------------------

                quantity = 0.0

                if line.product_id:
                    quantity = line.quantity or 0.0

                # ------------------------------------------------
                # UNIT PRICE
                # ------------------------------------------------

                unit_price = 0.0

                if line.product_id:
                    unit_price = line.price_unit or 0.0

                # ------------------------------------------------
                # MOVE KIND
                # ------------------------------------------------

                if self._is_invoice_move(move):

                    move_kind = 'invoice'

                elif self._is_payment_move(move):

                    move_kind = 'payment'

                else:

                    move_kind = 'other'

                # ------------------------------------------------
                # RUNNING BALANCE
                # ------------------------------------------------

                balance += debit - credit

                total_qty += quantity
                total_debit += debit
                total_credit += credit

                # ------------------------------------------------
                # LOG
                # ------------------------------------------------

                _logger.warning(
                    "REPORT LINE | "
                    "AML=%s | DATE=%s | MOVE=%s | "
                    "TYPE=%s | KIND=%s | ACCOUNT=%s %s | "
                    "PRODUCT=%s | QTY=%s | UNIT_PRICE=%s | "
                    "DEBIT=%s | CREDIT=%s | BALANCE=%s",
                    line.id,
                    line.date,
                    move.name,
                    move.move_type,
                    move_kind,
                    account.code if account else None,
                    account.name if account else None,
                    product,
                    quantity,
                    unit_price,
                    debit,
                    credit,
                    balance,
                )

                # ------------------------------------------------
                # RESULT ROW
                # ------------------------------------------------

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

                    # Extra information for QWeb
                    'account_id': account.id if account else False,
                    'account_code': account.code if account else '',
                    'account_name': account.name if account else '',
                    'account_type': (
                        account.account_type
                        if account
                        else ''
                    ),
                    'move_type': move.move_type,
                    'move_kind': move_kind,
                    'journal_name': (
                        move.journal_id.name
                        if move.journal_id
                        else ''
                    ),
                })

            # ==================================================
            # 10. VALIDATION
            # ==================================================

            expected_closing = (
                opening_balance
                + total_debit
                - total_credit
            )

            _logger.warning("")
            _logger.warning("=" * 90)
            _logger.warning("FINAL PARTNER RESULT")
            _logger.warning("=" * 90)

            _logger.warning(
                "PARTNER = %s",
                partner.name,
            )

            _logger.warning(
                "ORIGINAL SELECTED AML = %s",
                len(
                    selected_lines.filtered(
                        lambda l: l.partner_id == partner
                    )
                ),
            )

            _logger.warning(
                "INCLUDED AML = %s",
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
                "TOTAL DEBIT = %s",
                total_debit,
            )

            _logger.warning(
                "TOTAL CREDIT = %s",
                total_credit,
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

            # ==================================================
            # 11. INVOICE VALIDATION
            #
            # Verify that invoices contain ONLY product rows.
            # ==================================================

            invoice_moves = partner_selected.mapped('move_id').filtered(
                lambda m: self._is_invoice_move(m)
            )

            for invoice in invoice_moves:

                invoice_rows = partner_selected.filtered(
                    lambda l: l.move_id == invoice
                )

                for invoice_line in invoice_rows:

                    if not self._is_product_line(invoice_line):

                        _logger.error(
                            "!!!!!!!! INVOICE FILTER ERROR !!!!!!!! "
                            "Invoice %s contains non-product AML %s",
                            invoice.name,
                            invoice_line.id,
                        )

                _logger.warning(
                    "INVOICE VALIDATION | "
                    "MOVE=%s | PRODUCT REPORT ROWS=%s",
                    invoice.name,
                    len(invoice_rows),
                )

            # ==================================================
            # 12. PAYMENT VALIDATION
            #
            # Verify payment/cash moves are preserved.
            # ==================================================

            payment_moves = partner_selected.mapped(
                'move_id'
            ).filtered(
                lambda m: self._is_payment_move(m)
            )

            for payment in payment_moves:

                payment_rows = partner_selected.filtered(
                    lambda l: l.move_id == payment
                )

                _logger.warning(
                    "PAYMENT VALIDATION | "
                    "MOVE=%s | JOURNAL=%s | REPORT ROWS=%s",
                    payment.name,
                    payment.journal_id.name
                    if payment.journal_id
                    else None,
                    len(payment_rows),
                )

            # ==================================================
            # 13. ACCOUNT SUMMARY
            # ==================================================

            result_account_counts = {}

            for row in result_lines:

                code = row['account_code'] or 'NO_ACCOUNT'

                result_account_counts[code] = (
                    result_account_counts.get(code, 0) + 1
                )

            _logger.warning(
                "RESULT ACCOUNT COUNTS = %s",
                result_account_counts,
            )

            # ==================================================
            # 14. APPEND STATEMENT
            # ==================================================

            statements.append({
                'partner': partner,

                'opening_balance': opening_balance,

                'lines': result_lines,

                'closing_balance': balance,

                'total_qty': total_qty,

                'total_debit': total_debit,

                'total_credit': total_credit,

                'accounts': [],
            })

        # ======================================================
        # 15. GLOBAL VALIDATION
        # ======================================================

        _logger.warning("")
        _logger.warning("=" * 90)
        _logger.warning("GLOBAL VALIDATION")
        _logger.warning("=" * 90)

        total_original = len(selected_lines)

        total_included = len(included_lines)

        total_report_lines = sum(
            len(statement['lines'])
            for statement in statements
        )

        _logger.warning(
            "TOTAL ORIGINAL SELECTED AML = %s",
            total_original,
        )

        _logger.warning(
            "TOTAL INCLUDED AML = %s",
            total_included,
        )

        _logger.warning(
            "TOTAL REPORT LINES = %s",
            total_report_lines,
        )

        _logger.warning(
            "TOTAL EXCLUDED AML = %s",
            len(excluded_lines),
        )

        # ------------------------------------------------------
        # Included lines must equal report rows.
        # ------------------------------------------------------

        if total_included != total_report_lines:

            _logger.error(
                "!!!!!!!! FINAL INCLUDED ROW COUNT MISMATCH !!!!!!!!"
            )

            _logger.error(
                "INCLUDED=%s | REPORT=%s",
                total_included,
                total_report_lines,
            )

        else:

            _logger.warning(
                "SUCCESS: EVERY INCLUDED AML HAS ONE REPORT ROW"
            )

        # ======================================================
        # 16. FINAL DEBUG SUMMARY BY MOVE
        # ======================================================

        _logger.warning("")
        _logger.warning("=" * 90)
        _logger.warning("FINAL MOVE SUMMARY")
        _logger.warning("=" * 90)

        for move in included_lines.mapped('move_id').sorted(
            key=lambda m: (m.date, m.id)
        ):

            move_lines = included_lines.filtered(
                lambda l: l.move_id == move
            )

            if self._is_invoice_move(move):

                kind = 'INVOICE/BILL/REFUND'

            elif self._is_payment_move(move):

                kind = 'PAYMENT/CASH/BANK'

            else:

                kind = 'OTHER'

            _logger.warning(
                "MOVE SUMMARY | "
                "MOVE=%s | TYPE=%s | KIND=%s | "
                "JOURNAL=%s | INCLUDED_LINES=%s | IDS=%s",
                move.name,
                move.move_type,
                kind,
                move.journal_id.name
                if move.journal_id
                else None,
                len(move_lines),
                move_lines.ids,
            )

        # ======================================================
        # 17. END
        # ======================================================

        _logger.warning("")
        _logger.warning("=" * 90)
        _logger.warning(
            "CUSTOMER STATEMENT - PRODUCT/PAYMENT FILTER VERSION END"
        )
        _logger.warning("=" * 90)
        _logger.warning(
            "STATEMENTS = %s",
            len(statements),
        )
        _logger.warning("=" * 90)
        _logger.warning("")

        # ======================================================
        # 18. REPORT VALUES
        # ======================================================

        return {
            'doc_ids': docids,
            'doc_model': 'account.move.line',
            'docs': selected_lines,
            'statements': statements,
            'date_from': date_from,
            'date_to': date_to,
        }














# import logging

# from odoo import api, models


# _logger = logging.getLogger(__name__)


# class CustomerStatementReport(models.AbstractModel):
#     _name = 'report.customer_statement_report.from_lines'
#     _description = 'Customer Statement Report'

#     @api.model
#     def _get_report_values(self, docids, data=None):

#         _logger.warning("")
#         _logger.warning("=" * 120)
#         _logger.warning("CUSTOMER STATEMENT - VENDOR QUANTITY/PRICE FIX START")
#         _logger.warning("=" * 120)

#         # ==========================================================
#         # 1. SELECTED AML
#         # ==========================================================

#         selected_lines = self.env['account.move.line'].browse(docids).exists()

#         _logger.warning(
#             "DOCIDS COUNT=%s IDS=%s",
#             len(selected_lines),
#             selected_lines.ids,
#         )

#         if not selected_lines:
#             _logger.warning("NO SELECTED AML")

#             return {
#                 'doc_ids': docids,
#                 'doc_model': 'account.move.line',
#                 'docs': selected_lines,
#                 'statements': [],
#                 'date_from': False,
#                 'date_to': False,
#             }

#         # ==========================================================
#         # 2. SAFE FIELD ACCESS
#         # ==========================================================

#         def safe_value(record, field_name, default=None):

#             if not record:
#                 return default

#             if field_name not in record._fields:
#                 return default

#             try:
#                 return record[field_name]
#             except Exception as exc:
#                 _logger.warning(
#                     "SAFE VALUE ERROR | MODEL=%s | ID=%s | FIELD=%s | ERROR=%s",
#                     record._name,
#                     record.id,
#                     field_name,
#                     exc,
#                 )
#                 return default

#         # ==========================================================
#         # 3. DETERMINE PARTNER KIND
#         # ==========================================================

#         def get_partner_kind(partner):

#             if not partner:
#                 return "customer"

#             supplier_rank = getattr(partner, "supplier_rank", 0) or 0
#             customer_rank = getattr(partner, "customer_rank", 0) or 0

#             if supplier_rank > customer_rank:
#                 return "vendor"

#             if customer_rank > supplier_rank:
#                 return "customer"

#             if supplier_rank:
#                 return "vendor"

#             return "customer"

#         # ==========================================================
#         # 4. DETERMINE CONTROL ACCOUNT
#         # ==========================================================

#         def get_control_account(partner_lines, partner_kind):

#             expected_type = (
#                 "liability_payable"
#                 if partner_kind == "vendor"
#                 else "asset_receivable"
#             )

#             # ------------------------------------------------------
#             # First: find account by account_type
#             # ------------------------------------------------------

#             candidates = partner_lines.filtered(
#                 lambda l:
#                     l.account_id
#                     and l.account_id.account_type == expected_type
#             ).mapped("account_id")

#             candidates = candidates.exists()

#             if candidates:
#                 # Prefer the account having the highest number of lines.
#                 counts = {}

#                 for account in candidates:
#                     counts[account.id] = len(
#                         partner_lines.filtered(
#                             lambda l: l.account_id == account
#                         )
#                     )

#                 selected_account = max(
#                     candidates,
#                     key=lambda a: counts.get(a.id, 0),
#                 )

#                 _logger.warning(
#                     "CONTROL ACCOUNT FOUND | "
#                     "PARTNER=%s | KIND=%s | TYPE=%s | "
#                     "ACCOUNT=%s | CODE=%s | CANDIDATES=%s",
#                     partner_lines[:1].partner_id.display_name
#                     if partner_lines[:1].partner_id
#                     else None,
#                     partner_kind,
#                     expected_type,
#                     selected_account.display_name,
#                     selected_account.code,
#                     [
#                         (
#                             a.id,
#                             a.code,
#                             a.name,
#                             counts.get(a.id, 0),
#                         )
#                         for a in candidates
#                     ],
#                 )

#                 return selected_account

#             # ------------------------------------------------------
#             # Fallback: none found
#             # ------------------------------------------------------

#             _logger.warning(
#                 "CONTROL ACCOUNT NOT FOUND | KIND=%s | EXPECTED_TYPE=%s | "
#                 "ACCOUNTS=%s",
#                 partner_kind,
#                 expected_type,
#                 [
#                     (
#                         l.account_id.id,
#                         l.account_id.code,
#                         l.account_id.name,
#                         l.account_id.account_type,
#                     )
#                     for l in partner_lines
#                     if l.account_id
#                 ],
#             )

#             return self.env['account.account']

#         # ==========================================================
#         # 5. BUILD ONE REPORT ROW
#         # ==========================================================

#         def inspect_aml(line, partner_kind, control_account):
#             """
#             Build one report row.

#             CUSTOMER:
#                 quantity = account.move.line.quantity
#                 price    = account.move.line.price_unit

#             VENDOR:
#                 If purchase_line_id exists:
#                     quantity = purchase.order.line.product_qty
#                     UOM      = purchase.order.line.product_uom_id
#                     price    = purchase.order.line.price_unit

#                 Otherwise fallback to AML values.

#             Balance:
#                 ONLY control account affects balance.

#                 Vendor:
#                     credit - debit

#                 Customer:
#                     debit - credit
#             """

#             move = line.move_id
#             partner = line.partner_id

#             # ------------------------------------------------------
#             # AML RAW VALUES
#             # ------------------------------------------------------

#             aml_product = safe_value(line, "product_id")
#             aml_quantity = safe_value(line, "quantity", 0.0) or 0.0
#             aml_price_unit = safe_value(line, "price_unit", 0.0) or 0.0
#             aml_debit = safe_value(line, "debit", 0.0) or 0.0
#             aml_credit = safe_value(line, "credit", 0.0) or 0.0

#             # ------------------------------------------------------
#             # PURCHASE LINE
#             # ------------------------------------------------------

#             purchase_line = False

#             if "purchase_line_id" in line._fields:
#                 purchase_line = safe_value(
#                     line,
#                     "purchase_line_id",
#                     False,
#                 )

#             purchase_product = False
#             purchase_qty = 0.0
#             purchase_uom = False
#             purchase_price_unit = 0.0
#             purchase_order = False

#             if purchase_line:

#                 purchase_product = safe_value(
#                     purchase_line,
#                     "product_id",
#                     False,
#                 )

#                 purchase_qty = safe_value(
#                     purchase_line,
#                     "product_qty",
#                     0.0,
#                 ) or 0.0

#                 purchase_uom = safe_value(
#                     purchase_line,
#                     "product_uom_id",
#                     False,
#                 )

#                 purchase_price_unit = safe_value(
#                     purchase_line,
#                     "price_unit",
#                     0.0,
#                 ) or 0.0

#                 purchase_order = safe_value(
#                     purchase_line,
#                     "order_id",
#                     False,
#                 )

#             # ------------------------------------------------------
#             # START DIAGNOSTIC
#             # ------------------------------------------------------

#             _logger.warning("")
#             _logger.warning("=" * 110)
#             _logger.warning("INSPECT AML START")
#             _logger.warning("=" * 110)

#             _logger.warning(
#                 "AML BASIC | "
#                 "id=%s | date=%s | move=%s | move_type=%s | "
#                 "account=%s | account_type=%s | partner=%s | "
#                 "display_type=%s | partner_kind=%s",
#                 line.id,
#                 line.date,
#                 move.name if move else None,
#                 move.move_type if move else None,
#                 line.account_id.display_name
#                 if line.account_id
#                 else None,
#                 line.account_id.account_type
#                 if line.account_id
#                 else None,
#                 partner.display_name if partner else None,
#                 line.display_type,
#                 partner_kind,
#             )

#             _logger.warning(
#                 "AML RAW | "
#                 "product=%s | quantity=%s | price_unit=%s | "
#                 "debit=%s | credit=%s",
#                 aml_product.display_name
#                 if aml_product
#                 else None,
#                 aml_quantity,
#                 aml_price_unit,
#                 aml_debit,
#                 aml_credit,
#             )

#             _logger.warning(
#                 "PURCHASE LINK | "
#                 "purchase_line_id=%s | purchase_order=%s",
#                 purchase_line.id if purchase_line else None,
#                 purchase_order.name
#                 if purchase_order
#                 else None,
#             )

#             if purchase_line:

#                 _logger.warning(
#                     "PURCHASE RAW | "
#                     "PO_LINE=%s | product=%s | product_qty=%s | "
#                     "product_uom_id=%s | product_uom=%s | price_unit=%s",
#                     purchase_line.id,
#                     purchase_product.display_name
#                     if purchase_product
#                     else None,
#                     purchase_qty,
#                     purchase_uom.id
#                     if purchase_uom
#                     else None,
#                     purchase_uom.name
#                     if purchase_uom
#                     else None,
#                     purchase_price_unit,
#                 )

#             # ------------------------------------------------------
#             # DECIDE QUANTITY / PRICE / UOM
#             # ------------------------------------------------------

#             use_purchase_values = (
#                 partner_kind == "vendor"
#                 and purchase_line
#                 and line.display_type == "product"
#             )

#             if use_purchase_values:

#                 report_quantity = purchase_qty
#                 report_unit_price = purchase_price_unit
#                 report_uom = purchase_uom

#                 quantity_source = (
#                     "PURCHASE_LINE.product_qty"
#                 )

#                 price_source = (
#                     "PURCHASE_LINE.price_unit"
#                 )

#                 uom_source = (
#                     "PURCHASE_LINE.product_uom_id"
#                 )

#                 _logger.warning(
#                     "SOURCE SELECTED = PURCHASE ORDER LINE | "
#                     "AML_ID=%s | PO_LINE=%s",
#                     line.id,
#                     purchase_line.id,
#                 )

#             else:

#                 report_quantity = aml_quantity
#                 report_unit_price = aml_price_unit

#                 report_uom = safe_value(
#                     line,
#                     "product_uom_id",
#                     False,
#                 )

#                 quantity_source = "AML.quantity"
#                 price_source = "AML.price_unit"
#                 uom_source = "AML.product_uom_id"

#                 _logger.warning(
#                     "SOURCE SELECTED = ACCOUNT MOVE LINE | "
#                     "AML_ID=%s | DISPLAY_TYPE=%s",
#                     line.id,
#                     line.display_type,
#                 )

#             # ------------------------------------------------------
#             # PRODUCT
#             # ------------------------------------------------------

#             if (
#                 partner_kind == "vendor"
#                 and purchase_line
#                 and purchase_product
#             ):
#                 report_product = purchase_product
#                 product_source = "PURCHASE_LINE.product_id"

#             else:
#                 report_product = aml_product
#                 product_source = "AML.product_id"

#             # ------------------------------------------------------
#             # DESCRIPTION
#             # ------------------------------------------------------

#             if report_product:
#                 product_description = (
#                     report_product.display_name
#                 )
#             else:
#                 product_description = (
#                     line.name
#                     or (
#                         move.name
#                         if move
#                         else ""
#                     )
#                 )

#             # ------------------------------------------------------
#             # UOM
#             # ------------------------------------------------------

#             report_uom_name = (
#                 report_uom.name
#                 if report_uom
#                 else ""
#             )

#             # ------------------------------------------------------
#             # CONTROL ACCOUNT CHECK
#             # ------------------------------------------------------

#             is_control_account = False

#             if line.account_id and control_account:
#                 is_control_account = (
#                     line.account_id.id
#                     == control_account.id
#                 )

#             # ------------------------------------------------------
#             # BALANCE EFFECT
#             # ------------------------------------------------------

#             if is_control_account:

#                 if partner_kind == "vendor":
#                     balance_effect = (
#                         aml_credit
#                         - aml_debit
#                     )
#                 else:
#                     balance_effect = (
#                         aml_debit
#                         - aml_credit
#                     )

#             else:
#                 balance_effect = 0.0

#             # ------------------------------------------------------
#             # NON PRODUCT DESCRIPTION
#             # ------------------------------------------------------

#             if line.display_type != "product":

#                 if move:
#                     product_description = move.name

#                 if not product_description:
#                     product_description = (
#                         line.name
#                         or ""
#                     )

#             # ------------------------------------------------------
#             # FINAL DIAGNOSTIC
#             # ------------------------------------------------------

#             _logger.warning(
#                 "REPORT SOURCE DECISION | "
#                 "AML_ID=%s | MOVE=%s | PARTNER_KIND=%s | "
#                 "DISPLAY_TYPE=%s | "
#                 "PURCHASE_LINE=%s | "
#                 "PRODUCT=%s <- %s | "
#                 "QTY=%s <- %s | "
#                 "UOM=%s <- %s | "
#                 "PRICE=%s <- %s | "
#                 "DEBIT=%s | CREDIT=%s | "
#                 "CONTROL_ACCOUNT=%s | "
#                 "IS_CONTROL=%s | "
#                 "BALANCE_EFFECT=%s",
#                 line.id,
#                 move.name if move else None,
#                 partner_kind,
#                 line.display_type,
#                 purchase_line.id
#                 if purchase_line
#                 else None,
#                 report_product.display_name
#                 if report_product
#                 else None,
#                 product_source,
#                 report_quantity,
#                 quantity_source,
#                 report_uom_name,
#                 uom_source,
#                 report_unit_price,
#                 price_source,
#                 aml_debit,
#                 aml_credit,
#                 control_account.code
#                 if control_account
#                 else None,
#                 is_control_account,
#                 balance_effect,
#             )

#             _logger.warning("=" * 110)
#             _logger.warning("INSPECT AML END")
#             _logger.warning("=" * 110)

#             # ------------------------------------------------------
#             # RETURN
#             # ------------------------------------------------------

#             return {
#                 "aml_id": line.id,

#                 "date": line.date,

#                 "transaction": (
#                     move.name
#                     if move
#                     else ""
#                 ),

#                 "product": (
#                     report_product.display_name
#                     if report_product
#                     else ""
#                 ),

#                 "description": product_description,

#                 "quantity": report_quantity,

#                 "unit_price": report_unit_price,

#                 "uom": report_uom_name,

#                 "debit": aml_debit,

#                 "credit": aml_credit,

#                 "balance_effect": balance_effect,

#                 "quantity_source": quantity_source,

#                 "price_source": price_source,

#                 "uom_source": uom_source,

#                 "product_source": product_source,

#                 "purchase_line_id": (
#                     purchase_line.id
#                     if purchase_line
#                     else False
#                 ),

#                 "purchase_order": (
#                     purchase_order.name
#                     if purchase_order
#                     else ""
#                 ),

#                 "account_id": (
#                     line.account_id.id
#                     if line.account_id
#                     else False
#                 ),

#                 "account_code": (
#                     line.account_id.code
#                     if line.account_id
#                     else ""
#                 ),

#                 "account_name": (
#                     line.account_id.name
#                     if line.account_id
#                     else ""
#                 ),

#                 "account_type": (
#                     line.account_id.account_type
#                     if line.account_id
#                     else ""
#                 ),

#                 "move_type": (
#                     move.move_type
#                     if move
#                     else ""
#                 ),
#             }

#         # ==========================================================
#         # 6. DATE RANGE
#         # ==========================================================

#         dates = selected_lines.mapped("date")

#         date_from = False
#         date_to = False

#         if data:
#             date_from = (
#                 data.get("date_from")
#                 or False
#             )

#             date_to = (
#                 data.get("date_to")
#                 or False
#             )

#         if not date_from:
#             date_from = (
#                 min(dates)
#                 if dates
#                 else False
#             )

#         if not date_to:
#             date_to = (
#                 max(dates)
#                 if dates
#                 else False
#             )

#         _logger.warning(
#             "DATE RANGE | FROM=%s | TO=%s",
#             date_from,
#             date_to,
#         )

#         # ==========================================================
#         # 7. PARTNERS
#         # ==========================================================

#         partners = selected_lines.mapped(
#             "partner_id"
#         ).exists()

#         _logger.warning(
#             "PARTNERS | %s",
#             partners.mapped("display_name"),
#         )

#         statements = []

#         # ==========================================================
#         # 8. PROCESS EACH PARTNER
#         # ==========================================================

#         for partner in partners:

#             partner_selected = selected_lines.filtered(
#                 lambda l:
#                     l.partner_id == partner
#             ).sorted(
#                 key=lambda l: (
#                     l.date,
#                     l.move_id.id,
#                     l.sequence,
#                     l.id,
#                 )
#             )

#             partner_kind = get_partner_kind(
#                 partner
#             )

#             # ------------------------------------------------------
#             # CONTROL ACCOUNT
#             # ------------------------------------------------------

#             control_account = get_control_account(
#                 partner_selected,
#                 partner_kind,
#             )

#             _logger.warning("")
#             _logger.warning("=" * 120)
#             _logger.warning(
#                 "PROCESS PARTNER | %s",
#                 partner.display_name,
#             )
#             _logger.warning("=" * 120)

#             _logger.warning(
#                 "PARTNER KIND = %s",
#                 partner_kind,
#             )

#             _logger.warning(
#                 "SELECTED AML COUNT = %s",
#                 len(partner_selected),
#             )

#             _logger.warning(
#                 "CONTROL ACCOUNT = %s",
#                 control_account.display_name
#                 if control_account
#                 else "NONE",
#             )

#             _logger.warning(
#                 "CONTROL ACCOUNT CODE = %s",
#                 control_account.code
#                 if control_account
#                 else "NONE",
#             )

#             # ======================================================
#             # 9. OPENING BALANCE
#             # ======================================================

#             opening_balance = 0.0

#             if date_from and control_account:

#                 opening_lines = self.env[
#                     "account.move.line"
#                 ].search([
#                     (
#                         "partner_id",
#                         "=",
#                         partner.id,
#                     ),
#                     (
#                         "account_id",
#                         "=",
#                         control_account.id,
#                     ),
#                     (
#                         "parent_state",
#                         "=",
#                         "posted",
#                     ),
#                     (
#                         "date",
#                         "<",
#                         date_from,
#                     ),
#                 ])

#                 opening_debit = sum(
#                     opening_lines.mapped("debit")
#                 )

#                 opening_credit = sum(
#                     opening_lines.mapped("credit")
#                 )

#                 if partner_kind == "vendor":
#                     opening_balance = (
#                         opening_credit
#                         - opening_debit
#                     )
#                 else:
#                     opening_balance = (
#                         opening_debit
#                         - opening_credit
#                     )

#                 _logger.warning(
#                     "OPENING | "
#                     "PARTNER=%s | KIND=%s | "
#                     "ACCOUNT=%s | LINES=%s | "
#                     "DEBIT=%s | CREDIT=%s | "
#                     "OPENING_BALANCE=%s",
#                     partner.display_name,
#                     partner_kind,
#                     control_account.code,
#                     len(opening_lines),
#                     opening_debit,
#                     opening_credit,
#                     opening_balance,
#                 )

#             else:

#                 _logger.warning(
#                     "OPENING SKIPPED | "
#                     "DATE_FROM=%s | CONTROL_ACCOUNT=%s",
#                     date_from,
#                     control_account.id
#                     if control_account
#                     else None,
#                 )

#             # ======================================================
#             # 10. BUILD RESULT LINES
#             # ======================================================

#             balance = opening_balance

#             result_lines = []

#             total_qty = 0.0
#             total_debit = 0.0
#             total_credit = 0.0

#             for line in partner_selected:

#                 # --------------------------------------------------
#                 # IMPORTANT:
#                 #
#                 # inspect_aml() is now the ACTUAL source of
#                 # quantity/price/product/uom.
#                 #
#                 # We no longer read:
#                 #
#                 #     line.quantity
#                 #     line.price_unit
#                 #
#                 # directly for the final report.
#                 # --------------------------------------------------

#                 row = inspect_aml(
#                     line,
#                     partner_kind,
#                     control_account,
#                 )

#                 # --------------------------------------------------
#                 # UPDATE BALANCE
#                 # --------------------------------------------------

#                 balance += (
#                     row["balance_effect"]
#                 )

#                 # --------------------------------------------------
#                 # TOTALS
#                 # --------------------------------------------------

#                 total_qty += (
#                     row["quantity"]
#                     or 0.0
#                 )

#                 total_debit += (
#                     row["debit"]
#                     or 0.0
#                 )

#                 total_credit += (
#                     row["credit"]
#                     or 0.0
#                 )

#                 # --------------------------------------------------
#                 # FINAL ROW
#                 # --------------------------------------------------

#                 result_lines.append({
#                     "aml_id": row["aml_id"],

#                     "date": row["date"],

#                     "transaction": row["transaction"],

#                     "product": row["product"],

#                     "description": row["description"],

#                     "quantity": row["quantity"],

#                     "unit_price": row["unit_price"],

#                     "uom": row["uom"],

#                     "debit": row["debit"],

#                     "credit": row["credit"],

#                     "balance": balance,

#                     "balance_effect": row[
#                         "balance_effect"
#                     ],

#                     "account_id": row[
#                         "account_id"
#                     ],

#                     "account_code": row[
#                         "account_code"
#                     ],

#                     "account_name": row[
#                         "account_name"
#                     ],

#                     "account_type": row[
#                         "account_type"
#                     ],

#                     "move_type": row[
#                         "move_type"
#                     ],

#                     "quantity_source": row[
#                         "quantity_source"
#                     ],

#                     "price_source": row[
#                         "price_source"
#                     ],

#                     "uom_source": row[
#                         "uom_source"
#                     ],

#                     "product_source": row[
#                         "product_source"
#                     ],

#                     "purchase_line_id": row[
#                         "purchase_line_id"
#                     ],

#                     "purchase_order": row[
#                         "purchase_order"
#                     ],
#                 })

#                 # --------------------------------------------------
#                 # CRITICAL FINAL LOG
#                 # --------------------------------------------------

#                 _logger.warning(
#                     "FINAL REPORT ROW | "
#                     "AML=%s | MOVE=%s | "
#                     "ACCOUNT=%s | "
#                     "PRODUCT=%s | "
#                     "QTY=%s | "
#                     "UOM=%s | "
#                     "PRICE=%s | "
#                     "DEBIT=%s | CREDIT=%s | "
#                     "BALANCE_EFFECT=%s | "
#                     "BALANCE=%s | "
#                     "QTY_SOURCE=%s | "
#                     "PRICE_SOURCE=%s | "
#                     "PO_LINE=%s",
#                     row["aml_id"],
#                     row["transaction"],
#                     row["account_code"],
#                     row["product"],
#                     row["quantity"],
#                     row["uom"],
#                     row["unit_price"],
#                     row["debit"],
#                     row["credit"],
#                     row["balance_effect"],
#                     balance,
#                     row["quantity_source"],
#                     row["price_source"],
#                     row["purchase_line_id"],
#                 )

#             # ======================================================
#             # 11. VALIDATION
#             # ======================================================

#             control_debit = 0.0
#             control_credit = 0.0

#             if control_account:

#                 control_rows = partner_selected.filtered(
#                     lambda l:
#                         l.account_id
#                         and l.account_id.id
#                         == control_account.id
#                 )

#                 control_debit = sum(
#                     control_rows.mapped("debit")
#                 )

#                 control_credit = sum(
#                     control_rows.mapped("credit")
#                 )

#             if partner_kind == "vendor":
#                 expected_closing = (
#                     opening_balance
#                     + control_credit
#                     - control_debit
#                 )
#             else:
#                 expected_closing = (
#                     opening_balance
#                     + control_debit
#                     - control_credit
#                 )

#             _logger.warning("")
#             _logger.warning("=" * 120)
#             _logger.warning(
#                 "PARTNER FINAL VALIDATION"
#             )
#             _logger.warning("=" * 120)

#             _logger.warning(
#                 "PARTNER = %s",
#                 partner.display_name,
#             )

#             _logger.warning(
#                 "KIND = %s",
#                 partner_kind,
#             )

#             _logger.warning(
#                 "CONTROL ACCOUNT = %s",
#                 control_account.code
#                 if control_account
#                 else None,
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
#                 "CONTROL DEBIT = %s",
#                 control_debit,
#             )

#             _logger.warning(
#                 "CONTROL CREDIT = %s",
#                 control_credit,
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

#             _logger.warning(
#                 "CLOSING DIFFERENCE = %s",
#                 balance - expected_closing,
#             )

#             # ======================================================
#             # 12. SOURCE SUMMARY
#             # ======================================================

#             purchase_source_rows = [
#                 row
#                 for row in result_lines
#                 if row["quantity_source"]
#                 == "PURCHASE_LINE.product_qty"
#             ]

#             aml_source_rows = [
#                 row
#                 for row in result_lines
#                 if row["quantity_source"]
#                 == "AML.quantity"
#             ]

#             _logger.warning(
#                 "SOURCE SUMMARY | "
#                 "PURCHASE_LINE_ROWS=%s | "
#                 "AML_ROWS=%s",
#                 len(purchase_source_rows),
#                 len(aml_source_rows),
#             )

#             for row in purchase_source_rows:

#                 _logger.warning(
#                     "PURCHASE SOURCE RESULT | "
#                     "AML=%s | MOVE=%s | "
#                     "PO_LINE=%s | PRODUCT=%s | "
#                     "QTY=%s | UOM=%s | PRICE=%s",
#                     row["aml_id"],
#                     row["transaction"],
#                     row["purchase_line_id"],
#                     row["product"],
#                     row["quantity"],
#                     row["uom"],
#                     row["unit_price"],
#                 )

#             # ======================================================
#             # 13. STATEMENT
#             # ======================================================

#             statements.append({
#                 "partner": partner,

#                 "opening_balance": opening_balance,

#                 "lines": result_lines,

#                 "closing_balance": balance,

#                 "total_qty": total_qty,

#                 "total_debit": total_debit,

#                 "total_credit": total_credit,

#                 "accounts": [],

#                 "partner_kind": partner_kind,

#                 "control_account": (
#                     control_account
#                     if control_account
#                     else False
#                 ),
#             })

#         # ==========================================================
#         # 14. GLOBAL VALIDATION
#         # ==========================================================

#         total_report_lines = sum(
#             len(statement["lines"])
#             for statement in statements
#         )

#         _logger.warning("")
#         _logger.warning("=" * 120)
#         _logger.warning(
#             "GLOBAL VALIDATION"
#         )
#         _logger.warning("=" * 120)

#         _logger.warning(
#             "SELECTED AML = %s",
#             len(selected_lines),
#         )

#         _logger.warning(
#             "REPORT LINES = %s",
#             total_report_lines,
#         )

#         if (
#             len(selected_lines)
#             == total_report_lines
#         ):
#             _logger.warning(
#                 "SUCCESS: EVERY AML HAS ONE REPORT ROW"
#             )
#         else:
#             _logger.warning(
#                 "WARNING: AML/REPORT ROW COUNT MISMATCH"
#             )

#         # ==========================================================
#         # 15. END
#         # ==========================================================

#         _logger.warning("")
#         _logger.warning("=" * 120)
#         _logger.warning(
#             "CUSTOMER STATEMENT - VENDOR QUANTITY/PRICE FIX END"
#         )
#         _logger.warning("=" * 120)

#         # ==========================================================
#         # 16. RETURN REPORT DATA
#         # ==========================================================

#         return {
#             "doc_ids": docids,

#             "doc_model": "account.move.line",

#             "docs": selected_lines,

#             "statements": statements,

#             "date_from": date_from,

#             "date_to": date_to,
#         }





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