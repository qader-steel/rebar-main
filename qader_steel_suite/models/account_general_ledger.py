# -*- coding: utf-8 -*-
"""دفتر الأستاذ العام (General Ledger) — عرض كل سطر بعملته + إجمالي لكل عملة.

1. **تعبئة عمود Amount Currency** لكل بند قيد، بما فيها سطور عملة الشركة
   التي يُفرغها أودو عمدًا.
2. **صف إجمالي لكل عملة في نهاية سطور كل حساب** — "USD Total" و "IQD Total".

⚠ لماذا فشلت المحاولتان السابقتان (توثيق ضروري)
------------------------------------------------
المحاولة الأولى أعادت تعريف ``_get_report_line_move_line``، والثانية
``_get_aml_line`` و ``_report_expand_unfoldable_line_general_ledger``.
أثبت التشخيص على قاعدة بيانات أودو 19 حيّة أن **الثلاثة غير موجودة على
معالج دفتر الأستاذ العام في 19**:

    _get_aml_line                                 -> يعرّفها كودنا وحده
    _report_expand_unfoldable_line_general_ledger -> يعرّفها كودنا وحده
    _get_account_title_line                       -> غير معرّفة إطلاقًا

فكانت شفرة ميتة: لا تُستدعى، ولا ترفع خطأً، ولا تُسجِّل شيئًا — ولذلك لم
يظهر أي أثر في التقرير.

**أودو 19 أعاد بناء دفتر الأستاذ العام**: لم يعد تقريرًا يبني سطوره عبر
``_dynamic_lines_generator``، بل صار تقريرًا قياسيًا بسطر واحد:

    account.report.line id=68
        groupby = 'account_id, id_with_accumulated_balance'
        كل التعابير: engine='custom',
                     formula='_report_custom_engine_general_ledger'

وسطور الحسابات تستخدم ``_report_expand_unfoldable_line_with_groupby``
القياسية، لا أي ميثود خاصة بدفتر الأستاذ.

الحل: ``_custom_line_postprocessor``
-------------------------------------
خطاف **موثَّق** معرَّف على ``account.report.custom.handler`` نفسه — أي على
كل معالج تقرير بلا استثناء — ويُستدعى في المسارين:

    _get_lines(...)          → عرض التقرير كاملًا
    get_expanded_lines(...)  → فتح حساب واحد

فهو يستقبل السطور النهائية أيًّا كانت الطريقة التي بُنيت بها، ولا يتأثّر
بإعادة الهيكلة الداخلية التي أوقعت المحاولتين السابقتين.

لماذا الإجمالي تحت كل حساب لا أسفل التقرير؟
--------------------------------------------
قرار محاسبي: جمع الذمم المدينة + الدائنة + الإيرادات + المصاريف بالدولار
لا يعطي رقمًا يمكن تدقيقه. المفيد هو **رصيد كل حساب بكل عملة**.

مبدأ السلامة
------------
إضافة **عرضية فقط**: لا أعمدة جديدة، ولا مساس بأرقام مدين/دائن/رصيد.
الخطاف ملفوف بـ try/except، والاستعلام داخل savepoint ومقصور على الحسابات
المعروضة وحدها.
"""

import logging

from odoo import models
from odoo.tools import SQL

from . import account_report_currency_utils as cur_utils

_logger = logging.getLogger(__name__)

ACCOUNT_GROUPBY = SQL('account_move_line.account_id')


class GeneralLedgerCurrencyHandler(models.AbstractModel):
    _inherit = 'account.general.ledger.report.handler'

    def _custom_line_postprocessor(self, report, options, lines):
        """الخطاف الوحيد الذي نستخدمه — راجع ترويسة الملف لسبب ذلك."""
        lines = super()._custom_line_postprocessor(report, options, lines)

        try:
            # ميزان المراجعة يرث هذا المعالج ويميّز نفسه بهذا الخيار.
            # إجماليات العملات تخصّ دفتر الأستاذ العام.
            if options.get('general_ledger_strict_range'):
                return lines

            _logger.info(
                'QSS [GL] ▶ postprocessor: %s سطر | report_id=%s | '
                'عمود العملة=%s',
                len(lines), options.get('report_id'),
                cur_utils.has_amount_currency_column(options),
            )

            cur_utils.fill_amount_currency_cells(report, options, lines)

            with self.env.cr.savepoint():
                lines = cur_utils.inject_currency_totals(
                    report, options, lines, 'account.account', ACCOUNT_GROUPBY,
                )
        except Exception:
            # تحسين عرضي فقط — لا يجوز أن يكسر تقريرًا محاسبيًا.
            _logger.exception(
                'qader_steel_suite: تعذّرت معالجة عملات دفتر الأستاذ العام'
            )

        return lines