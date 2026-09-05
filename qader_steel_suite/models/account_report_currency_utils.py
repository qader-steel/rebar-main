# -*- coding: utf-8 -*-
"""أدوات مشتركة لعرض المبالغ بعملاتها الأصلية وإضافة صفوف إجمالي لكل عملة
على تقارير المحاسبة في Odoo 19 Enterprise (دفتر الشركاء + دفتر الأستاذ العام).

لماذا ملف دوال عادية وليس Mixin؟
--------------------------------
تقارير المحاسبة في Enterprise هي ``AbstractModel`` لها ترتيب وراثة (MRO)
حسّاس. إقحام ``_inherit`` إضافي في هذا الترتيب خطر لا داعي له: استدعاء دالة
عادية لا يمكنه أبدًا تغيير مخطط التقرير أو ترتيب وراثته.

الخلفية المحاسبية (سبب وجود هذا الملف كله)
------------------------------------------
أودو يخزّن كل بند قيد مرتين:

* ``debit`` / ``credit`` / ``balance`` → دائمًا **بعملة الشركة** (الدينار
  هنا)، محوَّلة بسعر صرف تاريخ القيد.
* ``amount_currency`` + ``currency_id`` → المبلغ **الأصلي** بعملة المستند.

والمصيدة: عندما تكون عملة المستند **هي نفسها عملة الشركة**، يترك أودو
``amount_currency`` مساويًا للصفر لأن القيمة موجودة أصلًا في ``balance``.

نتيجة ذلك أن أي كود يجمع ``SUM(amount_currency)`` بسذاجة يحصل على **صفر**
لكل سطور عملة الشركة — فيظهر إجمالي الدولار ويختفي إجمالي الدينار تمامًا.

الدالة ``amount_in_line_currency_sql()`` هي الإصلاح: ``balance`` لسطور عملة
الشركة و ``amount_currency`` لغيرها. الإشارة متوافقة بين الحقلين (مدين
موجب، دائن سالب) فجمعهما معًا سليم محاسبيًا.

⚠ حدٌّ معروف: فروقات الصرف
--------------------------
سطور فروقات أسعار الصرف تُقيَّد بـ ``currency_id`` أجنبية و
``amount_currency = 0`` و ``balance ≠ 0``. هذه السطور **لا تدخل** في أي من
الإجماليين: لا في إجمالي العملة الأجنبية (مبلغها الأصلي صفر) ولا في إجمالي
الدينار (عملتها ليست الدينار). لذلك قد لا يساوي "إجمالي الدينار + إجمالي
الدولار محوَّلًا" عمودَ الرصيد بعملة الشركة المجاور. هذا سلوك مقصود — الرقم
المعروض هو **المبلغ الأصلي بكل عملة** لا إعادة تقييم — لكنه يُذكر هنا
صراحةً لأنه أول ما سيحاول المحاسب مطابقته.
"""

import logging

from odoo.tools import SQL
from odoo.tools.misc import formatLang

_logger = logging.getLogger(__name__)

# المفاتيح التي قد يحمل بها صفُّ نتيجة SQL معرّف بند القيد، حسب التقرير
# والإصدار. تُجرَّب بالترتيب. ملاحظة: ``id`` عام جدًا، فلا يُستخدم إلا بعد
# التحقق من أن الصف يشبه صف بند قيد فعلًا (راجع ``looks_like_aml_row``).
AML_ID_KEYS = ('aml_id', 'move_line_id', 'line_id', 'id')


# ======================================================================
# 1) SQL — إصلاح مبلغ عملة الشركة
# ======================================================================

def company_currency_sql() -> SQL:
    """عملة شركة بند القيد، كاستعلام فرعي مترابط.

    استعلام فرعي وليس JOIN عمدًا: ``from_clause`` القادم من
    ``_get_report_query`` يخصّ Enterprise ولا يجوز أن نعدّله. جدول
    ``res_company`` صغير جدًا ويبقى في ذاكرة PostgreSQL، والاستعلام يظهر
    **مرة واحدة فقط** داخل دالة التجميع.
    """
    return SQL(
        "(SELECT rc.currency_id FROM res_company rc "
        "WHERE rc.id = account_move_line.company_id)"
    )


