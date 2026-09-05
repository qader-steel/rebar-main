# -*- coding: utf-8 -*-
"""أدوات مشتركة: عرض المبالغ بعملاتها الأصلية + إجمالي لكل عملة على تقارير
المحاسبة في Odoo 19 Enterprise (دفتر الأستاذ العام + دفتر الشركاء + كشف
حساب العميل).

الخلفية المحاسبية (سبب وجود هذا الملف كله)
------------------------------------------
أودو يخزّن كل بند قيد مرتين:

* ``debit`` / ``credit`` / ``balance`` → دائمًا **بعملة الشركة**.
* ``amount_currency`` + ``currency_id`` → المبلغ **الأصلي** بعملة المستند.

المصيدة: عندما تكون عملة المستند **هي نفسها عملة الشركة**، يترك أودو
``amount_currency`` صفرًا (القيمة في ``balance``)، ثم **يُفرغ الخانة عمدًا**
عند العرض. فيرى المحاسب عمودًا فارغًا لكل سطور عملة شركته، ويحصل أي كود
يجمع ``SUM(amount_currency)`` على **صفر** لتلك العملة.

الإصلاح هنا شقّان:
  1. ``amount_in_line_currency_sql()`` — ``balance`` لسطور عملة الشركة
     و ``amount_currency`` لغيرها، داخل استعلام الإجماليات.
  2. ``fill_amount_currency_cells()`` — نفس المنطق على مستوى خانات العرض.

لماذا كل شيء يمرّ عبر ``_custom_line_postprocessor``؟
-----------------------------------------------------
المحاولات السابقة أعادت تعريف ميثودات داخلية
(``_get_aml_line`` و ``_report_expand_unfoldable_line_general_ledger``
و ``_get_report_line_move_line``). أثبت التشخيص على أودو 19 أن هذه
الميثودات **حُذفت من دفتر الأستاذ العام**: صار تقريرًا قياسيًا بسطر واحد
``groupby='account_id, id_with_accumulated_balance'`` ومحرّك مخصّص
``_report_custom_engine_general_ledger``. فكانت إعادة التعريف شفرة ميتة
لا تُستدعى ولا ترفع خطأً ولا تُسجِّل شيئًا.

``_custom_line_postprocessor(report, options, lines)`` خطاف **موثَّق** معرَّف
على ``account.report.custom.handler`` نفسه — أي على كل معالج تقرير بلا
استثناء — ويُستدعى في المسارين معًا:

    _get_lines(...)            → عرض التقرير كاملًا
    get_expanded_lines(...)    → فتح سطر واحد

فهو يستقبل السطور النهائية أيًّا كانت الطريقة التي بُنيت بها. لذلك لا
يتأثّر بإعادة هيكلة داخلية كالتي حدثت في 19 — وهو ما جعل المحاولات
السابقة تفشل بصمت.

⚠ حدٌّ معروف: فروقات الصرف
--------------------------
سطور فروقات أسعار الصرف تُقيَّد بعملة أجنبية و ``amount_currency = 0``
و ``balance ≠ 0``، فلا تدخل في أي من الإجماليين. سلوك مقصود (نعرض المبالغ
الأصلية لا إعادة تقييم) لكنه يُذكر صراحةً لأنه أول ما سيحاول المحاسب
مطابقته.
"""

import json
import logging

from odoo import _
from odoo.tools import SQL

_logger = logging.getLogger(__name__)


# ======================================================================
# 1) SQL — إصلاح مبلغ عملة الشركة
# ======================================================================

def company_currency_sql() -> SQL:
    """عملة شركة بند القيد، كاستعلام فرعي مترابط.

    استعلام فرعي وليس JOIN عمدًا: ``from_clause`` القادم من
    ``_get_report_query`` يخصّ Enterprise ولا يجوز أن نعدّله. جدول
    ``res_company`` صغير ويبقى في ذاكرة PostgreSQL، والاستعلام يظهر **مرة
    واحدة فقط** داخل دالة التجميع.
    """
    return SQL(
        "(SELECT rc.currency_id FROM res_company rc "
        "WHERE rc.id = account_move_line.company_id)"
    )


def amount_in_line_currency_sql() -> SQL:
    """المبلغ بعملة السطر الحقيقية — مع معالجة سطور عملة الشركة.

    مع تعدّد الشركات يبقى سليمًا: داخل مجموعة عملة واحدة، سطور الشركة التي
    عملتها هي تلك العملة تأخذ ``balance``، وغيرها ``amount_currency`` —
    وكلا الفرعين مُقوَّم بعملة المجموعة نفسها.
    """
    return SQL(
        """
        CASE
            WHEN account_move_line.currency_id = %s
            THEN account_move_line.balance
            ELSE account_move_line.amount_currency
        END
        """,
        company_currency_sql(),
    )


