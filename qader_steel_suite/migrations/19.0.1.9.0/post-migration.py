# -*- coding: utf-8 -*-
"""إزالة حقل الاستديو المتبقّي الذي يكرّر عنوان "Total Payable".

الخلفية
-------
عند كل بناء للسجل كان أودو يطلق:

    Two fields (x_studio_related_field_80b_1k18m1n0l, x_studio_total_payable)
    of purchase.requisition() have the same label: Total Payable.
    [Modules: None and qader_steel_suite]

"Modules: None" تعني أن الحقل الأول من صنع Odoo Studio لا من أي موديول.
هو نسخة قديمة مكرّرة من الحقل نفسه، أنشأها المنفّذ الأول عبر Studio قبل
وجود هذا الموديول، وبقيت في قاعدة البيانات بعد أن أعاد الموديول تعريف
الحقل باسم واضح (x_studio_total_payable).

هذا السكربت يزيلها تلقائيًا بنفس أسلوب ميغريشن 1.2.0:
  1. يحذف عقدة <field> من أي واجهة لا تزال تشير إليها (واجهات Studio).
  2. يحذف الحقل نفسه.
  3. إن تعذّر الحذف لأي سبب، يكتفي بتغيير **عنوان الحقل القديم** (لا
     عنوان حقلنا) إلى نص واضح - فيزول تعارض العناوين ويختفي التحذير
     على كل حال.

أي خطأ داخله يُسجَّل فقط ولا يُفشل الترقية.
"""

import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)

MODEL = "purchase.requisition"
LABEL = "Total Payable"
KEEP = "x_studio_total_payable"          # حقل الموديول - لا يُمسّ إطلاقًا


def _leftovers(env):
    """حقول Studio على purchase.requisition تحمل نفس العنوان."""
    return env["ir.model.fields"].search([
        ("model", "=", MODEL),
        ("state", "=", "manual"),          # manual = من صنع Studio
        ("field_description", "=", LABEL),
        ("name", "!=", KEEP),
    ])


def _strip_from_views(env, field_name):
    try:
        from lxml import etree
    except ImportError:  # pragma: no cover
        return
    for view in env["ir.ui.view"].search([("model", "=", MODEL)]):
        try:
            arch = view.arch_db or ""
            if field_name not in arch:
                continue
            tree = etree.fromstring(arch.encode("utf-8"))
            nodes = tree.xpath("//field[@name='%s']" % field_name)
            if not nodes:
                continue
            for node in nodes:
                parent = node.getparent()
                if parent is not None:
                    parent.remove(node)
            view.arch_db = etree.tostring(tree, encoding="unicode")
            _logger.warning(
                "QSS [migration 1.9.0] أُزيل %s من الواجهة id=%s name=%r.",
                field_name, view.id, view.name,
            )
        except Exception as exc:  # noqa: BLE001
            _logger.warning(
                "QSS [migration 1.9.0] تعذّر تنظيف الواجهة id=%s: %s", view.id, exc
            )


def migrate(cr, version):
    if not version:
        return
    try:
        env = api.Environment(cr, SUPERUSER_ID, {})
        leftovers = _leftovers(env)
        if not leftovers:
            _logger.info(
                "QSS [migration 1.9.0] لا يوجد حقل استديو متبقٍّ بعنوان %r "
                "على %s — لا شيء للتنظيف.", LABEL, MODEL,
            )
            return
        for field in leftovers:
            name = field.name
            _strip_from_views(env, name)
            try:
                field.with_context(studio=True, _force_unlink=True).unlink()
                _logger.warning(
                    "QSS [migration 1.9.0] ✅ حُذف حقل الاستديو المتبقّي %s.", name,
                )
            except Exception as exc:  # noqa: BLE001
                _logger.warning(
                    "QSS [migration 1.9.0] ⚠ تعذّر حذف %s (%s) — سيُعاد "
                    "تسميته فقط ليزول تعارض العناوين.", name, exc,
                )
                try:
                    field.field_description = (
                        "OLD Studio field - احذفني (استُبدل بـ Total Payable)"
                    )
                except Exception as exc2:  # noqa: BLE001
                    _logger.warning(
                        "QSS [migration 1.9.0] تعذّر حتى إعادة تسمية %s: %s",
                        name, exc2,
                    )
    except Exception as exc:  # noqa: BLE001
        _logger.exception(
            "QSS [migration 1.9.0] فشل التنظيف التلقائي (الترقية تكمل "
            "بشكل طبيعي): %s", exc,
        )
