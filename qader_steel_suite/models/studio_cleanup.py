# -*- coding: utf-8 -*-
"""إزالة حقول Studio المتبقّية التي تكرّر عناوين حقول الموديول.

المشكلة
-------
عند كل بناء للسجل يطلق أودو::

    Two fields (x_studio_related_field_80b_1k18m1n0l, x_studio_total_payable)
    of purchase.requisition() have the same label: Total Payable.
    [Modules: None and qader_steel_suite]

"Modules: None" تعني أن الحقل الأول من صنع Odoo Studio لا من موديول. هو نسخة
قديمة مكرّرة أنشأها المنفّذ الأول قبل وجود هذا الموديول، وبقيت في قاعدة
البيانات بعد أن أعاد الموديول تعريف الحقل باسم واضح.

لماذا هذا الملف موجود بدل ميغريشن واحدة
---------------------------------------
سكربتات ``migrations/`` لا تعمل إلا في حالة واحدة: **ترقية** موديول مثبَّت
مسبقًا، وبشرط أن يكون رقم مجلد الميغريشن **أكبر تمامًا** من النسخة المثبَّتة
(odoo/modules/migration.py: ``installed < folder_version <= current``).

فترتّب على ذلك ثغرتان أوقعتا التحذير مرة أخرى:

  1. **التثبيت النظيف** - أودو لا يشغّل أي ميغريشن عند التثبيت الأول إطلاقًا.
     وهذا هو حال قاعدة الإنتاج التي لم يُثبَّت فيها الموديول بعد.
  2. **الترقية من 1.9.0 إلى 2.0.0** - مجلد ``19.0.1.9.0`` لا يُختار لأن
     1.9.0 ليست أكبر من 1.9.0.

لذلك يُستدعى التنظيف الآن من مكانين يغطّيان كل الحالات:

  * ``pre_init_hook`` عند التثبيت - ويعمل **قبل** انعكاس الحقول في السجل،
    فلا يظهر التحذير ولو مرة واحدة.
  * ``migrations/0.0.0/post-migration.py`` عند الترقية - والرقم 0.0.0 له
    معنى خاص في أودو: يعمل مع **أي** ترقية مهما كان رقم النسخة
    (migration.py: ``if version == "0.0.0" and installed < current``).

الدالة آمنة للتكرار: تشتغل عشر مرات ولا تفعل شيئًا بعد المرة الأولى.
"""

import logging

_logger = logging.getLogger(__name__)

# (الموديل، العنوان المكرَّر، اسم حقل الموديول الذي يجب ألا يُمسّ)
TARGETS = [
    ('purchase.requisition', 'Total Payable', 'x_studio_total_payable'),
]


def _strip_from_views(env, model, field_name):
    """أزل عقدة <field name="..."/> من أي واجهة تشير إليها."""
    try:
        from lxml import etree
    except ImportError:  # pragma: no cover
        return
    for view in env['ir.ui.view'].search([('model', '=', model)]):
        try:
            arch = view.arch_db or ''
            if field_name not in arch:
                continue
            tree = etree.fromstring(arch.encode('utf-8'))
            nodes = tree.xpath("//field[@name='%s']" % field_name)
            if not nodes:
                continue
            for node in nodes:
                parent = node.getparent()
                if parent is not None:
                    parent.remove(node)
            view.arch_db = etree.tostring(tree, encoding='unicode')
            _logger.warning(
                "QSS [studio_cleanup] أُزيل %s من الواجهة id=%s name=%r.",
                field_name, view.id, view.name,
            )
        except Exception as exc:  # noqa: BLE001
            _logger.warning(
                "QSS [studio_cleanup] تعذّر تنظيف الواجهة id=%s: %s", view.id, exc
            )


def clean_duplicate_studio_labels(env, stage='unknown'):
    """احذف حقول Studio المكرّرة، أو أعد تسميتها إن تعذّر الحذف.

    لا ترفع استثناءً أبدًا: التنظيف يجب ألا يُفشل تثبيتًا ولا ترقية.
    """
    try:
        for model, label, keep in TARGETS:
            leftovers = env['ir.model.fields'].search([
                ('model', '=', model),
                ('state', '=', 'manual'),        # manual = من صنع Studio
                ('field_description', '=', label),
                ('name', '!=', keep),
            ])
            if not leftovers:
                _logger.info(
                    "QSS [studio_cleanup/%s] لا يوجد حقل استديو متبقٍّ بعنوان "
                    "%r على %s.", stage, label, model,
                )
                continue

            for field in leftovers:
                name = field.name
                _strip_from_views(env, model, name)
                try:
                    field.with_context(studio=True, _force_unlink=True).unlink()
                    _logger.warning(
                        "QSS [studio_cleanup/%s] ✅ حُذف حقل الاستديو المتبقّي "
                        "%s على %s.", stage, name, model,
                    )
                except Exception as exc:  # noqa: BLE001
                    _logger.warning(
                        "QSS [studio_cleanup/%s] ⚠ تعذّر حذف %s (%s) — "
                        "سيُعاد تسميته فقط ليزول تعارض العناوين.",
                        stage, name, exc,
                    )
                    try:
                        field.field_description = (
                            "OLD Studio field - احذفني (استُبدل بـ %s)" % label
                        )
                    except Exception as exc2:  # noqa: BLE001
                        _logger.warning(
                            "QSS [studio_cleanup/%s] تعذّر حتى إعادة تسمية "
                            "%s: %s", stage, name, exc2,
                        )
    except Exception as exc:  # noqa: BLE001
        _logger.exception(
            "QSS [studio_cleanup/%s] فشل التنظيف التلقائي (العملية تكمل "
            "بشكل طبيعي): %s", stage, exc,
        )