def build_currency_sums_query(report, options, groupby_sql: SQL,
                              groupby_ids=None) -> SQL:
    """استعلام إجماليات العملات مجمَّعًا حسب ``groupby_sql``.

    ``groupby_sql`` : ``account_move_line.account_id`` لدفتر الأستاذ،
                      ``account_move_line.partner_id`` لدفتر الشركاء.
    ``groupby_ids`` : قصر الاستعلام على هذه المعرّفات فقط (الأداء).

    النطاق ``from_beginning`` مقصود: المطلوب **الرصيد الختامي** بكل عملة
    (افتتاحي + حركة الفترة)، لا حركة الفترة وحدها.
    """
    queries = []

    for column_group_key, column_group_options in report._split_options_per_column_group(options).items():
        query = report._get_report_query(column_group_options, 'from_beginning')
        scope = SQL("AND %s = ANY(%s)", groupby_sql, list(groupby_ids)) if groupby_ids else SQL("")

        # وسائط موضعية عمدًا (لا مسمّاة): النمط المُثبت في أكواد محاسبة أودو.
        # التجميع على ``currency_id`` مباشرة ليبقى GROUP BY قابلًا للفهرسة،
        # ويظهر الاستعلام الفرعي مرة واحدة داخل دالة التجميع فقط.
        queries.append(SQL(
            """
            SELECT
                %s AS groupby,
                account_move_line.currency_id AS currency_id,
                %s AS column_group_key,
                COALESCE(SUM(%s), 0.0) AS amount_currency
            FROM %s
            WHERE %s
              AND %s IS NOT NULL
              AND account_move_line.currency_id IS NOT NULL
              %s
            GROUP BY %s, account_move_line.currency_id
            """,
            groupby_sql,
            column_group_key,
            amount_in_line_currency_sql(),
            query.from_clause,
            query.where_clause,
            groupby_sql,
            scope,
            groupby_sql,
        ))

    return SQL(' UNION ALL ').join(queries) if queries else SQL("")


def compute_currency_sums(report, options, groupby_sql: SQL, groupby_ids=None):
    """يرجع ``{column_group_key: {groupby_id: {currency_id: amount}}}``.

    ⚠ التجميع حسب ``column_group_key`` ضروري وليس تفصيلًا: عند تفعيل
    "المقارنة" يقسم أودو التقرير إلى أكثر من مجموعة أعمدة بنطاقات تاريخ
    مختلفة. دمجها في سلة واحدة يُظهر رقمًا = مجموع فترتين، لا وجود له في
    الدفتر ولا يمكن مطابقته بأي شيء.
    """
    query = build_currency_sums_query(report, options, groupby_sql, groupby_ids)
    if not query.code:
        return {}

    report.env.cr.execute(query)

    data = {}
    for row in report.env.cr.dictfetchall():
        key, currency_id = row.get('groupby'), row.get('currency_id')
        if not key or not currency_id:
            continue
        bucket = data.setdefault(row.get('column_group_key'), {}).setdefault(int(key), {})
        bucket[int(currency_id)] = bucket.get(int(currency_id), 0.0) + float(row.get('amount_currency') or 0.0)

    return data


# ======================================================================
# 2) مساعدات عامة
# ======================================================================

def has_amount_currency_column(options):
    """هل يعرض التقرير عمود Amount Currency أصلًا؟

    كلا التقريرين يحذفان العمود من ``options['columns']`` عندما لا يكون
    المستخدم ضمن ``base.group_multi_currency``. وبدونه لا مكان لعرض أي
    مبلغ أو إجمالي، فتبدو الميزة معطّلة بلا سبب ظاهر.
    """
    return any(c.get('expression_label') == 'amount_currency'
               for c in options.get('columns', []))