def amount_in_line_currency_sql() -> SQL:
    """المبلغ بعملة السطر الحقيقية — مع معالجة سطور عملة الشركة.

    إن كانت عملة السطر هي عملة الشركة فالقيمة الصحيحة هي ``balance``؛ لأن
    أودو يترك ``amount_currency`` صفرًا في تلك الحالة. خلاف ذلك
    ``amount_currency`` هو المبلغ الأصلي المطلوب.

    مع تعدّد الشركات يبقى هذا سليمًا: داخل مجموعة عملة واحدة، سطور الشركة
    التي عملتها هي تلك العملة تأخذ ``balance``، وسطور الشركات الأخرى تأخذ
    ``amount_currency`` — وكلا الفرعين مُقوَّم بعملة المجموعة نفسها.
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
    """يبني استعلام إجماليات العملات مجمّعًا حسب ``groupby_sql``.

    ``groupby_sql``  : عمود التجميع — ``account_move_line.partner_id``
                       لدفتر الشركاء، و ``account_move_line.account_id``
                       لدفتر الأستاذ العام.
    ``groupby_ids``  : قصر الاستعلام على هذه المعرّفات فقط. مهم للأداء:
                       بدونه يمسح كل الشركاء/الحسابات في كل مرة يُفتح فيها
                       سطر واحد (مع "فتح الكل" على ٨٠٠ شريك = ٨٠٠ مسح كامل).

    النطاق ``from_beginning`` مقصود: الرقم المطلوب هو **الرصيد الختامي**
    بكل عملة (افتتاحي + حركة الفترة)، لا حركة الفترة وحدها — وهو ما يطابق
    صف "الرصيد الافتتاحي" الذي يعرضه التقريران أصلًا.
    """
    queries = []
    grouped = report._split_options_per_column_group(options)

    for column_group_key, column_group_options in grouped.items():
        query = report._get_report_query(column_group_options, 'from_beginning')

        # قصر النطاق على السجلات المطلوبة فقط (الأداء).
        if groupby_ids:
            scope = SQL("AND %s = ANY(%s)", groupby_sql, list(groupby_ids))
        else:
            scope = SQL("")

        # وسائط موضعية عمدًا (لا مسمّاة): النمط المُثبت في أكواد محاسبة
        # أودو. الترتيب أدناه يطابق ترتيب %s في النص تمامًا.
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
            groupby_sql,                    # SELECT ... AS groupby
            column_group_key,               # SELECT ... AS column_group_key
            amount_in_line_currency_sql(),  # COALESCE(SUM(...))
            query.from_clause,              # FROM
            query.where_clause,             # WHERE
            groupby_sql,                    # AND ... IS NOT NULL
            scope,                          # AND ... = ANY(...)
            groupby_sql,                    # GROUP BY
        ))

    if not queries:
        return SQL("")

    return SQL(' UNION ALL ').join(queries)


def compute_currency_sums(report, options, groupby_sql: SQL, groupby_ids=None):
    """يرجع ``{column_group_key: {groupby_id: {currency_id: amount}}}``.

    ⚠ التجميع حسب ``column_group_key`` **ضروري** وليس تفصيلًا: عند تفعيل
    "المقارنة" (Comparison) يقسم أودو التقرير إلى أكثر من مجموعة أعمدة،
    ولكل مجموعة نطاق تاريخ مختلف. النسخة الأولى من هذا الكود كانت تجمع كل
    المجموعات في سلة واحدة، فيظهر للمحاسب رقم = مجموع فترتين معًا، وهو رقم
    لا وجود له في الدفتر ولا يمكن مطابقته بأي شيء.
    """
    query = build_currency_sums_query(report, options, groupby_sql, groupby_ids)
    if not query.code:
        return {}

    report.env.cr.execute(query)
    rows = report.env.cr.dictfetchall()

    data = {}
    for row in rows:
        key = row.get('groupby')
        currency_id = row.get('currency_id')
        group_key = row.get('column_group_key')
        if not key or not currency_id:
            continue
        amount = float(row.get('amount_currency') or 0.0)
        bucket = data.setdefault(group_key, {}).setdefault(int(key), {})
        bucket[int(currency_id)] = bucket.get(int(currency_id), 0.0) + amount

    return data


# ======================================================================
# 2) تعبئة خانة Amount Currency في سطور التقرير
# ======================================================================

def looks_like_aml_row(row):
    """هل يشبه هذا الصف نتيجة استعلام بند قيد؟

    حارس ضد تغيّر توقيع Enterprise: لو صار الوسيط الثاني شيئًا آخر (قاموسًا
    مختلفًا مثلًا) نفضّل الانسحاب بصمت على قراءة ``id`` من قاموس غريب وطباعة
    مبلغ لا علاقة له بالسطر — وهو خطأ صامت لا يرفع استثناءً ولا يُسجَّل.
    """
    return isinstance(row, dict) and (
        'currency_id' in row or 'amount_currency' in row or 'balance' in row
    )


def currency_from_value(env, value):
    """يحوّل قيمة عملة من الأشكال المختلفة التي قد تصل من SQL إلى سجل."""
    if not value:
        return env['res.currency']

    if isinstance(value, int):
        return env['res.currency'].browse(value)

    if isinstance(value, (tuple, list)) and value and isinstance(value[0], int):
        return env['res.currency'].browse(value[0])

    if getattr(value, '_name', None) == 'res.currency':
        return value[:1]

    return env['res.currency']


def resolve_line_currency(env, row):
    """يرجع ``(currency, amount)`` لصف بند قيد واحد.

    الأداء: يُقرأ كل شيء من صف SQL نفسه ما أمكن. الرجوع إلى ``browse()``
    لقراءة بند القيد هو المسار الأخير فقط — النسخة الأولى كانت تستدعي
    ``browse().exists()`` لكل سطر، أي ~٣ استعلامات لكل بند قيد (١٥٬٠٠٠
    استعلام على دفتر فيه ٥٬٠٠٠ سطر)، وهو ما يُسقط تصدير PDF/XLSX بمهلة
    التنفيذ.
    """
    if not isinstance(row, dict):
        return env['res.currency'], None

    currency = currency_from_value(env, row.get('currency_id'))

    # ملاحظة مقصودة: ``0.0`` قيمة صالحة هنا ويجب أن تمرّ إلى منطق
    # عملة الشركة أدناه (حيث تُستبدل بـ balance). لذلك نفحص None/False/''
    # صراحةً بدل ``is not None`` أو الاعتماد على صدق القيمة.
    raw_amount = row.get('amount_currency')
    amount = None if raw_amount in (None, False, '') else raw_amount

    # سطور عملة الشركة: أودو يترك amount_currency صفرًا والقيمة في balance.
    if currency and row.get('balance') not in (None, False, ''):
        company_id = row.get('company_id')
        company_currency = env['res.currency']
        if company_id:
            company_currency = env['res.company'].browse(company_id).currency_id
        if not company_currency:
            company_currency = env.company.currency_id
        if currency == company_currency and not amount:
            amount = row['balance']

    # المسار الأخير: لم يكفِ الصف، نقرأ بند القيد نفسه.
    if not currency or amount is None:
        aml_id = next((row.get(k) for k in AML_ID_KEYS if row.get(k)), None)
        if aml_id:
            aml = env['account.move.line'].browse(aml_id).exists()
            if aml:
                if not currency:
                    currency = aml.currency_id or aml.company_currency_id
                if amount is None:
                    amount = aml.amount_currency
                company_currency = aml.company_currency_id or aml.company_id.currency_id
                if currency == company_currency and not amount:
                    amount = aml.balance

    if not currency:
        currency = env.company.currency_id

    return currency, amount


def patch_amount_currency_cell(env, options, line, row):
    """يملأ خانة Amount Currency القياسية دون تغيير مخطط التقرير.

    ⚠ يجب مطابقة ``column_group_key``: عند تفعيل المقارنة يحتوي
    ``options['columns']`` على خانة ``amount_currency`` **لكل مجموعة
    أعمدة**. النسخة الأولى كانت تكتب مبلغ السطر في كل تلك الخانات، فيظهر
    مبلغ يناير أيضًا تحت عمود ديسمبر — أي إفساد لعمود قياسي في أودو،
    وليس مجرد إضافة عرضية.
    """
    if not looks_like_aml_row(row):
        return

    cells = line.get('columns') or []
    option_columns = options.get('columns') or []

    if not cells or len(cells) != len(option_columns):
        return

    row_group_key = row.get('column_group_key')

    currency, amount = resolve_line_currency(env, row)
    if not currency or amount is None:
        return

    for index, column in enumerate(option_columns):
        if column.get('expression_label') != 'amount_currency':
            continue
        # لا نلمس إلا خانة مجموعة الأعمدة التي ينتمي إليها هذا السطر.
        if row_group_key and column.get('column_group_key') != row_group_key:
            continue

        cell = cells[index]
        cell['no_format'] = amount
        # formatLang يعرض رمز العملة بنفسه — لا نضيف اسم العملة مرة ثانية.
        cell['name'] = formatLang(env, amount, currency_obj=currency)


# ======================================================================
# 3) بناء صفوف إجمالي العملات
# ======================================================================

def sort_currencies(env, currency_ids):
    """عملة الشركة أولًا ثم أبجديًا — ترتيب ثابت ومفهوم للمحاسب."""
    company_currency = env.company.currency_id
    currencies = env['res.currency'].browse(sorted(currency_ids))
    return currencies.sorted(
        key=lambda c: (0 if c == company_currency else 1, c.name or '')
    )


def build_currency_total_columns(env, options, currency, sums_by_group, groupby_id):
    """يبني خانات صف إجمالي عملة واحدة، خانةً خانة حسب مجموعة الأعمدة."""
    columns = []

    for col in options.get('columns', []):
        expression_label = col.get('expression_label')

        if expression_label != 'amount_currency':
            columns.append({
                'name': '',
                'no_format': None,
                'expression_label': expression_label,
                'figure_type': 'string',
            })
            continue

        group_key = col.get('column_group_key')
        amount = (
            sums_by_group.get(group_key, {})
            .get(groupby_id, {})
            .get(currency.id, 0.0)
        )

        columns.append({
            'name': formatLang(env, amount, currency_obj=currency),
            'no_format': amount,
            'expression_label': 'amount_currency',
            'figure_type': 'monetary',
            'class': 'number',
        })

    return columns


def extract_line_id_value(report, line_dict_id, model_name):
    """يستخرج معرّف السجل الخاص بـ ``model_name`` من معرّف سطر التقرير.

    يبحث بالاسم لا بموضع ثابت، لأن Enterprise قد يضيف مستويات تجميع بين
    الإصدارات. يُرجع ``int`` دائمًا: مفاتيح نتائج SQL أعداد صحيحة، ولو عاد
    المعرّف نصًّا لفشل البحث في القاموس بصمت ولاختفت الميزة كلها دون أي
    استثناء أو سطر في اللوق.
    """
    parsed = report._parse_line_id(line_dict_id)
    if not parsed:
        return None

    for entry in reversed(parsed):
        # كل عنصر بالشكل (markup, model, value)
        if len(entry) >= 3 and entry[1] == model_name:
            try:
                return int(entry[2])
            except (TypeError, ValueError):
                _logger.warning(
                    'qader_steel_suite: تعذّر تحويل معرّف %s إلى رقم: %r',
                    model_name, entry[2],
                )
                return None

    return None


def append_currency_total_lines(
    env, report, options, result, line_dict_id, sums_by_group, groupby_id,
):
    """يضيف صف إجمالي واحدًا لكل عملة إلى نتيجة توسيع سطر.

    ``sums_by_group`` بالشكل ``{column_group_key: {groupby_id: {cur: amt}}}``.
    يُبنى صف واحد لكل عملة، وتُملأ خانته في كل مجموعة أعمدة من سلّتها.
    """
    # كل العملات التي ظهرت لهذا الشريك/الحساب في أي مجموعة أعمدة.
    currency_ids = set()
    for group_data in sums_by_group.values():
        currency_ids |= set(group_data.get(groupby_id, {}))

    if not currency_ids:
        return

    existing = result.get('lines') or []
    # نرث مستوى آخر سطر فعلي بدل تخمين رقم ثابت، حتى يظهر صف الإجمالي
    # كابن للسطر المفتوح لا كقسم شقيق.
    level = existing[-1].get('level', 3) if existing else 3

    for currency in sort_currencies(env, currency_ids):
        amounts = [
            group_data.get(groupby_id, {}).get(currency.id, 0.0)
            for group_data in sums_by_group.values()
        ]
        # صفر حقيقي في كل المجموعات لا يستحق صفًا. نستخدم is_zero بدل
        # ``not amount`` حتى لا يُعرض بقايا تقريب مثل 1e-13 كصف "0.00".
        if all(currency.is_zero(a) for a in amounts):
            continue

        result.setdefault('lines', []).append({
            'id': report._get_generic_line_id(
                None, None,
                parent_line_id=line_dict_id,
                markup='currency_total_%s' % currency.id,
            ),
            'parent_id': line_dict_id,
            'name': env._('%(currency)s Total', currency=currency.name),
            'level': level,
            'columns': build_currency_total_columns(
                env, options, currency, sums_by_group, groupby_id,
            ),
            'class': 'o_account_report_total custom-currency-total',
        })