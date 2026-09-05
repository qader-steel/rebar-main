# -*- coding: utf-8 -*-
"""تشخيص شامل: لماذا لا تظهر إجماليات العملات في دفتر الأستاذ العام؟

طريقة التشغيل
-------------
    odoo-bin shell -d <DATABASE> --shell-interface=python < diagnose_general_ledger.py

(أو على odoo.sh:  odoo-bin shell --shell-interface=python < diagnose_general_ledger.py)

السكربت **للقراءة فقط** — لا يكتب أي شيء، وينهي بـ rollback.
انسخ كامل المخرجات وأرسلها كما هي.
"""

import inspect
import traceback

SEP = "=" * 78


def hdr(n, title):
    print("\n" + SEP)
    print(f"[{n}] {title}")
    print(SEP)


def safe(fn):
    """يشغّل قسمًا ويطبع الخطأ بدل أن يوقف السكربت كله."""
    try:
        fn()
    except Exception:
        print("!! فشل هذا القسم:")
        traceback.print_exc()


print("\n" + SEP)
print("QSS — تشخيص دفتر الأستاذ العام / إجماليات العملات")
print(SEP)


# ======================================================================
def s1_module():
    hdr(1, "حالة الموديول (هل الكود الجديد محمّل أصلًا؟)")
    mods = env['ir.module.module'].search([
        ('name', 'in', ('qader_steel_suite', 'account_reports', 'account')),
    ])
    for m in mods:
        print(f"  {m.name:<22} state={m.state:<12} installed={m.installed_version}  latest={m.latest_version}")
    qss = mods.filtered(lambda x: x.name == 'qader_steel_suite')
    if qss and qss.installed_version and '1.3' not in (qss.installed_version or ''):
        print("  ⛔ النسخة المثبّتة ليست 19.0.1.3.x — الترقية لم تُنفَّذ! نفّذ:")
        print("     odoo-bin -d <db> -u qader_steel_suite --stop-after-init")


# ======================================================================
def s2_handler():
    hdr(2, "معالج دفتر الأستاذ العام و MRO (هل كودي داخل سلسلة الوراثة؟)")
    name = 'account.general.ledger.report.handler'
    if name not in env:
        print(f"  ⛔ النموذج {name} غير موجود إطلاقًا في هذه النسخة!")
        return
    handler = env[name]
    print(f"  النموذج موجود: {name}")
    print("  MRO:")
    found = False
    for k in type(handler).__mro__:
        mark = ""
        mod = getattr(k, '__module__', '') or ''
        if 'qader_steel_suite' in mod:
            mark = "   <<<<<< كودنا"
            found = True
        print(f"    - {k.__name__:<42} [{mod}]{mark}")
    print()
    if found:
        print("  ✅ امتدادنا موجود في MRO.")
    else:
        print("  ⛔ امتدادنا **غير موجود** في MRO — الملف لم يُحمَّل أو الموديول لم يُرقَّ.")


# ======================================================================
def s3_methods():
    hdr(3, "أسماء الميثودات الحقيقية على المعالج (الأهم!)")
    name = 'account.general.ledger.report.handler'
    if name not in env:
        return
    handler = env[name]

    print("  الميثودات المرشّحة الموجودة فعلًا:")
    for cand in ('_get_aml_line', '_get_report_line_move_line',
                 '_report_expand_unfoldable_line_general_ledger',
                 '_get_account_title_line', '_dynamic_lines_generator',
                 '_custom_options_initializer'):
        exists = hasattr(handler, cand)
        flag = "✅" if exists else "❌"
        sig = ""
        if exists:
            try:
                sig = str(inspect.signature(getattr(handler, cand)))
            except Exception:
                sig = "(تعذّر قراءة التوقيع)"
            owner = ""
            for k in type(handler).__mro__:
                if cand in k.__dict__:
                    owner = f"  [أول تعريف في: {k.__name__} / {getattr(k, '__module__', '')}]"
                    break
        else:
            owner = ""
        print(f"    {flag} {cand}{sig}{owner}")

    print("\n  كل ميثودات المعالج التي تبني سطورًا (للبحث عن أي اسم لم نتوقّعه):")
    for m in sorted(d for d in dir(handler)
                    if d.startswith('_') and (
                        'line' in d or 'aml' in d or 'expand' in d)):
        print(f"    - {m}")