def extract_aml_id(report, line_id):
    """معرّف بند القيد من معرّف سطر التقرير — بالشكلين المعروفين.

    * دفتر الشركاء : آخر مقطع ``('...', 'account.move.line', <id>)``
    * دفتر الأستاذ : آخر مقطع ``({'groupby': 'id_with_accumulated_balance'},
      None, '["2026-09-03", 168]')`` — أي نص JSON عنصره الثاني هو المعرّف
      (نفس ما يقرؤه أودو نفسه لبناء زر المحادثة).
    """
    try:
        parsed = report._parse_line_id(line_id)
        if not parsed:
            return None
        markup, model, res_id = parsed[-1]

        if model == 'account.move.line' and res_id:
            return int(res_id)

        if model is None and isinstance(markup, dict) \
                and markup.get('groupby') == 'id_with_accumulated_balance' \
                and isinstance(res_id, str) and res_id.startswith('['):
            return int(json.loads(res_id)[1])
    except Exception:
        return None

    return None


def sort_currencies(env, currency_ids):
    """عملة الشركة أولًا ثم أبجديًا — ترتيب ثابت ومفهوم للمحاسب."""
    company_currency = env.company.currency_id
    return env['res.currency'].browse(sorted(currency_ids)).sorted(
        key=lambda c: (0 if c == company_currency else 1, c.name or '')
    )


# ======================================================================
# 3) تعبئة خانات Amount Currency
# ======================================================================

def fill_amount_currency_cells(report, options, lines):
    """يملأ خانة Amount Currency لكل سطر بند قيد، بما فيها عملة الشركة.

    أودو يُفرغ الخانة عمدًا لسطور عملة الشركة. نعيد ملأها من ``balance``
    فتُقرأ كل الأسطر بنفس الطريقة.

    الأداء: استعلام SQL **واحد** لكل بنود القيود الظاهرة، بدل قراءة كل
    سطر على حدة.
    """
    if not has_amount_currency_column(options):
        return

    aml_by_line = {}
    for idx, line in enumerate(lines):
        aml_id = extract_aml_id(report, line.get('id'))
        if aml_id:
            aml_by_line[idx] = aml_id

    if not aml_by_line:
        return

    report.env.cr.execute(
        """
        SELECT aml.id,
               aml.currency_id,
               aml.amount_currency,
               aml.balance,
               (SELECT rc.currency_id FROM res_company rc
                 WHERE rc.id = aml.company_id) AS company_currency_id
          FROM account_move_line aml
         WHERE aml.id = ANY(%s)
        """,
        (list(set(aml_by_line.values())),),
    )
    aml_data = {r['id']: r for r in report.env.cr.dictfetchall()}

    option_columns = options.get('columns') or []
    filled = 0

    for idx, aml_id in aml_by_line.items():
        row = aml_data.get(aml_id)
        if not row or not row.get('currency_id'):
            continue

        currency = report.env['res.currency'].browse(row['currency_id'])
        if row['currency_id'] == row.get('company_currency_id'):
            amount = row.get('balance') or 0.0
        else:
            amount = row.get('amount_currency') or 0.0

        cells = lines[idx].get('columns') or []
        if len(cells) != len(option_columns):
            continue

        for i, column in enumerate(option_columns):
            if column.get('expression_label') != 'amount_currency':
                continue
            # لا نلمس إلا خانة مجموعة الأعمدة التي ينتمي إليها هذا السطر —
            # وإلا ظهر مبلغ يناير أيضًا تحت عمود ديسمبر عند تفعيل المقارنة.
            # (سطور بند القيد تخصّ مجموعة واحدة، فنملأ التي لها قيمة أو
            # التي أفرغها أودو.)
            cells[i] = report._build_column_dict(
                amount, column, options=options, currency=currency,
            )
            filled += 1

    _logger.info(
        'QSS ✔ عُبّئت %s خانة عملة على %s سطر بند قيد.', filled, len(aml_by_line),
    )


# ======================================================================
# 4) حقن صفوف إجمالي العملات
# ======================================================================

def build_currency_total_columns(report, options, currency, sums_by_group, groupby_id):
    """خانات صف إجمالي عملة واحدة، خانةً خانة حسب مجموعة الأعمدة."""
    columns = []
    for col in options.get('columns', []):
        if col.get('expression_label') != 'amount_currency':
            # ``_build_column_dict(None, None)`` يعيد {} وهي الخانة الفارغة
            # القياسية في أودو.
            columns.append(report._build_column_dict(None, None))
            continue
        amount = (sums_by_group.get(col.get('column_group_key'), {})
                  .get(groupby_id, {}).get(currency.id, 0.0))
        columns.append(report._build_column_dict(
            amount, col, options=options, currency=currency,
        ))
    return columns


