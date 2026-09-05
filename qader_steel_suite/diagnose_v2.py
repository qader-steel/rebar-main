# -*- coding: utf-8 -*-
"""تشخيص المرحلة الثانية — بنية دفتر الأستاذ العام في أودو 19.

أثبت التشخيص الأول أن أودو 19 أعاد بناء التقرير: لا سطر يستخدم
``_report_expand_unfoldable_line_general_ledger`` و ``_get_account_title_line``
اختفت. هذا السكربت يستخرج البنية الحقيقية ليُبنى الحقن في المكان الصحيح.

التشغيل:
    odoo-bin shell --shell-interface=python < diagnose_v2.py

يكتب ملفين في /tmp ويطبع ملخّصًا. أرسل الملفين + المخرجات.
"""

import inspect
import traceback

SEP = "=" * 78
OUT_GL = "/tmp/odoo19_general_ledger_source.py"
OUT_PL = "/tmp/odoo19_partner_ledger_source.py"


def hdr(n, t):
    print("\n" + SEP)
    print(f"[{n}] {t}")
    print(SEP)


def safe(fn):
    try:
        fn()
    except Exception:
        print("!! فشل هذا القسم:")
        traceback.print_exc()


print("\n" + SEP)
print("QSS — تشخيص 2: بنية دفتر الأستاذ العام في أودو 19")
print(SEP)


# ======================================================================
def a_owners():
    hdr("A", "من يعرّف كل ميثود؟ (كل الطبقات وليس الأولى فقط) — حاسم")
    h = env['account.general.ledger.report.handler']
    cands = [
        '_get_aml_line',
        '_report_expand_unfoldable_line_general_ledger',
        '_get_account_title_line',
        '_dynamic_lines_generator',
        '_custom_line_postprocessor',
        '_custom_groupby_line_completer',
        '_custom_unfold_all_batch_data_generator',
        '_custom_options_initializer',
        '_get_custom_groupby_map',
        '_report_custom_engine_general_ledger',
    ]
    for c in cands:
        owners = []
        for k in type(h).__mro__:
            if c in k.__dict__:
                owners.append(f"{k.__name__}[{(getattr(k,'__module__','') or '').split('.')[-1]}]")
        if not owners:
            print(f"  ❌ {c}: غير معرّف في أي طبقة")
        else:
            odoo_owns = any('qader_steel_suite' not in o for o in owners)
            mark = "" if odoo_owns else "   ⛔ نحن فقط من يعرّفها — أودو لا يعرفها!"
            print(f"  ✅ {c}: {' <- '.join(owners)}{mark}")


# ======================================================================
def b_report_lines():
    hdr("B", "تعريف التقرير: account.report.line + التعابير")
    r = env.ref('account_reports.general_ledger_report')
    print(f"  التقرير id={r.id} name={r.name!r}")
    print(f"  custom_handler={r.custom_handler_model_name!r}")
    for f in ('filter_hierarchy', 'load_more_limit', 'search_bar',
              'prefix_groups_threshold', 'filter_unfold_all'):
        if f in r._fields:
            print(f"  {f} = {r[f]!r}")

    print(f"\n  عدد سطور التقرير: {len(r.line_ids)}")
    for ln in r.line_ids:
        print(f"\n  ── سطر: {ln.name!r} (id={ln.id}, code={ln.code!r})")
        for f in ('groupby', 'user_groupby', 'foldable', 'hierarchy_level', 'sequence'):
            if f in ln._fields:
                print(f"       {f} = {ln[f]!r}")
        for e in ln.expression_ids:
            print(f"       • {e.label:<18} engine={e.engine:<14} "
                  f"date_scope={e.date_scope:<12} figure={e.figure_type!r}")
            print(f"         formula={e.formula!r}")
            if e.subformula:
                print(f"         subformula={e.subformula!r}")


