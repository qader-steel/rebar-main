# -*- coding: utf-8 -*-
"""دفتر الشركاء (Partner Ledger) — عرض كل سطر بعملته + إجمالي لكل عملة.

1. **تعبئة عمود Amount Currency** لكل سطر، بما فيها سطور عملة الشركة التي
   يُفرغها أودو عمدًا.
2. **صف إجمالي لكل عملة في نهاية سطور كل شريك** — فيرى المحاسب إجمالي
   الدولار وحده وإجمالي الدينار وحده لنفس الزبون.

يغطّي أيضًا **تقرير كشف حساب العميل**: معالجه
``account.customer.statement.report.handler`` يرث معالج دفتر الشركاء، فيأخذ
الإصلاح نفسه تلقائيًا بلا كود إضافي.

الإصلاح المحاسبي الأصلي
------------------------
كان الاستعلام يجمع ``amount_currency`` مباشرة، وهذا يعطي **صفرًا** لكل
سطور عملة الشركة (أودو يترك الحقل صفرًا والقيمة في ``balance``). ثم يتخطى
الكود أي مجموع صفري، فيختفي صف إجمالي عملة الشركة ولا يظهر إلا صف العملة
الأجنبية. الشرح الكامل في ترويسة ``account_report_currency_utils``.

لماذا ``_custom_line_postprocessor`` وحده؟
-------------------------------------------
النسخ السابقة أعادت تعريف ``_get_report_line_move_line`` و
``_report_expand_unfoldable_line_partner_ledger``. أثبت التشخيص على أودو 19
أن نظائرها في دفتر الأستاذ العام **حُذفت** في هذا الإصدار، فكانت الشفرة
ميتة بلا أي إشارة. لتفادي تكرار ذلك هنا، تعتمد هذه النسخة على الخطاف
الموثَّق ``_custom_line_postprocessor`` المعرَّف على
``account.report.custom.handler`` نفسه — فهو موجود على كل معالج تقرير،
ويُستدعى في مساري العرض الكامل وفتح السطر الواحد معًا.

مبدأ السلامة
------------
إضافة **عرضية فقط**: لا أعمدة جديدة، ولا مساس بأرقام مدين/دائن/رصيد.
"""

import logging

from odoo import models
from odoo.tools import SQL

from . import account_report_currency_utils as cur_utils

_logger = logging.getLogger(__name__)

PARTNER_GROUPBY = SQL('account_move_line.partner_id')


class PartnerLedgerCurrencyHandler(models.AbstractModel):
    _inherit = 'account.partner.ledger.report.handler'

    def _custom_line_postprocessor(self, report, options, lines):
        lines = super()._custom_line_postprocessor(report, options, lines)

        try:
            _logger.info(
                'QSS [PL] ▶ postprocessor: %s سطر | report_id=%s | '
                'عمود العملة=%s',
                len(lines), options.get('report_id'),
                cur_utils.has_amount_currency_column(options),
            )

            cur_utils.fill_amount_currency_cells(report, options, lines)

            with self.env.cr.savepoint():
                lines = cur_utils.inject_currency_totals(
                    report, options, lines, 'res.partner', PARTNER_GROUPBY,
                )
        except Exception:
            _logger.exception(
                'qader_steel_suite: تعذّرت معالجة عملات دفتر الشركاء'
            )

        return lines


class AccountReportCurrencyTotals(models.Model):
    """واجهة رفيعة تُبقي الميثودات القديمة متاحة لأي كود خارجي.

    ⚠ شكل القيمة المُعادة صار
    ``{column_group_key: {id: {currency_id: amount}}}`` — لأن الشكل القديم
    كان يدمج مجموعات الأعمدة (فترات المقارنة) في سلة واحدة وينتج رقمًا
    خاطئًا لا وجود له في الدفتر.
    """
    _inherit = 'account.report'

    def _get_query_amount_currency_sums(self, options, groupby_ids=None) -> SQL:
        return cur_utils.build_currency_sums_query(
            self, options, PARTNER_GROUPBY, groupby_ids,
        )

    def _compute_amount_currency_by_partner(self, options, groupby_ids=None):
        """``{column_group_key: {partner_id: {currency_id: amount}}}``."""
        return cur_utils.compute_currency_sums(
            self, options, PARTNER_GROUPBY, groupby_ids,
        )

    def _compute_amount_currency_by_account(self, options, groupby_ids=None):
        """``{column_group_key: {account_id: {currency_id: amount}}}``."""
        return cur_utils.compute_currency_sums(
            self, options, SQL('account_move_line.account_id'), groupby_ids,
        )