# ======================================================================
def s4_reports():
    hdr(4, "تقارير دفتر الأستاذ العام ونسخها المحلّية (variants)")
    root = env.ref('account_reports.general_ledger_report', raise_if_not_found=False)
    if not root:
        print("  ⛔ لم يُعثر على account_reports.general_ledger_report")
        return
    print(f"  الأصل: id={root.id}  name={root.name!r}  handler={root.custom_handler_model_name!r}")

    variants = env['account.report'].with_context(active_test=False).search([
        ('root_report_id', '=', root.id),
    ])
    if variants:
        print(f"\n  ⚠ توجد {len(variants)} نسخة محلّية (variant) — مهم جدًا:")
        for v in variants:
            print(f"    - id={v.id}  name={v.name!r}  active={v.active}  "
                  f"country={v.country_id.code or '-'}  handler={v.custom_handler_model_name!r}")
        print("    ← إن كان التقرير المعروض عندك إحدى هذه النسخ، فإن أي شرط")
        print("      يطابق معرّف الأصل بشكل صارم سيمنع ظهور الإجماليات.")
    else:
        print("\n  لا توجد نسخ محلّية — التقرير المعروض هو الأصل.")

    others = env['account.report'].with_context(active_test=False).search([
        ('custom_handler_model_name', '=', 'account.general.ledger.report.handler'),
    ])
    print(f"\n  كل التقارير التي تستخدم معالج دفتر الأستاذ ({len(others)}):")
    for o in others:
        print(f"    - id={o.id}  name={o.name!r}  root={o.root_report_id.id or '-'}")


# ======================================================================
def s5_currency_group():
    hdr(5, "مجموعة العملات المتعددة (السبب الأشهر لاختفاء العمود)")
    grp = env.ref('base.group_multi_currency', raise_if_not_found=False)
    if not grp:
        print("  ⛔ المجموعة base.group_multi_currency غير موجودة")
        return
    me = env.user
    print(f"  المستخدم الحالي: {me.name} (id={me.id}, login={me.login})")
    print(f"  ضمن مجموعة العملات المتعددة؟  {'✅ نعم' if me.has_group('base.group_multi_currency') else '⛔ لا'}")
    print(f"  عدد المستخدمين في المجموعة: {len(grp.users)}")
    actives = env['res.currency'].search([('active', '=', True)])
    print(f"  العملات المفعّلة ({len(actives)}): {', '.join(actives.mapped('name'))}")
    print(f"  عملة الشركة {env.company.name}: {env.company.currency_id.name}")
    if not me.has_group('base.group_multi_currency'):
        print("\n  ⛔ هذا وحده يكفي لإخفاء عمود Amount Currency والإجماليات معه.")
        print("     الحل: الإعدادات ▸ المحاسبة ▸ فعّل \"العملات المتعددة\".")


# ======================================================================
def s6_columns():
    hdr(6, "أعمدة التقرير بعد get_options (هل عمود amount_currency موجود؟)")
    root = env.ref('account_reports.general_ledger_report', raise_if_not_found=False)
    if not root:
        return
    print("  أعمدة التعريف (account.report.column):")
    for c in root.column_ids:
        print(f"    - {c.expression_label:<20} name={c.name!r}  figure_type={c.figure_type}")

    opts = root.get_options({'unfold_all': True})
    print(f"\n  report_id بعد get_options = {opts.get('report_id')}  "
          f"(الأصل id={root.id})")
    if opts.get('report_id') != root.id:
        print("    ⚠ التقرير أُعيد توجيهه إلى نسخة محلّية! هذا هو المعرّف الذي يصل الكود.")
    print(f"  multi_currency = {opts.get('multi_currency')}")
    print(f"  عدد مجموعات الأعمدة = {len(opts.get('column_groups', {}))}")
    labels = [c.get('expression_label') for c in opts.get('columns', [])]
    print(f"  أعمدة options: {labels}")
    if 'amount_currency' in labels:
        print("  ✅ عمود amount_currency موجود.")
    else:
        print("  ⛔ عمود amount_currency **محذوف** — لا مكان لعرض المبالغ ولا الإجماليات.")


