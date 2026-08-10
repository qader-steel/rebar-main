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








# -*- coding: utf-8 -*-
import logging
from odoo import api, models

_logger = logging.getLogger(__name__)


class CustomerStatementReport(models.AbstractModel):
    _name = 'report.customer_statement_report.from_lines'
    _description = 'Customer Statement Report'

    @api.model
    def _get_report_values(self, docids, data=None):

        _logger.warning("")
        _logger.warning("==================================================")
        _logger.warning("========== CUSTOMER STATEMENT START ==========")
        _logger.warning("==================================================")
        _logger.warning("DOCIDS RAW = %s", docids)
        _logger.warning("DATA PASSED = %s", data)

        # ==========================================================
        # 1. Selected Journal Items
        # ==========================================================

        all_selected = self.env['account.move.line'].browse(docids)

        _logger.warning(
            "BROWSED LINES (before filter) = %s -> %s",
            len(all_selected),
            all_selected.ids
        )

        selected_lines = all_selected.filtered(
            lambda l:
                l.exists()
                and l.partner_id
                and l.parent_state == 'posted'
                and l.account_id.account_type in (
                    'asset_receivable',
                    'liability_payable',
                )
        )

        _logger.warning(
            "SELECTED RECEIVABLE/PAYABLE LINES = %s -> %s",
            len(selected_lines),
            selected_lines.ids
        )

        # ----------------------------------------------------------
        # Debug rejected lines
        # ----------------------------------------------------------

        rejected = all_selected - selected_lines

        for rl in rejected:
            _logger.warning(
                "REJECTED LINE id=%s exists=%s partner=%s state=%s "
                "account=%s account_type=%s",
                rl.id,
                rl.exists(),
                rl.partner_id.name if rl.exists() and rl.partner_id else None,
                rl.parent_state if rl.exists() else None,
                rl.account_id.code if rl.exists() and rl.account_id else None,
                rl.account_id.account_type
                if rl.exists() and rl.account_id
                else None,
            )

        if not selected_lines:
            _logger.warning(
                "NO VALID RECEIVABLE/PAYABLE SELECTED LINES - RETURNING EMPTY"
            )

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

        _logger.warning(
            "PARTNERS (%s) = %s",
            len(partners),
            partners.mapped('name')
        )

        # ==========================================================
        # 3. Date Range
        #
        # Prefer dates supplied by the wizard/report data.
        # Otherwise fallback to selected journal items.
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
            date_to
        )

        # ==========================================================
        # 4. Process each partner
        # ==========================================================

        statements = []

        for partner in partners:

            _logger.warning("")
            _logger.warning("==================================================")
            _logger.warning(
                "PROCESS PARTNER: %s (%s)",
                partner.name,
                partner.id
            )
            _logger.warning("==================================================")

            # ======================================================
            # 4.1 Determine actual Receivable / Payable accounts
            #
            # IMPORTANT:
            #
            # DO NOT use:
            #
            #     partner.property_account_receivable_id
            #
            # because this property can exist even when the partner
            # is actually being used as a vendor.
            #
            # Instead, determine the actual account from the selected
            # journal items themselves.
            # ======================================================

            partner_selected_lines = selected_lines.filtered(
                lambda l: l.partner_id == partner
            )

            partner_accounts = partner_selected_lines.mapped(
                'account_id'
            ).filtered(
                lambda a: a.account_type in (
                    'asset_receivable',
                    'liability_payable',
                )
            )

            if not partner_accounts:

                _logger.warning(
                    "NO RECEIVABLE/PAYABLE ACCOUNT FOUND IN SELECTED "
                    "LINES FOR PARTNER %s - SKIPPING",
                    partner.name
                )

                continue

            _logger.warning(
                "SELECTED PARTNER ACCOUNTS:"
            )

            for acc in partner_accounts:
                _logger.warning(
                    "    ACCOUNT = %s / %s (id=%s) TYPE=%s",
                    acc.code,
                    acc.name,
                    acc.id,
                    acc.account_type,
                )

            # ======================================================
            # 4.2 Load ALL posted receivable/payable lines for this
            # partner and period.
            #
            # Notice:
            # We DO NOT restrict this to property_account_receivable_id.
            #
            # We use the actual accounts found above.
            # ======================================================

            aml_domain = [
                ('partner_id', '=', partner.id),
                ('parent_state', '=', 'posted'),
                ('account_id', 'in', partner_accounts.ids),
                ('date', '>=', date_from),
                ('date', '<=', date_to),
            ]

            moves = self.env['account.move.line'].search(
                aml_domain,
                order='date asc, move_name asc, id asc'
            )

            _logger.warning(
                "PERIOD MOVES FOR PARTNER %s = %s -> ids=%s",
                partner.name,
                len(moves),
                moves.ids,
            )

            # ======================================================
            # 4.3 Opening Balance
            #
            # Use the SAME actual accounts selected above.
            # ======================================================

            opening_domain = [
                ('partner_id', '=', partner.id),
                ('parent_state', '=', 'posted'),
                ('account_id', 'in', partner_accounts.ids),
                ('date', '<', date_from),
            ]

            opening_lines = self.env['account.move.line'].search(
                opening_domain,
                order='date asc, move_name asc, id asc'
            )

            opening_debit = sum(opening_lines.mapped('debit'))
            opening_credit = sum(opening_lines.mapped('credit'))

            opening_balance = opening_debit - opening_credit

            _logger.warning(
                "OPENING LINES = %s -> ids=%s",
                len(opening_lines),
                opening_lines.ids
            )

            _logger.warning(
                "OPENING DEBIT  = %s",
                opening_debit
            )

            _logger.warning(
                "OPENING CREDIT = %s",
                opening_credit
            )

            _logger.warning(
                "OPENING BALANCE = %s",
                opening_balance
            )

            # ======================================================
            # Running Balance
            # ======================================================

            balance = opening_balance

            result_lines = []

            total_qty = 0.0
            total_debit = 0.0
            total_credit = 0.0

            # ======================================================
            # 5. Process Journal Items
            # ======================================================

            for line in moves:

                move = line.move_id

                _logger.warning(
                    ""
                )

                _logger.warning(
                    "PROCESS AML"
                )

                _logger.warning(
                    "    PARTNER       = %s",
                    partner.name
                )

                _logger.warning(
                    "    DATE          = %s",
                    line.date
                )

                _logger.warning(
                    "    MOVE          = %s",
                    move.name
                )

                _logger.warning(
                    "    MOVE TYPE     = %s",
                    move.move_type
                )

                _logger.warning(
                    "    AML ID        = %s",
                    line.id
                )

                _logger.warning(
                    "    ACCOUNT       = %s",
                    line.account_id.code
                )

                _logger.warning(
                    "    ACCOUNT TYPE  = %s",
                    line.account_id.account_type
                )

                _logger.warning(
                    "    DEBIT         = %s",
                    line.debit
                )

                _logger.warning(
                    "    CREDIT        = %s",
                    line.credit
                )

                # ==================================================
                # Customer Invoice / Refund
                # ==================================================

                if move.move_type in (
                    'out_invoice',
                    'out_refund',
                ):

                    invoice_lines = move.invoice_line_ids.filtered(
                        lambda x:
                            x.display_type == 'product'
                            and x.product_id
                    ).sorted(
                        key=lambda x: (x.sequence, x.id)
                    )

                    _logger.warning(
                        "INVOICE %s PRODUCT LINES = %s -> ids=%s",
                        move.name,
                        len(invoice_lines),
                        invoice_lines.ids,
                    )

                    # ------------------------------------------------
                    # Product lines
                    # ------------------------------------------------

                    if invoice_lines:

                        lines_subtotal_sum = sum(
                            invoice_lines.mapped('price_subtotal')
                        )

                        _logger.warning(
                            "INVOICE SUBTOTAL CHECK: "
                            "SUM PRODUCT SUBTOTALS=%s | "
                            "AML DEBIT=%s | AML CREDIT=%s",
                            lines_subtotal_sum,
                            line.debit,
                            line.credit,
                        )

                        for il in invoice_lines:

                            amount = il.price_subtotal or 0.0
                            quantity = il.quantity or 0.0
                            unit_price = il.price_unit or 0.0

                            # ------------------------------------------------
                            # Customer invoice:
                            #
                            # Receivable:
                            #       Debit  -> customer owes us
                            #
                            # Customer refund:
                            #       Credit -> customer balance decreases
                            # ------------------------------------------------

                            if move.move_type == 'out_invoice':

                                debit = amount
                                credit = 0.0

                            else:

                                debit = 0.0
                                credit = amount

                            balance += debit - credit

                            total_qty += quantity
                            total_debit += debit
                            total_credit += credit

                            _logger.warning(
                                ""
                            )

                            _logger.warning(
                                "                    REPORT LINE"
                            )

                            _logger.warning(
                                "                    PARTNER       = %s",
                                partner.name
                            )

                            _logger.warning(
                                "                    DATE          = %s",
                                line.date
                            )

                            _logger.warning(
                                "                    MOVE          = %s",
                                move.name
                            )

                            _logger.warning(
                                "                    MOVE TYPE     = %s",
                                move.move_type
                            )

                            _logger.warning(
                                "                    AML ID        = %s",
                                line.id
                            )

                            _logger.warning(
                                "                    ACCOUNT       = %s",
                                line.account_id.code
                            )

                            _logger.warning(
                                "                    ACCOUNT TYPE  = %s",
                                line.account_id.account_type
                            )

                            _logger.warning(
                                "                    PRODUCT       = %s",
                                il.product_id.display_name
                            )

                            _logger.warning(
                                "                    QTY           = %s",
                                quantity
                            )

                            _logger.warning(
                                "                    UNIT PRICE    = %s",
                                unit_price
                            )

                            _logger.warning(
                                "                    SUBTOTAL      = %s",
                                amount
                            )

                            _logger.warning(
                                "                    DEBIT         = %s",
                                debit
                            )

                            _logger.warning(
                                "                    CREDIT        = %s",
                                credit
                            )

                            _logger.warning(
                                "                    MOVEMENT      = %s",
                                debit - credit
                            )

                            _logger.warning(
                                "                    BALANCE       = %s",
                                balance
                            )

                            result_lines.append({
                                'date': line.date,
                                'transaction': move.name,
                                'product': il.product_id.display_name,
                                'quantity': quantity,
                                'unit_price': unit_price,
                                'debit': debit,
                                'credit': credit,
                                'balance': balance,
                            })

                    # ------------------------------------------------
                    # Invoice without product lines
                    # ------------------------------------------------

                    else:

                        debit = line.debit or 0.0
                        credit = line.credit or 0.0

                        balance += debit - credit

                        total_debit += debit
                        total_credit += credit

                        _logger.warning(
                            "INVOICE WITHOUT PRODUCT LINES"
                        )

                        _logger.warning(
                            "    MOVE    = %s",
                            move.name
                        )

                        _logger.warning(
                            "    AML ID  = %s",
                            line.id
                        )

                        _logger.warning(
                            "    DEBIT   = %s",
                            debit
                        )

                        _logger.warning(
                            "    CREDIT  = %s",
                            credit
                        )

                        _logger.warning(
                            "    BALANCE = %s",
                            balance
                        )

                        result_lines.append({
                            'date': line.date,
                            'transaction': move.name,
                            'product': line.name or move.ref or '',
                            'quantity': None,
                            'unit_price': None,
                            'debit': debit,
                            'credit': credit,
                            'balance': balance,
                        })

                # ==================================================
                # Vendor Bill / Vendor Refund
                #
                # IMPORTANT:
                #
                # For Payable:
                #
                # Vendor Bill:
                #     Credit -> we owe vendor
                #
                # Vendor Refund:
                #     Debit  -> amount owed decreases
                #
                # This is different from Customer Receivable.
                # ==================================================

                elif move.move_type in (
                    'in_invoice',
                    'in_refund',
                ):

                    invoice_lines = move.invoice_line_ids.filtered(
                        lambda x:
                            x.display_type == 'product'
                            and x.product_id
                    ).sorted(
                        key=lambda x: (x.sequence, x.id)
                    )

                    _logger.warning(
                        "VENDOR DOCUMENT %s PRODUCT LINES = %s -> ids=%s",
                        move.name,
                        len(invoice_lines),
                        invoice_lines.ids,
                    )

                    if invoice_lines:

                        for il in invoice_lines:

                            amount = il.price_subtotal or 0.0
                            quantity = il.quantity or 0.0
                            unit_price = il.price_unit or 0.0

                            # ------------------------------------------------
                            # Vendor bill:
                            #     Credit -> payable increases
                            #
                            # Vendor refund:
                            #     Debit -> payable decreases
                            # ------------------------------------------------

                            if move.move_type == 'in_invoice':

                                debit = 0.0
                                credit = amount

                            else:

                                debit = amount
                                credit = 0.0

                            balance += debit - credit

                            total_qty += quantity
                            total_debit += debit
                            total_credit += credit

                            _logger.warning(
                                ""
                            )

                            _logger.warning(
                                "                    VENDOR REPORT LINE"
                            )

                            _logger.warning(
                                "                    PARTNER       = %s",
                                partner.name
                            )

                            _logger.warning(
                                "                    DATE          = %s",
                                line.date
                            )

                            _logger.warning(
                                "                    MOVE          = %s",
                                move.name
                            )

                            _logger.warning(
                                "                    MOVE TYPE     = %s",
                                move.move_type
                            )

                            _logger.warning(
                                "                    AML ID        = %s",
                                line.id
                            )

                            _logger.warning(
                                "                    ACCOUNT       = %s",
                                line.account_id.code
                            )

                            _logger.warning(
                                "                    ACCOUNT TYPE  = %s",
                                line.account_id.account_type
                            )

                            _logger.warning(
                                "                    PRODUCT       = %s",
                                il.product_id.display_name
                            )

                            _logger.warning(
                                "                    QTY           = %s",
                                quantity
                            )

                            _logger.warning(
                                "                    UNIT PRICE    = %s",
                                unit_price
                            )

                            _logger.warning(
                                "                    SUBTOTAL      = %s",
                                amount
                            )

                            _logger.warning(
                                "                    DEBIT         = %s",
                                debit
                            )

                            _logger.warning(
                                "                    CREDIT        = %s",
                                credit
                            )

                            _logger.warning(
                                "                    MOVEMENT      = %s",
                                debit - credit
                            )

                            _logger.warning(
                                "                    BALANCE       = %s",
                                balance
                            )

                            result_lines.append({
                                'date': line.date,
                                'transaction': move.name,
                                'product': il.product_id.display_name,
                                'quantity': quantity,
                                'unit_price': unit_price,
                                'debit': debit,
                                'credit': credit,
                                'balance': balance,
                            })

                    else:

                        debit = line.debit or 0.0
                        credit = line.credit or 0.0

                        balance += debit - credit

                        total_debit += debit
                        total_credit += credit

                        result_lines.append({
                            'date': line.date,
                            'transaction': move.name,
                            'product': line.name or move.ref or '',
                            'quantity': None,
                            'unit_price': None,
                            'debit': debit,
                            'credit': credit,
                            'balance': balance,
                        })

                # ==================================================
                # Payment / Journal Entry / Other
                # ==================================================

                else:

                    debit = line.debit or 0.0
                    credit = line.credit or 0.0

                    balance += debit - credit

                    total_debit += debit
                    total_credit += credit

                    _logger.warning(
                        ""
                    )

                    _logger.warning(
                        "                    ACCOUNTING ENTRY"
                    )

                    _logger.warning(
                        "                    PARTNER       = %s",
                        partner.name
                    )

                    _logger.warning(
                        "                    DATE          = %s",
                        line.date
                    )

                    _logger.warning(
                        "                    MOVE          = %s",
                        move.name
                    )

                    _logger.warning(
                        "                    MOVE TYPE     = %s",
                        move.move_type
                    )

                    _logger.warning(
                        "                    AML ID        = %s",
                        line.id
                    )

                    _logger.warning(
                        "                    JOURNAL       = %s",
                        move.journal_id.display_name
                    )

                    _logger.warning(
                        "                    ACCOUNT       = %s",
                        line.account_id.code
                    )

                    _logger.warning(
                        "                    ACCOUNT TYPE  = %s",
                        line.account_id.account_type
                    )

                    _logger.warning(
                        "                    DEBIT         = %s",
                        debit
                    )

                    _logger.warning(
                        "                    CREDIT        = %s",
                        credit
                    )

                    _logger.warning(
                        "                    MOVEMENT      = %s",
                        debit - credit
                    )

                    _logger.warning(
                        "                    BALANCE       = %s",
                        balance
                    )

                    _logger.warning(
                        "                    DESCRIPTION   = %s",
                        line.name or move.ref or ''
                    )

                    result_lines.append({
                        'date': line.date,
                        'transaction': move.name,
                        'product': line.name or move.ref or '',
                        'quantity': None,
                        'unit_price': None,
                        'debit': debit,
                        'credit': credit,
                        'balance': balance,
                    })

            # ======================================================
            # 6. Final Summary
            # ======================================================

            expected_closing = (
                opening_balance
                + total_debit
                - total_credit
            )

            _logger.warning("")
            _logger.warning("========== PARTNER RESULT ==========")

            _logger.warning(
                "PARTNER        = %s",
                partner.name
            )

            _logger.warning(
                "ACCOUNTS       = %s",
                partner_accounts.mapped('code')
            )

            _logger.warning(
                "LINES          = %s",
                len(result_lines)
            )

            _logger.warning(
                "TOTAL QTY      = %s",
                total_qty
            )

            _logger.warning(
                "TOTAL DEBIT    = %s",
                total_debit
            )

            _logger.warning(
                "TOTAL CREDIT   = %s",
                total_credit
            )

            _logger.warning(
                "OPENING        = %s",
                opening_balance
            )

            _logger.warning(
                "EXPECTED CLOSE = %s",
                expected_closing
            )

            _logger.warning(
                "CLOSING        = %s",
                balance
            )

            if round(expected_closing, 2) != round(balance, 2):

                _logger.warning(
                    "!!! BALANCE MISMATCH !!! "
                    "EXPECTED=%s ACTUAL=%s",
                    expected_closing,
                    balance,
                )

            _logger.warning("====================================")

            statements.append({
                'partner': partner,
                'opening_balance': opening_balance,
                'lines': result_lines,
                'closing_balance': balance,
                'total_qty': total_qty,
                'total_debit': total_debit,
                'total_credit': total_credit,
            })

        # ==========================================================
        # 7. Final Debug Dump
        # ==========================================================

        _logger.warning("")
        _logger.warning("==================================================")
        _logger.warning("STATEMENTS COUNT = %s", len(statements))

        for statement in statements:

            _logger.warning(
                "PARTNER=%s | LINES=%s | OPENING=%s | "
                "DEBIT=%s | CREDIT=%s | CLOSING=%s",
                statement['partner'].name,
                len(statement['lines']),
                statement['opening_balance'],
                statement['total_debit'],
                statement['total_credit'],
                statement['closing_balance'],
            )

        _logger.warning("========== CUSTOMER STATEMENT END ==========")
        _logger.warning("==================================================")
        _logger.warning("")

        # ==========================================================
        # 8. Report Values
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