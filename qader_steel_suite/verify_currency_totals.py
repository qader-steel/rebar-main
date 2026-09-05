# -*- coding: utf-8 -*-
"""تحقّق: هل ظهرت صفوف إجمالي العملات فعلًا بعد الترقية؟

    odoo-bin shell --shell-interface=python < verify_currency_totals.py

قراءة فقط. يفحص دفتر الأستاذ العام ودفتر الشركاء وكشف حساب العميل.
"""

import traceback

SEP = "=" * 78


def check(xmlid, label, model_name):
    print("\n" + SEP)
    print(f"{label}")
    print(SEP)

    rep = env.ref(xmlid, raise_if_not_found=False)
    if not rep:
        print(f"  ⏭ التقرير {xmlid} غير موجود — تخطٍّ.")
        return

    report = env['account.report'].browse(rep.id)
    opts = report.get_options({'unfold_all': True})
    real = env['account.report'].browse(opts['report_id'])

    labels = [c.get('expression_label') for c in opts.get('columns', [])]
    if 'amount_currency' not in labels:
        print("  ⛔ عمود amount_currency غير موجود!")
        print("     فعّل \"العملات المتعددة\": الإعدادات ▸ المحاسبة.")
        return
    ac = labels.index('amount_currency')

    lines = real._get_lines(opts)
    totals = [l for l in lines if 'qss-currency-total' in (l.get('class') or '')]

    print(f"  السطور: {len(lines)}   صفوف الإجمالي المُضافة: {len(totals)}")

    if totals:
        print("\n  ✅ صفوف الإجمالي:")
        for t in totals:
            cols = t.get('columns') or []
            cell = cols[ac] if ac < len(cols) else {}
            print(f"     {t.get('name'):<14} = {cell.get('name') or cell.get('no_format')!r}"
                  f"   (level={t.get('level')})")
    else:
        print("  ⛔ لم يظهر أي صف إجمالي.")

    # كم سطر بند قيد صارت خانته معبّأة؟
    filled = blank = 0
    for l in lines:
        cols = l.get('columns') or []
        if ac < len(cols) and cols[ac]:
            if cols[ac].get('no_format') is not None:
                filled += 1
            else:
                blank += 1
    print(f"\n  خانات العملة: معبّأة={filled}  فارغة={blank}")
    print(f"  عملة الشركة: {env.company.currency_id.name}")
    print("  ← قبل الإصلاح كانت كل سطور عملة الشركة فارغة.")


print("\n" + SEP)
print("QSS — التحقق من إجماليات العملات")
print(SEP)

for args in (
    ('account_reports.general_ledger_report', 'دفتر الأستاذ العام', 'account.account'),
    ('account_reports.partner_ledger_report', 'دفتر الشركاء', 'res.partner'),
    ('account_reports.customer_statement_report', 'كشف حساب العميل', 'res.partner'),
):
    try:
        check(*args)
    except Exception:
        print("!! فشل:")
        traceback.print_exc()

print("\n" + SEP + "\n")
env.cr.rollback()
