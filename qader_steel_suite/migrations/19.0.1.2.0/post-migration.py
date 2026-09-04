# -*- coding: utf-8 -*-
"""تنظيف حقل الاستديو المتبقّي "x_studio_total_net_weight".

الخلفية
-------
في نسخة سابقة كان حقل "إجمالي الوزن الصافي" يحمل الاسم التقني
``x_studio_total_net_weight``. تبيّن أن هذا الاسم يتعارض مع حقل أنشأه
Odoo Studio مسبقًا في قاعدة البيانات (نسخة مكرّرة من "Net weight"،
ولذلك يظهر عنوانه في الواجهة كـ "Net weight (Copy)"). عنوان الحقل
مخزَّن في ``ir_model_fields.field_description`` وهو ما يظهر للمستخدم،
فيتجاوز قيمة ``string=`` المكتوبة في بايثون.

الحل في الموديول: أُعيدت تسمية الحقل إلى ``mq_total_net_weight``
(بادئة الموديول نفسه) ليستحيل التعارض. لكن حقل الاستديو القديم يبقى
موجودًا في قاعدة البيانات وقد يبقى معروضًا داخل واجهة عدّلها Studio -
وهذا ما يجعل المستخدم يرى "Net weight (Copy)" رغم الترقية.

هذا السكربت يزيل البقايا تلقائيًا:
  1. يسجّل في اللوق كل حقول ``sale.order`` التي يحوي عنوانها "(Copy)"
     (تشخيص - أرسل هذه الأسطر إن بقيت المشكلة).
  2. يحذف عقدة ``<field name="x_studio_total_net_weight"/>`` من أي
     ``ir.ui.view`` لا يزال يشير إليها (بما فيها واجهات Studio).
  3. يحذف حقل الاستديو نفسه. وإن تعذّر الحذف لأي سبب، يكتفي بتغيير
     عنوانه إلى نص واضح حتى لا يُخلط مع الحقل الصحيح.

السكربت مصمَّم ليكون آمنًا تمامًا: أي خطأ داخله يُسجَّل فقط ولا يُفشل
الترقية.
"""

import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)

OLD_FIELD = "x_studio_total_net_weight"
MODEL = "sale.order"


def _log_copy_labelled_fields(cr):
    """تشخيص: اطبع كل حقول sale.order التي عنوانها يحوي "(Copy)"."""
    cr.execute(
        """
        SELECT f.name, f.field_description::text, f.state
          FROM ir_model_fields f
          JOIN ir_model m ON m.id = f.model_id
         WHERE m.model = %s
           AND (f.name = %s OR f.field_description::text ILIKE %s)
        """,
        (MODEL, OLD_FIELD, "%(Copy)%"),
    )
    rows = cr.fetchall()
    if not rows:
        _logger.info(
            "QSS [migration 1.2.0] لا يوجد أي حقل متبقٍّ باسم %s ولا أي حقل "
            "عنوانه يحوي '(Copy)' على %s — لا شيء للتنظيف.",
            OLD_FIELD, MODEL,
        )
    for name, description, state in rows:
        _logger.warning(
            "QSS [migration 1.2.0] حقل مرشَّح للتنظيف على %s: "
            "name=%r label=%r state=%r",
            MODEL, name, description, state,
        )


def _strip_field_from_views(env):
    """أزل <field name="x_studio_total_net_weight"/> من أي واجهة تشير إليه."""
    try:
        from lxml import etree
    except ImportError:  # pragma: no cover - lxml موجود دائمًا مع Odoo
        _logger.warning("QSS [migration 1.2.0] lxml غير متاح — تخطّي تنظيف الواجهات.")
        return

    views = env["ir.ui.view"].search([("model", "=", MODEL)])
    for view in views:
        try:
            arch = view.arch_db or ""
            if OLD_FIELD not in arch:
                continue
            tree = etree.fromstring(arch.encode("utf-8"))
            nodes = tree.xpath("//field[@name='%s']" % OLD_FIELD)
            if not nodes:
                continue
            for node in nodes:
                parent = node.getparent()
                if parent is not None:
                    parent.remove(node)
            view.arch_db = etree.tostring(tree, encoding="unicode")
            _logger.warning(
                "QSS [migration 1.2.0] أُزيل %s من الواجهة id=%s name=%r "
                "(عدد العقد=%s).",
                OLD_FIELD, view.id, view.name, len(nodes),
            )
        except Exception as exc:  # noqa: BLE001 - التنظيف يجب ألا يُفشل الترقية
            _logger.warning(
                "QSS [migration 1.2.0] تعذّر تنظيف الواجهة id=%s: %s", view.id, exc
            )


def _drop_leftover_field(env):
    """احذف حقل الاستديو المتبقّي، أو أعد تسميته إن تعذّر الحذف."""
    leftover = env["ir.model.fields"].search(
        [("model", "=", MODEL), ("name", "=", OLD_FIELD)]
    )
    if not leftover:
        return

    for field in leftover:
        label = field.field_description
        try:
            field.with_context(studio=True, _force_unlink=True).unlink()
            _logger.warning(
                "QSS [migration 1.2.0] ✅ حُذف حقل الاستديو المتبقّي %s "
                "(كان عنوانه %r).",
                OLD_FIELD, label,
            )
        except Exception as exc:  # noqa: BLE001
            _logger.warning(
                "QSS [migration 1.2.0] ⚠ تعذّر حذف %s تلقائيًا (%s) — "
                "سيُعاد تسميته فقط. احذفه يدويًا من Studio أو من "
                "Settings ▸ Technical ▸ Fields.",
                OLD_FIELD, exc,
            )
            try:
                field.field_description = (
                    "OLD Studio field - احذفني (استُبدل بـ Total Net Weight)"
                )
            except Exception as exc2:  # noqa: BLE001
                _logger.warning(
                    "QSS [migration 1.2.0] تعذّر حتى إعادة تسمية %s: %s",
                    OLD_FIELD, exc2,
                )


def migrate(cr, version):
    if not version:
        return
    try:
        env = api.Environment(cr, SUPERUSER_ID, {})
        _log_copy_labelled_fields(cr)
        _strip_field_from_views(env)
        _drop_leftover_field(env)
        _logger.info("QSS [migration 1.2.0] ■ انتهى تنظيف حقل %s.", OLD_FIELD)
    except Exception as exc:  # noqa: BLE001 - لا يجوز أن تفشل الترقية بسبب التنظيف
        _logger.exception(
            "QSS [migration 1.2.0] فشل التنظيف التلقائي (الترقية تكمل بشكل "
            "طبيعي): %s", exc,
        )
