# -*- coding: utf-8 -*-
"""دفتر الشركاء (Partner Ledger) — عرض كل سطر بعملته + إجمالي لكل عملة.

ما الذي يفعله هذا الملف
-----------------------
1. **تعبئة عمود Amount Currency** لكل سطر، بما فيها سطور عملة الشركة التي
   يتركها أودو فارغة (القيمة موجودة في ``balance``).
2. **إضافة صف إجمالي لكل عملة تحت كل شريك** — "IQD Total" و "USD Total" —
   فيرى المحاسب إجمالي الدينار وحده وإجمالي الدولار وحده لنفس الزبون.

إصلاح (19.0.1.3.0) — لماذا كان إجمالي الدينار مفقودًا
------------------------------------------------------
الاستعلام السابق كان ``COALESCE(SUM(amount_currency), 0.0)``، وهذا يعطي
**صفرًا** لكل سطور عملة الشركة لأن أودو يترك ``amount_currency = 0`` عندما
تكون عملة المستند هي عملة الشركة (القيمة في ``balance``). ثم كان الكود
يتخطى أي مجموع صفري، فيختفي صف "IQD Total" ولا يظهر إلا "USD Total".

الشرح الكامل وبقية المزالق (المقارنة، فروقات الصرف) في ترويسة
``account_report_currency_utils``.

مبدأ السلامة
------------
كل إضافة هنا **عرضية فقط**: لا تُنشئ أعمدة ولا تغيّر أرقام مدين/دائن/رصيد.
واستدعاء ``super()`` نفسه ملفوف بـ try/except أيضًا — لأن الخطر الحقيقي ليس
في كودنا بل في تغيّر توقيع الدالة في Enterprise بين الإصدارات.
"""

import logging

from odoo import models
from odoo.tools import SQL

from . import account_report_currency_utils as cur_utils

_logger = logging.getLogger(__name__)

PARTNER_GROUPBY = SQL('account_move_line.partner_id')


class PartnerLedgerCurrencyHandler(models.AbstractModel):
    _inherit = 'account.partner.ledger.report.handler'

    # ------------------------------------------------------------------
    # 1) تعبئة خانة Amount Currency لكل سطر
    # ------------------------------------------------------------------

    def _get_report_line_move_line(self, options, aml_query_result, *args, **kwargs):
        """بنّاء سطر بند القيد في دفتر الشركاء.

        توقيعه الفعلي في Enterprise::

            _get_report_line_move_line(self, options, aml_query_result,
                                       partner_line_id, init_bal_by_col_group,
                                       level_shift=0)

        نُبقي الذيل ``*args/**kwargs`` تحسّبًا لتغيّره بين الإصدارات.

        ملاحظة: هذا المعالج موروث أيضًا في **تقرير كشف حساب العميل**
        (``account.customer.statement.report.handler`` يرث معالج دفتر
        الشركاء)، فيستفيد التقريران من الإصلاح نفسه تلقائيًا.

        أودو يُفرغ الخانة عمدًا لسطور عملة الشركة::

            if currency == self.env.company.currency_id:
                col_value = ''

        ونحن نعيد ملأها من ``balance``.
        """
        line = super()._get_report_line_move_line(
            options, aml_query_result, *args, **kwargs
        )

        try:
            report = self.env['account.report'].browse(options['report_id'])
            # صف واحد هنا (لا قاموس لكل مجموعة أعمدة)، فنغلّفه بمفتاح مجموعته.
            cur_utils.patch_amount_currency_cells(
                report, options, line,
                {aml_query_result.get('column_group_key'): aml_query_result},
            )
        except Exception:
            # تحسين عرضي فقط — لا يجوز أن يكسر تقريرًا محاسبيًا.
            _logger.exception(
                'qader_steel_suite: تعذّر تعبئة خانة العملة في دفتر الشركاء'
            )

        return line

    # ------------------------------------------------------------------
    # 2) صف إجمالي لكل عملة تحت كل شريك
    # ------------------------------------------------------------------

    def _report_expand_unfoldable_line_partner_ledger(
        self, line_dict_id, groupby, options, progress, offset, *args, **kwargs
    ):
        result = super()._report_expand_unfoldable_line_partner_ledger(
            line_dict_id, groupby, options, progress, offset, *args, **kwargs
        )

        try:
            # (أ) توسيع فرعي (الشريك مقسَّمًا حسب شهر/حساب ...): إجمالي
            #     الشريك كاملًا لا يخصّ المجموعة الفرعية، وعرضه تحتها رقم
            #     مضلِّل. نتركها بلا إجماليات.
            if groupby:
                return result

            # (ب) الترقيم: لا نضيف الإجماليات إلا بعد اكتمال عرض كل سطور
            #     الشريك، وإلا تكرّر الصف مع كل صفحة "تحميل المزيد".
            if result.get('has_more'):
                return result

            report = self.env['account.report'].browse(options['report_id'])

            # (ج) سطر "شريك غير معروف" يحمل markup='no_partner' بلا معرّف،
            #     فيرجع None هنا ونتخطّاه بهدوء.
            partner_id = cur_utils.extract_line_id_value(
                report, line_dict_id, 'res.partner',
            )
            if not partner_id:
                return result

            # savepoint: يبقي معاملة أودو الخارجية سليمة حتى لو رفض
            # PostgreSQL استعلام التجميع على إصدار Enterprise مستقبلي.
            # groupby_ids: قصر الاستعلام على هذا الشريك وحده (الأداء).
            with self.env.cr.savepoint():
                sums = cur_utils.compute_currency_sums(
                    report, options, PARTNER_GROUPBY, groupby_ids=[partner_id],
                )

            cur_utils.append_currency_total_lines(
                report, options, result, line_dict_id, sums, partner_id,
            )

        except Exception:
            _logger.exception(
                'qader_steel_suite: تعذّر إضافة إجماليات العملات في دفتر الشركاء'
            )

        return result


class AccountReportCurrencyTotals(models.Model):
    """واجهة رفيعة تُبقي الميثودات القديمة متاحة لأي كود خارجي.

    كان المنطق معرَّفًا هنا في النسخ السابقة؛ صار في
    ``account_report_currency_utils`` ليتشاركه دفتر الشركاء ودفتر الأستاذ.

    ⚠ تغيّر شكل القيمة المُعادة في 19.0.1.3.0: صارت
    ``{column_group_key: {id: {currency_id: amount}}}`` بدل
    ``{id: {currency_id: amount}}`` — لأن الشكل القديم كان يدمج مجموعات
    الأعمدة (فترات المقارنة) في سلة واحدة وينتج رقمًا خاطئًا.
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