def inject_currency_totals(report, options, lines, model_name, groupby_sql):
    """يضيف صف إجمالي لكل عملة في نهاية سطور كل حساب/شريك.

    يعمل في المسارين معًا:
      * عرض التقرير كاملًا — سطر العنوان موجود مع أبنائه؛
      * فتح سطر واحد — الأبناء وحدهم، فيُشتقّ العنوان من معرّفاتهم.

    لا تُضاف إجماليات لمجموعة بلا أبناء (حساب مطويّ)، ولا لمجموعة فيها
    سطر "تحميل المزيد" (عرض جزئي).
    """
    if not lines:
        return lines

    if not has_amount_currency_column(options):
        _logger.warning(
            'QSS ⛔ عمود Amount Currency غير موجود — لن تظهر إجماليات العملات. '
            'السبب المعتاد: المستخدم ليس ضمن مجموعة "العملات المتعددة" '
            '(base.group_multi_currency)، فيحذف أودو العمود تلقائيًا. '
            'فعّلها من الإعدادات ▸ المحاسبة.'
        )
        return lines

    # ── تصنيف السطور حسب الحساب/الشريك ──────────────────────────────
    res_ids, has_child, has_load_more, last_index = [], {}, set(), {}

    for idx, line in enumerate(lines):
        rid = None
        try:
            rid = report._get_res_id_from_line_id(line.get('id'), model_name)
        except Exception:
            pass
        if not rid:
            continue

        rid = int(rid)
        if rid not in res_ids:
            res_ids.append(rid)
        last_index[rid] = idx

        parsed = report._parse_line_id(line.get('id')) or []
        markup, model, _res = parsed[-1] if parsed else (None, None, None)

        if markup == 'load_more':
            has_load_more.add(rid)
        elif model != model_name:
            # ليس سطر العنوان ⇒ ابن حقيقي
            has_child[rid] = idx

    targets = [r for r in res_ids if r in has_child and r not in has_load_more]
    if not targets:
        _logger.info(
            'QSS ⏭ لا توجد مجموعات مفتوحة لإضافة إجماليات (%s مجموعة مفحوصة).',
            len(res_ids),
        )
        return lines

    sums = compute_currency_sums(report, options, groupby_sql, groupby_ids=targets)
    _logger.info(
        'QSS 🔢 %s=%s | مجاميع العملات=%r',
        model_name, targets,
        {gk: {k: v for k, v in g.items() if k in targets} for gk, g in sums.items()},
    )

    # ── بناء صفوف الإجمالي وإدراجها ─────────────────────────────────
    to_insert = {}
    for rid in targets:
        currency_ids = set()
        for group_data in sums.values():
            currency_ids |= set(group_data.get(rid, {}))
        if not currency_ids:
            continue

        anchor = lines[last_index[rid]]
        parsed_anchor = report._parse_line_id(anchor['id']) or []
        anchor_model = parsed_anchor[-1][1] if parsed_anchor else None
        # العنوان هو السطر نفسه إن كان سطر الحساب، وإلا أبوه.
        parent_id = (anchor['id'] if anchor_model == model_name
                     else report._build_parent_line_id(parsed_anchor))
        level = anchor.get('level', 3)

        rows = []
        for currency in sort_currencies(report.env, currency_ids):
            amounts = [g.get(rid, {}).get(currency.id, 0.0) for g in sums.values()]
            # صفر حقيقي في كل المجموعات لا يستحق صفًا. ``is_zero`` بدل
            # ``not amount`` حتى لا تُعرض بقايا تقريب مثل 1e-13 كصف "0.00".
            if all(currency.is_zero(a) for a in amounts):
                continue
            rows.append({
                'id': report._get_generic_line_id(
                    None, None, parent_line_id=parent_id,
                    markup='qss_currency_total_%s' % currency.id,
                ),
                'parent_id': parent_id,
                'name': _('%s Total') % currency.name,
                'level': level,
                'columns': build_currency_total_columns(
                    report, options, currency, sums, rid,
                ),
                'unfoldable': False,
                'unfolded': False,
                'class': 'o_account_report_total qss-currency-total',
            })

        if rows:
            to_insert[last_index[rid]] = rows

    if not to_insert:
        _logger.info('QSS ⏭ كل المجاميع أصفار — لم يُضف أي صف.')
        return lines

    out = []
    for idx, line in enumerate(lines):
        out.append(line)
        out.extend(to_insert.get(idx, ()))

    _logger.info(
        'QSS ✅ أُضيف %s صف إجمالي عملة على %s مجموعة.',
        sum(len(v) for v in to_insert.values()), len(to_insert),
    )
    return out