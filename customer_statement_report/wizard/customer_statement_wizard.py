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

        _logger.warning("")
        _logger.warning("========== CUSTOMER STATEMENT START ==========")
        _logger.warning("DOCIDS RAW = %s", docids)
        _logger.warning("DATA PASSED = %s", data)

        AccountMoveLine = self.env['account.move.line']

        # ==========================================================
        # 1. Selected lines
        #
        # IMPORTANT:
        # Do NOT restrict selected lines to receivable/payable.
        #
        # The partner can have:
        #   100100 Cash
        #   100201 Receivable
        #   400101 Sales
        #
        # The statement must be able to see all partner transactions.
        # ==========================================================

        all_selected = AccountMoveLine.browse(docids).exists()

        selected_lines = all_selected.filtered(
            lambda l:
                l.partner_id
                and l.parent_state == 'posted'
        )

        _logger.warning(
            "SELECTED PARTNER LINES = %s -> ids=%s",
            len(selected_lines),
            selected_lines.ids,
        )

        if not selected_lines:
            _logger.warning(
                "NO VALID SELECTED LINES - RETURNING EMPTY"
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
            partners.mapped('name'),
        )

        # ==========================================================
        # 3. Date range
        #
        # Prefer wizard data if available.
        # Otherwise use min/max selected lines.
        # ==========================================================

        dates = selected_lines.mapped('date')

        date_from = (
            data.get('date_from')
            if data and data.get('date_from')
            else (min(dates) if dates else False)
        )

        date_to = (
            data.get('date_to')
            if data and data.get('date_to')
            else (max(dates) if dates else False)
        )

        _logger.warning(
            "DATE RANGE = %s -> %s",
            date_from,
            date_to,
        )

        # ==========================================================
        # 4. Get ALL partner journal items in the period
        #
        # IMPORTANT:
        # No account_type restriction here.
        #
        # This allows:
        #   100100
        #   100201
        #   400101
        #   etc.
        # ==========================================================

        aml = AccountMoveLine.search([
            ('partner_id', 'in', partners.ids),
            ('parent_state', '=', 'posted'),
            ('date', '>=', date_from),
            ('date', '<=', date_to),
        ], order='date asc, move_id asc, sequence asc, id asc')

        _logger.warning(
            "ALL PARTNER AML IN RANGE = %s -> ids=%s",
            len(aml),
            aml.ids,
        )

        # ==========================================================
        # 5. Opening balance
        #
        # IMPORTANT:
        # Opening balance must use ALL partner accounts,
        # not only the default receivable account.
        # ==========================================================

        statements = []

        for partner in partners:

            _logger.warning("")
            _logger.warning(
                "---------------------------------------------"
            )
            _logger.warning(
                "PROCESS PARTNER = %s (id=%s)",
                partner.name,
                partner.id,
            )
            _logger.warning(
                "---------------------------------------------"
            )

            partner_aml = aml.filtered(
                lambda l: l.partner_id == partner
            )

            # ------------------------------------------------------
            # Opening lines
            # ------------------------------------------------------

            opening_lines = AccountMoveLine.search([
                ('partner_id', '=', partner.id),
                ('parent_state', '=', 'posted'),
                ('date', '<', date_from),
            ])

            opening_debit = sum(opening_lines.mapped('debit'))
            opening_credit = sum(opening_lines.mapped('credit'))

            opening_balance = opening_debit - opening_credit

            _logger.warning(
                "OPENING: lines=%s debit=%s credit=%s balance=%s",
                len(opening_lines),
                opening_debit,
                opening_credit,
                opening_balance,
            )

            # ------------------------------------------------------
            # Running balance
            # ------------------------------------------------------

            balance = opening_balance

            result_lines = []

            total_qty = 0.0
            total_debit = 0.0
            total_credit = 0.0

            # ======================================================
            # IMPORTANT:
            #
            # Process MOVE by MOVE, not AML by AML.
            #
            # This prevents the same invoice/payment from appearing
            # multiple times because it contains multiple accounts.
            # ======================================================

            moves = partner_aml.mapped('move_id').sorted(
                key=lambda m: (
                    m.date or False,
                    m.id,
                )
            )

            _logger.warning(
                "PARTNER %s HAS %s MOVES",
                partner.name,
                len(moves),
            )

            # ======================================================
            # 6. Process moves
            # ======================================================

            for move in moves:

                move_lines = partner_aml.filtered(
                    lambda l: l.move_id == move
                )

                if not move_lines:
                    continue

                _logger.warning(
                    "PROCESS MOVE=%s TYPE=%s PARTNER_LINES=%s IDS=%s",
                    move.name,
                    move.move_type,
                    len(move_lines),
                    move_lines.ids,
                )

                # ==================================================
                # INVOICE / REFUND
                #
                # For invoices, display PRODUCT lines only once.
                #
                # We do NOT separately display:
                #   400101 Sales
                #   100201 Receivable
                #
                # because those are accounting counterpart lines
                # of the same invoice.
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
                        key=lambda x: (
                            x.sequence,
                            x.id,
                        )
                    )

                    _logger.warning(
                        "INVOICE %s PRODUCT LINES=%s IDS=%s",
                        move.name,
                        len(invoice_lines),
                        invoice_lines.ids,
                    )

                    # --------------------------------------------------
                    # Invoice with product lines
                    # --------------------------------------------------

                    if invoice_lines:

                        for il in invoice_lines:

                            amount = il.price_subtotal or 0.0
                            quantity = il.quantity or 0.0
                            unit_price = il.price_unit or 0.0

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

                            result_lines.append({
                                'date': move.date,
                                'transaction': move.name,
                                'product': il.product_id.display_name,
                                'quantity': quantity,
                                'unit_price': unit_price,
                                'debit': debit,
                                'credit': credit,
                                'balance': balance,
                            })

                            _logger.warning(
                                "  PRODUCT: %s qty=%s subtotal=%s "
                                "debit=%s credit=%s balance=%s",
                                il.product_id.display_name,
                                quantity,
                                amount,
                                debit,
                                credit,
                                balance,
                            )

                    # --------------------------------------------------
                    # Invoice without product lines
                    # --------------------------------------------------

                    else:

                        # Find the partner receivable/payable lines
                        # for the invoice.
                        #
                        # This is only a fallback.
                        partner_amount = sum(
                            line.debit - line.credit
                            for line in move_lines
                        )

                        debit = partner_amount if partner_amount > 0 else 0.0
                        credit = -partner_amount if partner_amount < 0 else 0.0

                        balance += debit - credit

                        total_debit += debit
                        total_credit += credit

                        result_lines.append({
                            'date': move.date,
                            'transaction': move.name,
                            'product': move.ref or move.name or '',
                            'quantity': None,
                            'unit_price': None,
                            'debit': debit,
                            'credit': credit,
                            'balance': balance,
                        })

                # ==================================================
                # PAYMENT / MANUAL / JOURNAL ENTRY
                #
                # Aggregate ALL partner lines belonging to this move.
                #
                # This prevents:
                #
                # 100100 Cash
                # 100201 Receivable
                #
                # from becoming two separate transactions.
                # ==================================================

                else:

                    partner_debit = sum(
                        move_lines.mapped('debit')
                    )

                    partner_credit = sum(
                        move_lines.mapped('credit')
                    )

                    # Net partner effect
                    net_amount = partner_debit - partner_credit

                    if net_amount > 0:
                        debit = net_amount
                        credit = 0.0

                    elif net_amount < 0:
                        debit = 0.0
                        credit = abs(net_amount)

                    else:
                        debit = 0.0
                        credit = 0.0

                    # If the partner has zero net effect, skip it.
                    # This avoids displaying pure accounting moves
                    # which do not affect the partner balance.
                    if debit == 0.0 and credit == 0.0:
                        _logger.warning(
                            "SKIP MOVE %s because partner net effect is zero",
                            move.name,
                        )
                        continue

                    balance += debit - credit

                    total_debit += debit
                    total_credit += credit

                    transaction_text = (
                        move.ref
                        or move_line_name(move_lines)
                        or move.name
                        or ''
                    )

                    result_lines.append({
                        'date': move.date,
                        'transaction': move.name,
                        'product': transaction_text,
                        'quantity': None,
                        'unit_price': None,
                        'debit': debit,
                        'credit': credit,
                        'balance': balance,
                    })

                    _logger.warning(
                        "  JOURNAL/PAYMENT: move=%s "
                        "partner_debit=%s partner_credit=%s "
                        "net=%s debit=%s credit=%s balance=%s",
                        move.name,
                        partner_debit,
                        partner_credit,
                        net_amount,
                        debit,
                        credit,
                        balance,
                    )

            # ======================================================
            # 7. Summary
            # ======================================================

            expected_closing = (
                opening_balance
                + total_debit
                - total_credit
            )

            _logger.warning("")
            _logger.warning(
                "RESULT SUMMARY PARTNER=%s | "
                "LINES=%s | QTY=%s | DEBIT=%s | CREDIT=%s | "
                "OPENING=%s | FINAL=%s | EXPECTED=%s",
                partner.name,
                len(result_lines),
                total_qty,
                total_debit,
                total_credit,
                opening_balance,
                balance,
                expected_closing,
            )

            if round(expected_closing, 2) != round(balance, 2):

                _logger.warning(
                    "BALANCE MISMATCH: expected=%s actual=%s",
                    expected_closing,
                    balance,
                )

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
        # 8. Final debug
        # ==========================================================

        _logger.warning("")
        _logger.warning(
            "STATEMENTS COUNT = %s",
            len(statements),
        )

        for statement in statements:

            _logger.warning(
                "STATEMENT PARTNER=%s "
                "LINES=%s OPENING=%s CLOSING=%s",
                statement['partner'].name,
                len(statement['lines']),
                statement['opening_balance'],
                statement['closing_balance'],
            )

        _logger.warning(
            "========== CUSTOMER STATEMENT END =========="
        )
        _logger.warning("")

        # ==========================================================
        # 9. Report values
        # ==========================================================

        return {
            'doc_ids': docids,
            'doc_model': 'account.move.line',
            'docs': selected_lines,
            'statements': statements,
            'date_from': date_from,
            'date_to': date_to,
        }


def move_line_name(lines):
    """
    Return a useful description for a journal/payment move.

    We prefer the first non-empty line name.
    """
    names = lines.mapped('name')
    names = [name for name in names if name]

    return names[0] if names else ''














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