# ======================================================================
def s7_run():
    hdr(7, "تشغيل التقرير فعليًا وفتح حساب (الاختبار الحاسم)")
    root = env.ref('account_reports.general_ledger_report', raise_if_not_found=False)
    if not root:
        return
    report = env['account.report'].browse(root.id)
    opts = report.get_options({'unfold_all': True})
    real = env['account.report'].browse(opts['report_id'])
    print(f"  التقرير المُشغَّل: id={real.id} name={real.name!r}")

    lines = real._get_lines(opts)
    print(f"  إجمالي السطور المُولَّدة: {len(lines)}")

    total_rows = [l for l in lines if 'custom-currency-total' in (l.get('class') or '')]
    print(f"  صفوف إجمالي العملات التي أضفناها: {len(total_rows)}")
    for t in total_rows[:10]:
        vals = [c.get('no_format') for c in t.get('columns', []) if c.get('no_format') is not None]
        print(f"    ✅ {t.get('name')!r} level={t.get('level')} قيم={vals}")

    if not total_rows:
        print("    ⛔ لم يظهر أي صف إجمالي.")

    # أول حساب قابل للفتح
    acc_lines = [l for l in lines if l.get('expand_function') ==
                 '_report_expand_unfoldable_line_general_ledger']
    print(f"\n  حسابات قابلة للفتح: {len(acc_lines)}")
    if acc_lines:
        first = acc_lines[0]
        print(f"  نفتح: {first.get('name')!r}  id={first['id']!r}")
        handler = env[real.custom_handler_model_name]
        res = handler._report_expand_unfoldable_line_general_ledger(
            first['id'], None, opts,
            {k: 0 for k in opts['column_groups']}, 0,
        )
        sub = res.get('lines', [])
        print(f"  سطور ناتجة عن الفتح: {len(sub)}  has_more={res.get('has_more')}")
        for l in sub:
            cls = l.get('class') or ''
            mark = "  <<< إجمالي عملة" if 'custom-currency-total' in cls else ""
            amt = [c.get('no_format') for c in l.get('columns', []) if c.get('no_format') is not None]
            print(f"    - {str(l.get('name'))[:44]:<44} level={l.get('level')} {amt}{mark}")


# ======================================================================
def s8_sums():
    hdr(8, "استعلام مجاميع العملات مباشرةً (هل الأرقام موجودة أصلًا؟)")
    root = env.ref('account_reports.general_ledger_report', raise_if_not_found=False)
    if not root:
        return
    report = env['account.report'].browse(root.id)
    opts = report.get_options({'unfold_all': True})
    real = env['account.report'].browse(opts['report_id'])
    try:
        from odoo.addons.qader_steel_suite.models import account_report_currency_utils as u
    except Exception:
        print("  ⛔ تعذّر استيراد account_report_currency_utils — الموديول غير محمّل.")
        traceback.print_exc()
        return

    sums = u.compute_currency_sums(real, opts, u.SQL('account_move_line.account_id'))
    print(f"  مجموعات أعمدة في النتيجة: {list(sums.keys())}")
    n = 0
    for gk, by_acc in sums.items():
        for acc_id, cur_map in list(by_acc.items())[:8]:
            acc = env['account.account'].browse(acc_id)
            pretty = {env['res.currency'].browse(c).name: round(v, 2)
                      for c, v in cur_map.items()}
            print(f"    [{gk[:18]}] {acc.code} {acc.name[:28]:<28} → {pretty}")
            n += 1
    if not n:
        print("    ⛔ لا توجد أي مجاميع — لا حركات في الفترة، أو الاستعلام يرجع فارغًا.")

    # كم سطر قيد فيه عملة أجنبية أصلًا؟
    env.cr.execute("""
        SELECT c.name, COUNT(*), SUM(aml.amount_currency), SUM(aml.balance)
          FROM account_move_line aml
          JOIN res_currency c ON c.id = aml.currency_id
          JOIN account_move m ON m.id = aml.move_id
         WHERE m.state = 'posted'
         GROUP BY c.name ORDER BY 2 DESC
    """)
    print("\n  توزيع بنود القيود المرحّلة حسب العملة (من قاعدة البيانات):")
    for name, cnt, amt_cur, bal in env.cr.fetchall():
        print(f"    {name}: {cnt} سطر | SUM(amount_currency)={amt_cur} | SUM(balance)={bal}")
    print("    ← لاحظ: عملة الشركة يكون SUM(amount_currency) فيها صفرًا — هذا هو أصل المشكلة.")


# ======================================================================
def s9_api():
    hdr(9, "توفّر الدوال المساعدة التي يعتمد عليها الكود")
    rep = env['account.report']
    for m in ('_build_column_dict', '_get_res_id_from_line_id',
              '_get_generic_line_id', '_parse_line_id',
              '_split_options_per_column_group', '_get_report_query',
              '_currency_table_aml_join', '_currency_table_apply_rate'):
        ok = hasattr(rep, m)
        sig = ''
        if ok:
            try:
                sig = str(inspect.signature(getattr(rep, m)))
            except Exception:
                sig = ''
        print(f"    {'✅' if ok else '⛔'} account.report.{m}{sig}")


for fn in (s1_module, s2_handler, s3_methods, s4_reports, s5_currency_group,
           s6_columns, s7_run, s8_sums, s9_api):
    safe(fn)

print("\n" + SEP)
print("انتهى التشخيص — انسخ كل ما سبق وأرسله.")
print(SEP + "\n")

env.cr.rollback()
