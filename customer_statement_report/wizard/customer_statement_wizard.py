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




import logging

from odoo import api, models


_logger = logging.getLogger(__name__)


class CustomerStatementReport(models.AbstractModel):

    _name = 'report.customer_statement_report.from_lines'
    _description = 'Customer Statement Report'

    @api.model
    def _get_report_values(self, docids, data=None):

        # ==========================================================
        # START DEBUG
        # ==========================================================

        _logger.warning("")
        _logger.warning("==========================================================")
        _logger.warning(" CUSTOMER STATEMENT DEBUG START")
        _logger.warning("==========================================================")

        _logger.warning(
            "DOCIDS RAW = %s",
            docids
        )

        _logger.warning(
            "DOCIDS COUNT = %s",
            len(docids) if docids else 0
        )

        _logger.warning(
            "DATA PASSED = %s",
            data
        )

        AccountMoveLine = self.env['account.move.line']

        # ==========================================================
        # STEP 1
        # What exactly was sent to the report?
        # ==========================================================

        _logger.warning("")
        _logger.warning("==========================================================")
        _logger.warning(" STEP 1 - RAW DOCIDS")
        _logger.warning("==========================================================")

        all_selected = AccountMoveLine.browse(docids).exists()

        _logger.warning(
            "all_selected COUNT = %s",
            len(all_selected)
        )

        _logger.warning(
            "all_selected IDS = %s",
            all_selected.ids
        )

        for line in all_selected:

            _logger.warning(
                "DOC AML | "
                "id=%s | "
                "date=%s | "
                "move_id=%s | "
                "move=%s | "
                "move_type=%s | "
                "partner_id=%s | "
                "partner=%s | "
                "account_id=%s | "
                "account_code=%s | "
                "account_name=%s | "
                "account_type=%s | "
                "debit=%s | "
                "credit=%s | "
                "name=%s",
                line.id,
                line.date,
                line.move_id.id if line.move_id else None,
                line.move_id.name if line.move_id else None,
                line.move_id.move_type if line.move_id else None,
                line.partner_id.id if line.partner_id else None,
                line.partner_id.name if line.partner_id else None,
                line.account_id.id if line.account_id else None,
                line.account_id.code if line.account_id else None,
                line.account_id.name if line.account_id else None,
                line.account_id.account_type if line.account_id else None,
                line.debit,
                line.credit,
                line.name,
            )

        # ==========================================================
        # STEP 2
        # Partners
        # ==========================================================

        _logger.warning("")
        _logger.warning("==========================================================")
        _logger.warning(" STEP 2 - PARTNERS")
        _logger.warning("==========================================================")

        partners = all_selected.mapped('partner_id')

        _logger.warning(
            "PARTNERS COUNT = %s",
            len(partners)
        )

        _logger.warning(
            "PARTNER IDS = %s",
            partners.ids
        )

        for partner in partners:

            _logger.warning("")
            _logger.warning(
                "PARTNER | id=%s | name=%s",
                partner.id,
                partner.name
            )

            if partner.property_account_receivable_id:

                _logger.warning(
                    "  DEFAULT RECEIVABLE | id=%s | code=%s | name=%s | type=%s",
                    partner.property_account_receivable_id.id,
                    partner.property_account_receivable_id.code,
                    partner.property_account_receivable_id.name,
                    partner.property_account_receivable_id.account_type,
                )

            else:

                _logger.warning(
                    "  DEFAULT RECEIVABLE = NONE"
                )

            if partner.property_account_payable_id:

                _logger.warning(
                    "  DEFAULT PAYABLE | id=%s | code=%s | name=%s | type=%s",
                    partner.property_account_payable_id.id,
                    partner.property_account_payable_id.code,
                    partner.property_account_payable_id.name,
                    partner.property_account_payable_id.account_type,
                )

            else:

                _logger.warning(
                    "  DEFAULT PAYABLE = NONE"
                )

        # ==========================================================
        # STEP 3
        # Date range
        # ==========================================================

        _logger.warning("")
        _logger.warning("==========================================================")
        _logger.warning(" STEP 3 - DATE RANGE")
        _logger.warning("==========================================================")

        dates = all_selected.mapped('date')

        date_from = False
        date_to = False

        if data and data.get('date_from'):
            date_from = data.get('date_from')

        elif dates:
            date_from = min(dates)

        if data and data.get('date_to'):
            date_to = data.get('date_to')

        elif dates:
            date_to = max(dates)

        _logger.warning(
            "DATE FROM = %s",
            date_from
        )

        _logger.warning(
            "DATE TO = %s",
            date_to
        )

        _logger.warning(
            "DATES FOUND IN DOCIDS = %s",
            dates
        )

        # ==========================================================
        # STEP 4
        # Search ALL partner AML
        #
        # IMPORTANT:
        # NO account_type restriction here.
        # ==========================================================

        _logger.warning("")
        _logger.warning("==========================================================")
        _logger.warning(" STEP 4 - SEARCH ALL PARTNER AML")
        _logger.warning("==========================================================")

        if not partners:

            _logger.warning(
                "NO PARTNERS FOUND"
            )

            return {
                'doc_ids': docids,
                'doc_model': 'account.move.line',
                'docs': all_selected,
                'statements': [],
                'date_from': date_from,
                'date_to': date_to,
            }

        aml_domain = [
            ('partner_id', 'in', partners.ids),
            ('parent_state', '=', 'posted'),
        ]

        if date_from:
            aml_domain.append(
                ('date', '>=', date_from)
            )

        if date_to:
            aml_domain.append(
                ('date', '<=', date_to)
            )

        _logger.warning(
            "AML SEARCH DOMAIN = %s",
            aml_domain
        )

        aml = AccountMoveLine.search(
            aml_domain,
            order='date asc, move_id asc, sequence asc, id asc'
        )

        _logger.warning(
            "ALL PARTNER AML COUNT = %s",
            len(aml)
        )

        _logger.warning(
            "ALL PARTNER AML IDS = %s",
            aml.ids
        )

        # ==========================================================
        # STEP 5
        # Accounts
        # ==========================================================

        _logger.warning("")
        _logger.warning("==========================================================")
        _logger.warning(" STEP 5 - ACCOUNTS FOUND")
        _logger.warning("==========================================================")

        accounts = aml.mapped('account_id')

        _logger.warning(
            "UNIQUE ACCOUNTS COUNT = %s",
            len(accounts)
        )

        _logger.warning(
            "ACCOUNT IDS = %s",
            accounts.ids
        )

        for account in accounts:

            account_lines = aml.filtered(
                lambda l: l.account_id == account
            )

            account_debit = sum(
                account_lines.mapped('debit')
            )

            account_credit = sum(
                account_lines.mapped('credit')
            )

            _logger.warning("")
            _logger.warning(
                "ACCOUNT | "
                "id=%s | "
                "code=%s | "
                "name=%s | "
                "type=%s | "
                "AML_COUNT=%s | "
                "DEBIT=%s | "
                "CREDIT=%s",
                account.id,
                account.code,
                account.name,
                account.account_type,
                len(account_lines),
                account_debit,
                account_credit,
            )

            _logger.warning(
                "ACCOUNT AML IDS = %s",
                account_lines.ids
            )

        # ==========================================================
        # STEP 6
        # Detailed partner AML
        # ==========================================================

        _logger.warning("")
        _logger.warning("==========================================================")
        _logger.warning(" STEP 6 - PARTNER AML DETAILS")
        _logger.warning("==========================================================")

        for partner in partners:

            partner_lines = aml.filtered(
                lambda l: l.partner_id == partner
            )

            _logger.warning("")
            _logger.warning(
                "------------------------------------------------------"
            )

            _logger.warning(
                "PARTNER = %s | ID = %s",
                partner.name,
                partner.id
            )

            _logger.warning(
                "PARTNER AML COUNT = %s",
                len(partner_lines)
            )

            _logger.warning(
                "PARTNER AML IDS = %s",
                partner_lines.ids
            )

            for line in partner_lines:

                _logger.warning(
                    "PARTNER AML | "
                    "id=%s | "
                    "date=%s | "
                    "move_id=%s | "
                    "move=%s | "
                    "move_type=%s | "
                    "account=%s | "
                    "account_name=%s | "
                    "account_type=%s | "
                    "debit=%s | "
                    "credit=%s | "
                    "balance=%s | "
                    "name=%s",
                    line.id,
                    line.date,
                    line.move_id.id if line.move_id else None,
                    line.move_id.name if line.move_id else None,
                    line.move_id.move_type if line.move_id else None,
                    line.account_id.code if line.account_id else None,
                    line.account_id.name if line.account_id else None,
                    line.account_id.account_type if line.account_id else None,
                    line.debit,
                    line.credit,
                    line.balance,
                    line.name,
                )

        # ==========================================================
        # STEP 7
        # Moves
        # ==========================================================

        _logger.warning("")
        _logger.warning("==========================================================")
        _logger.warning(" STEP 7 - UNIQUE MOVES")
        _logger.warning("==========================================================")

        moves = aml.mapped('move_id').sorted(
            key=lambda m: (
                m.date or False,
                m.id,
            )
        )

        _logger.warning(
            "UNIQUE MOVES COUNT = %s",
            len(moves)
        )

        _logger.warning(
            "MOVE IDS = %s",
            moves.ids
        )

        for move in moves:

            move_lines = aml.filtered(
                lambda l: l.move_id == move
            )

            _logger.warning("")
            _logger.warning(
                "======================================================"
            )

            _logger.warning(
                "MOVE | "
                "id=%s | "
                "name=%s | "
                "date=%s | "
                "type=%s | "
                "ref=%s | "
                "partner=%s | "
                "AML_COUNT=%s",
                move.id,
                move.name,
                move.date,
                move.move_type,
                move.ref,
                move.partner_id.name if move.partner_id else None,
                len(move_lines),
            )

            _logger.warning(
                "MOVE AML IDS = %s",
                move_lines.ids
            )

            # ------------------------------------------------------
            # Show every AML inside the move
            # ------------------------------------------------------

            for line in move_lines:

                _logger.warning(
                    "  MOVE AML | "
                    "id=%s | "
                    "account=%s | "
                    "account_name=%s | "
                    "type=%s | "
                    "debit=%s | "
                    "credit=%s | "
                    "partner=%s | "
                    "name=%s",
                    line.id,
                    line.account_id.code if line.account_id else None,
                    line.account_id.name if line.account_id else None,
                    line.account_id.account_type if line.account_id else None,
                    line.debit,
                    line.credit,
                    line.partner_id.name if line.partner_id else None,
                    line.name,
                )

            # ------------------------------------------------------
            # Invoice details
            # ------------------------------------------------------

            if move.move_type in (
                'out_invoice',
                'out_refund',
            ):

                _logger.warning(
                    "  THIS MOVE IS CUSTOMER INVOICE/REFUND"
                )

                _logger.warning(
                    "  invoice_line_ids COUNT = %s",
                    len(move.invoice_line_ids)
                )

                invoice_lines = move.invoice_line_ids.filtered(
                    lambda x:
                        x.display_type == 'product'
                        and x.product_id
                ).sorted(
                    key=lambda x: (
                        x.sequence,
                        x.id,
                    )
                )

                _logger.warning(
                    "  PRODUCT INVOICE LINES COUNT = %s",
                    len(invoice_lines)
                )

                _logger.warning(
                    "  PRODUCT INVOICE LINE IDS = %s",
                    invoice_lines.ids
                )

                for il in invoice_lines:

                    _logger.warning(
                        "    PRODUCT LINE | "
                        "id=%s | "
                        "sequence=%s | "
                        "product_id=%s | "
                        "product=%s | "
                        "qty=%s | "
                        "unit_price=%s | "
                        "subtotal=%s | "
                        "display_type=%s",
                        il.id,
                        il.sequence,
                        il.product_id.id if il.product_id else None,
                        il.product_id.display_name
                        if il.product_id
                        else None,
                        il.quantity,
                        il.price_unit,
                        il.price_subtotal,
                        il.display_type,
                    )

            else:

                _logger.warning(
                    "  THIS MOVE IS NOT CUSTOMER INVOICE"
                )

                # --------------------------------------------------
                # Calculate partner effect for this move
                # --------------------------------------------------

                move_debit = sum(
                    move_lines.mapped('debit')
                )

                move_credit = sum(
                    move_lines.mapped('credit')
                )

                move_net = move_debit - move_credit

                _logger.warning(
                    "  MOVE PARTNER TOTALS | "
                    "debit=%s | "
                    "credit=%s | "
                    "net=%s",
                    move_debit,
                    move_credit,
                    move_net,
                )

        # ==========================================================
        # STEP 8
        # Compare selected docids vs searched AML
        # ==========================================================

        _logger.warning("")
        _logger.warning("==========================================================")
        _logger.warning(" STEP 8 - DOCIDS VS SEARCH RESULT")
        _logger.warning("==========================================================")

        selected_ids = set(all_selected.ids)
        searched_ids = set(aml.ids)

        missing_from_search = selected_ids - searched_ids
        extra_from_search = searched_ids - selected_ids

        _logger.warning(
            "DOCIDS COUNT = %s",
            len(selected_ids)
        )

        _logger.warning(
            "SEARCHED AML COUNT = %s",
            len(searched_ids)
        )

        _logger.warning(
            "DOCIDS NOT IN SEARCH RESULT = %s",
            sorted(missing_from_search)
        )

        _logger.warning(
            "SEARCH RESULT NOT IN DOCIDS = %s",
            sorted(extra_from_search)
        )

        # ==========================================================
        # STEP 9
        # Account-specific comparison
        # ==========================================================

        _logger.warning("")
        _logger.warning("==========================================================")
        _logger.warning(" STEP 9 - IMPORTANT ACCOUNT CHECK")
        _logger.warning("==========================================================")

        expected_account_codes = [
            '100100',
            '100201',
            '400101',
        ]

        for code in expected_account_codes:

            lines = aml.filtered(
                lambda l:
                    l.account_id
                    and l.account_id.code == code
            )

            _logger.warning(
                "EXPECTED ACCOUNT %s | COUNT=%s | IDS=%s | "
                "DEBIT=%s | CREDIT=%s",
                code,
                len(lines),
                lines.ids,
                sum(lines.mapped('debit')),
                sum(lines.mapped('credit')),
            )

        # ==========================================================
        # STEP 10
        # FINAL
        # ==========================================================

        _logger.warning("")
        _logger.warning("==========================================================")
        _logger.warning(" CUSTOMER STATEMENT DEBUG END")
        _logger.warning("==========================================================")
        _logger.warning("")

        # ==========================================================
        # TEMPORARY RETURN
        #
        # We intentionally return empty statements.
        # This test is ONLY for logs.
        # ==========================================================

        return {
            'doc_ids': docids,
            'doc_model': 'account.move.line',
            'docs': all_selected,
            'statements': [],
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