# ======================================================================
def c_lines():
    hdr("C", "السطور الفعلية: ما هي expand_function و groupby الحقيقية؟")
    r = env['account.report'].browse(env.ref('account_reports.general_ledger_report').id)
    opts = r.get_options({'unfold_all': True})
    real = env['account.report'].browse(opts['report_id'])
    lines = real._get_lines(opts)
    print(f"  عدد السطور: {len(lines)}")

    funcs = {}
    for l in lines:
        funcs[l.get('expand_function')] = funcs.get(l.get('expand_function'), 0) + 1
    print(f"\n  توزيع expand_function: {funcs}")

    ac_idx = next((i for i, c in enumerate(opts['columns'])
                   if c.get('expression_label') == 'amount_currency'), None)
    print(f"  موضع عمود amount_currency = {ac_idx}\n")

    print("  أول 25 سطر:")
    for l in lines[:25]:
        cols = l.get('columns') or []
        ac = cols[ac_idx].get('no_format') if (ac_idx is not None and ac_idx < len(cols)) else '-'
        acn = cols[ac_idx].get('name') if (ac_idx is not None and ac_idx < len(cols)) else '-'
        print(f"   lvl={l.get('level')} unfold={str(l.get('unfoldable'))[:5]:<5} "
              f"gb={str(l.get('groupby'))[:16]:<16} "
              f"fn={str(l.get('expand_function'))[:44]:<44}")
        print(f"      name={str(l.get('name'))[:50]!r}")
        print(f"      id={l['id']!r}")
        print(f"      amount_currency: no_format={ac!r} name={acn!r}")


# ======================================================================
def d_source():
    hdr("D", "استخراج مصدر أودو 19 الحقيقي إلى ملفات")
    import odoo.addons.account_reports.models.account_general_ledger as gl
    import odoo.addons.account_reports.models.account_partner_ledger as pl

    for mod, path, label in ((gl, OUT_GL, 'General Ledger'),
                             (pl, OUT_PL, 'Partner Ledger')):
        try:
            src = inspect.getsource(mod)
            with open(path, 'w') as f:
                f.write(src)
            print(f"  ✅ {label}: {len(src.splitlines())} سطر → {path}")
        except Exception as e:
            print(f"  ⛔ {label}: {e}")

    print(f"\n  ملف المصدر على القرص:")
    print(f"    {inspect.getfile(gl)}")
    print(f"    {inspect.getfile(pl)}")


# ======================================================================
def e_hooks():
    hdr("E", "الخطافات المتاحة للحقن (البديل الصحيح)")
    h = env['account.general.ledger.report.handler']
    for m in ('_custom_line_postprocessor', '_custom_groupby_line_completer'):
        if hasattr(h, m):
            try:
                print(f"  ✅ {m}{inspect.signature(getattr(h, m))}")
                print(inspect.getsource(getattr(h, m)))
            except Exception as e:
                print(f"     (تعذّر: {e})")
        else:
            print(f"  ❌ {m} غير موجودة")


# ======================================================================
def f_currency():
    hdr("F", "العملات (القسم الذي فشل سابقًا)")
    print(f"  عملة الشركة {env.company.name}: {env.company.currency_id.name} "
          f"(id={env.company.currency_id.id})")
    for c in env['res.currency'].search([('active', '=', True)]):
        print(f"    - {c.name} id={c.id} rounding={c.rounding}")
    grp = env.ref('base.group_multi_currency', raise_if_not_found=False)
    if grp:
        # اسم الحقل تغيّر بين الإصدارات
        fld = 'user_ids' if 'user_ids' in grp._fields else ('users' if 'users' in grp._fields else None)
        print(f"  مجموعة العملات المتعددة: حقل المستخدمين = {fld!r}, "
              f"العدد = {len(grp[fld]) if fld else '?'}")


for fn in (a_owners, b_report_lines, c_lines, d_source, e_hooks, f_currency):
    safe(fn)

print("\n" + SEP)
print("انتهى. أرسل المخرجات + الملفين:")
print(f"   {OUT_GL}")
print(f"   {OUT_PL}")
print(SEP + "\n")

env.cr.rollback()
