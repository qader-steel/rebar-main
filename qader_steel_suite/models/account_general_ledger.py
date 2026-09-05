# -*- coding: utf-8 -*-
"""دفتر الأستاذ العام (General Ledger) — عرض كل سطر بعملته + إجمالي لكل عملة.

نفس منطق دفتر الشركاء بالضبط، لكن التجميع **حسب الحساب** بدل الشريك:

1. **تعبئة عمود Amount Currency** لكل بند قيد، بما فيها سطور عملة الشركة
   التي يتركها أودو فارغة (القيمة في ``balance``).
2. **صف إجمالي لكل عملة تحت كل حساب** — عند فتح أي حساب يظهر في نهايته
   "IQD Total" و "USD Total"، فيرى المحاسب رصيد الحساب مفصولًا بالعملة.

لماذا "تحت كل حساب" وليس إجمالي عام أسفل التقرير؟
--------------------------------------------------
قرار محاسبي مقصود. الإجمالي العام لكل العملات عبر **كل** الحسابات ليس رقمًا
ذا معنى: جمع الذمم المدينة + الذمم الدائنة + الإيرادات + المصاريف بالدولار
لا يمثّل شيئًا يمكن للمحاسب استخدامه أو تدقيقه. الرقم المفيد والقابل
للمطابقة هو **رصيد كل حساب بكل عملة**، وهو ما يظهر هنا — تمامًا كما يظهر
رصيد كل شريك بكل عملة في دفتر الشركاء.

إن طُلب لاحقًا إجمالي عام أسفل التقرير، يُضاف عبر
``_dynamic_lines_generator`` — لكنه لم يُضَف الآن تجنّبًا لرقم مضلِّل.

⚠ تحذير تنفيذي — يجب التحقق بعد الترقية
----------------------------------------
``account.general.ledger.report.handler`` نموذج من Odoo **Enterprise**، ولم
يكن متاحًا للفحص أثناء كتابة هذا الملف. تحديدًا **اسما الميثودين
المُعاد تعريفهما أدناه غير مؤكَّدين** مقابل مصدر Enterprise:

    _get_report_line_move_line
    _report_expand_unfoldable_line_general_ledger

إن كان أيٌّ منهما باسم مختلف في نسختكم، فلن يُستدعى الكود إطلاقًا وستكون
الميزة **صامتة تمامًا** — لا خطأ ولا سطر في اللوق ولا صفوف إجمالي. لذلك:
**افتح دفتر الأستاذ العام مرة واحدة بعد الترقية، افتح أي حساب، وتأكد من
ظهور صفوف "IQD Total" / "USD Total"** قبل الاعتماد عليه. إن لم تظهر، أرسل
لي اسمي الميثودين من مصدر Enterprise عندكم وأصحّحهما فورًا.

مبدأ السلامة
------------
كل إضافة **عرضية فقط**: لا أعمدة جديدة، ولا مساس بأرقام مدين/دائن/رصيد. كل
خطاف ملفوف بـ try/except (بما فيه استدعاء ``super()`` نفسه)، والاستعلام
داخل savepoint ومقصور على الحساب المفتوح وحده.
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

    def _get_report_line_move_line(self, options, aml_query_result, *args, **kwargs):
        """التوقيع مرن عمدًا: هذه الدالة يختلف توقيعها بين دفتر الأستاذ
        ودفتر الشركاء وبين الإصدارات (currency_table، level_shift ...).
        نمرّر كل شيء كما هو إلى super."""
        line = super()._get_report_line_move_line(
            options, aml_query_result, *args, **kwargs
        )

        try:
            cur_utils.patch_amount_currency_cell(
                self.env, options, line, aml_query_result,
            )
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
            # (أ) توسيع فرعي (الحساب مقسَّمًا حسب شريك/شهر ...): إجمالي
            #     الحساب كاملًا لا يخصّ المجموعة الفرعية. مثال الخطأ الذي
            #     نتجنّبه: "١٢١٠٠٠ ذمم مدينة › الشريك أ" يعرض "USD Total
            #     50,000" بينما نصيب الشريك أ هو ٤٠٠ فقط.
            if groupby:
                return result

            # (ب) الترقيم: لا نضيف الإجماليات إلا بعد اكتمال عرض كل سطور
            #     الحساب، وإلا تكرّر الصف مع كل صفحة.
            if result.get('has_more'):
                return result

            report = self.env['account.report'].browse(options['report_id'])

            account_id = cur_utils.extract_line_id_value(
                report, line_dict_id, 'account.account',
            )
            if not account_id:
                return result

            with self.env.cr.savepoint():
                sums = cur_utils.compute_currency_sums(
                    report, options, ACCOUNT_GROUPBY, groupby_ids=[account_id],
                )

            cur_utils.append_currency_total_lines(
                self.env, report, options, result, line_dict_id, sums, account_id,
            )

        except Exception:
            _logger.exception(
                'qader_steel_suite: تعذّر إضافة إجماليات العملات '
                'في دفتر الأستاذ العام'
            )

        return result