# -*- coding: utf-8 -*-
"""دفتر الأستاذ العام (General Ledger) — عرض كل سطر بعملته + إجمالي لكل عملة.

1. **تعبئة عمود Amount Currency** لكل بند قيد، بما فيها سطور عملة الشركة.
2. **صف إجمالي لكل عملة تحت كل حساب** — عند فتح أي حساب يظهر في نهايته
   "IQD Total" و "USD Total"، فيرى المحاسب رصيد الحساب مفصولًا بالعملة.

⚠ تصحيح مهم (النسخة الأولى لم تكن تعمل إطلاقًا)
------------------------------------------------
كانت النسخة الأولى تعيد تعريف ``_get_report_line_move_line``. هذه الميثود
**غير موجودة على معالج دفتر الأستاذ العام** — إنها تخصّ *دفتر الشركاء* وحده.
دفتر الأستاذ يبني سطوره عبر::

    def _get_aml_line(self, report, parent_line_id, options, eval_dict,
                      init_bal_by_col_group)

فكان الكود السابق **شفرة ميتة**: لا يُستدعى أبدًا، ولا يرفع استثناءً، ولا
يكتب سطرًا في اللوق — ولذلك لم يظهر أي شيء في التقرير. صُحّح هنا باعتماد
الاسم الصحيح، بعد مطابقته على مصدر ``account_reports`` الفعلي.

لماذا قد لا تظهر الإجماليات رغم ذلك؟ (سبب شائع جدًا)
-----------------------------------------------------
``_custom_options_initializer`` في دفتر الأستاذ العام يحذف العمود بالكامل::

    if self.env.user.has_group('base.group_multi_currency'):
        options['multi_currency'] = True
    else:
        options['columns'] = [column for column in options['columns']
                              if column['expression_label'] != 'amount_currency']

فإن لم يكن المستخدم ضمن مجموعة **"العملات المتعددة"** فلا وجود لعمود
Amount Currency أصلًا، ولا مكان لعرض المبالغ ولا الإجماليات. الحل: تفعيل
"العملات المتعددة" من الإعدادات ▸ المحاسبة. الكود يكتب تحذيرًا صريحًا في
اللوق عند حدوث ذلك بدل أن يبدو معطّلًا بلا سبب.

لماذا "تحت كل حساب" وليس إجمالي عام أسفل التقرير؟
--------------------------------------------------
قرار محاسبي مقصود. الإجمالي العام لكل العملات عبر **كل** الحسابات ليس رقمًا
ذا معنى: جمع الذمم المدينة + الذمم الدائنة + الإيرادات + المصاريف بالدولار
لا يمثّل شيئًا يمكن تدقيقه. الرقم المفيد هو **رصيد كل حساب بكل عملة**.

مبدأ السلامة
------------
كل إضافة **عرضية فقط**: لا أعمدة جديدة، ولا مساس بأرقام مدين/دائن/رصيد. كل
خطاف ملفوف بـ try/except، والاستعلام داخل savepoint ومقصور على الحساب
المفتوح وحده.
"""

import logging

from odoo import models
from odoo.tools import SQL

from . import account_report_currency_utils as cur_utils

_logger = logging.getLogger(__name__)

ACCOUNT_GROUPBY = SQL('account_move_line.account_id')


class GeneralLedgerCurrencyHandler(models.AbstractModel):
    _inherit = 'account.general.ledger.report.handler'

    # ------------------------------------------------------------------
    # 1) تعبئة خانة Amount Currency لكل سطر
    # ------------------------------------------------------------------

    def _get_aml_line(self, report, parent_line_id, options, eval_dict, *args, **kwargs):
        """الاسم الصحيح لبنّاء سطر بند القيد في دفتر الأستاذ العام.

        ``eval_dict`` بالشكل ``{column_group_key: aml_query_result}`` — وهو
        تمامًا ما تحتاجه دالة التعبئة، فيُمرَّر كما هو.

        أودو يُفرغ الخانة عمدًا لسطور عملة الشركة::

            col_value = None if col_currency == self.env.company.currency_id else col_value

        ونحن نعيد ملأها من ``balance``.
        """
        line = super()._get_aml_line(
            report, parent_line_id, options, eval_dict, *args, **kwargs
        )

        try:
            cur_utils.patch_amount_currency_cells(report, options, line, eval_dict)
        except Exception:
            _logger.exception(
                'qader_steel_suite: تعذّر تعبئة خانة العملة في دفتر الأستاذ العام'
            )

        return line

    # ------------------------------------------------------------------
    # 2) صف إجمالي لكل عملة تحت كل حساب
    # ------------------------------------------------------------------

    def _report_expand_unfoldable_line_general_ledger(
        self, line_dict_id, groupby, options, progress, offset, *args, **kwargs
    ):
        result = super()._report_expand_unfoldable_line_general_ledger(
            line_dict_id, groupby, options, progress, offset, *args, **kwargs
        )

        try:
            # (أ) الترقيم: لا نضيف الإجماليات إلا بعد اكتمال عرض كل سطور
            #     الحساب، وإلا تكرّر الصف مع كل صفحة "تحميل المزيد".
            if result.get('has_more'):
                return result

            report = self.env['account.report'].browse(options['report_id'])

            # (ب) هذا المعالج موروث أيضًا في تقارير أخرى (ميزان المراجعة
            #     يرث معالج دفتر الأستاذ). إجماليات العملات مطلوبة في دفتر
            #     الأستاذ العام وحده، فلا نتدخّل في غيره.
            gl_report = self.env.ref(
                'account_reports.general_ledger_report', raise_if_not_found=False,
            )
            if not gl_report or report.id != gl_report.id:
                return result

            account_id = cur_utils.extract_line_id_value(
                report, line_dict_id, 'account.account',
            )
            if not account_id:
                return result

            # savepoint: يبقي معاملة أودو الخارجية سليمة حتى لو رفض
            # PostgreSQL الاستعلام على إصدار Enterprise مستقبلي.
            # groupby_ids: قصر الاستعلام على هذا الحساب وحده (الأداء).
            with self.env.cr.savepoint():
                sums = cur_utils.compute_currency_sums(
                    report, options, ACCOUNT_GROUPBY, groupby_ids=[account_id],
                )

            cur_utils.append_currency_total_lines(
                report, options, result, line_dict_id, sums, account_id,
            )

        except Exception:
            _logger.exception(
                'qader_steel_suite: تعذّر إضافة إجماليات العملات '
                'في دفتر الأستاذ العام'
            )

        return result