# -*- coding: utf-8 -*-
"""تنظيف حقول Studio المكرّرة عند **أي** ترقية للموديول.

الرقم 0.0.0 ليس رقم نسخة، بل حالة خاصة في أودو: مجلد الميغريشن المسمّى
``0.0.0`` يُنفَّذ مع أي ترقية طالما أن النسخة المثبَّتة أقدم من نسخة الكود
(odoo/modules/migration.py). فلا نحتاج بعد اليوم إلى تذكّر رفع رقم مجلد
ميغريشن كلما أردنا إعادة تشغيل هذا التنظيف.

المنطق نفسه مُستدعى أيضًا من ``pre_init_hook`` ليغطّي حالة التثبيت النظيف،
التي لا تُشغَّل فيها الميغريشنات إطلاقًا.
"""

from odoo import SUPERUSER_ID, api

from odoo.addons.qader_steel_suite.models.studio_cleanup import (
    clean_duplicate_studio_labels,
)


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    clean_duplicate_studio_labels(env, stage='migration')
