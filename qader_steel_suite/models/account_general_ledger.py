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

    # علامة تحميل: إن لم يظهر هذا السطر في اللوق عند إقلاع الخادم، فالملف
    # لم يُحمَّل أصلًا (الموديول لم يُرقَّ، أو الملف في مسار خاطئ).
    _logger.info(
        'QSS [GL] ✔ تم تحميل امتداد دفتر الأستاذ العام '
        '(GeneralLedgerCurrencyHandler) — الميثودات المُعاد تعريفها: '
        '_get_aml_line، _report_expand_unfoldable_line_general_ledger'
    )

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
            # تُسجَّل مرة واحدة لكل طلب (debug) — لإثبات أن الميثود تُستدعى.
            if not self.env.context.get('qss_gl_aml_logged'):
                _logger.info(
                    'QSS [GL] ✔ _get_aml_line تُستدعى فعلًا. مفاتيح الصف: %r',
                    sorted(next(iter(eval_dict.values()), {}).keys())
                    if eval_dict else 'eval_dict فارغ',
                )
                self.env.context = dict(self.env.context, qss_gl_aml_logged=True)
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

        _logger.info(
            'QSS [GL] ▶ استُدعي توسيع الحساب: line=%r groupby=%r report_id=%s '
            'has_more=%s',
            line_dict_id, groupby, options.get('report_id'),
            result.get('has_more'),
        )

        try:
            # (أ) الترقيم: لا نضيف الإجماليات إلا بعد اكتمال عرض كل سطور
            #     الحساب، وإلا تكرّر الصف مع كل صفحة "تحميل المزيد".
            if result.get('has_more'):
                _logger.info('QSS [GL] ⏸ has_more=True — تأجيل الإجماليات للصفحة الأخيرة.')
                return result

            report = self.env['account.report'].browse(options['report_id'])

            # (ب) هذا المعالج موروث أيضًا في ميزان المراجعة، الذي يميّز نفسه
            #     بالخيار ``general_ledger_strict_range``. إجماليات العملات
            #     تخصّ دفتر الأستاذ العام، فلا نتدخّل في ميزان المراجعة.
            #
            # ⚠ إصلاح 19.0.1.3.2: كان الشرط سابقًا مطابقة صارمة مع
            #     ``account_reports.general_ledger_report``. هذا يكسر الميزة
            #     في أي قاعدة فيها **نسخة محلّية (variant)** من دفتر الأستاذ
            #     — وهو الحال في معظم تركيبات l10n — لأن
            #     ``options['report_id']`` يكون حينها معرّف النسخة لا الأصل،
            #     فيخرج الكود مبكرًا ولا يظهر أي إجمالي إطلاقًا.
            if options.get('general_ledger_strict_range'):
                _logger.info(
                    'QSS [GL] ⏭ general_ledger_strict_range=True (ميزان مراجعة) '
                    '— تُتخطّى إجماليات العملات عمدًا.'
                )
                return result

            account_id = cur_utils.extract_line_id_value(
                report, line_dict_id, 'account.account',
            )
            if not account_id:
                _logger.warning(
                    'QSS [GL] ⛔ تعذّر استخراج معرّف الحساب من %r — '
                    'لن تُضاف إجماليات.', line_dict_id,
                )
                return result

            # savepoint: يبقي معاملة أودو الخارجية سليمة حتى لو رفض
            # PostgreSQL الاستعلام على إصدار Enterprise مستقبلي.
            # groupby_ids: قصر الاستعلام على هذا الحساب وحده (الأداء).
            with self.env.cr.savepoint():
                sums = cur_utils.compute_currency_sums(
                    report, options, ACCOUNT_GROUPBY, groupby_ids=[account_id],
                )

            _logger.info(
                'QSS [GL] 🔢 حساب=%s | عمود Amount Currency موجود=%s | '
                'مجاميع العملات=%r',
                account_id,
                cur_utils.has_amount_currency_column(options),
                {gk: v.get(account_id) for gk, v in sums.items()},
            )

            before = len(result.get('lines') or [])
            cur_utils.append_currency_total_lines(
                report, options, result, line_dict_id, sums, account_id,
            )
            added = len(result.get('lines') or []) - before
            _logger.info('QSS [GL] ✅ أُضيف %s صف إجمالي عملة للحساب %s.', added, account_id)

        except Exception:
            _logger.exception(
                'qader_steel_suite: تعذّر إضافة إجماليات العملات '
                'في دفتر الأستاذ العام'
            )

        return result