# -*- coding: utf-8 -*-
"""عملة الشراء الافتراضية (طلب إداري - سبتمبر 2026).

الخلفية
-------
طلب المدير حرفيًا: «بس خليها لشراء عراقي، المبيعات… خليها تضل، هو
يختار دينار لو دولار» — أي أن أمر الشراء المتولّد تلقائيًا في دورة
الدروب-شيبنج يجب أن يخرج بالدينار العراقي، بينما تبقى عملة أمر البيع
اختيارًا حرًّا للمستخدم. ومع ذلك «مو دائما إنه هم يشترون بالدولار»،
أي أن الدولار يبقى ممكنًا عند الحاجة — فالمطلوب تصحيح **الافتراضي**
لا فرضُ قفلٍ حديدي.

من أين كانت تأتي عملة الدولار؟ (تحقّق من مصدر أودو 19، لا تخمين)
----------------------------------------------------------------
``purchase_stock/models/stock_rule.py::_prepare_purchase_order`` ::

    'currency_id': currency.id
        or partner.with_company(company_id).property_purchase_currency_id.id
        or company_id.currency_id.id,

حيث ``currency = values['supplier'].currency_id`` أي عملة سطر
``product.supplierinfo``. فالترتيب هو:

    1) product.supplierinfo.currency_id           (قائمة أسعار المورّد)
    2) res.partner.property_purchase_currency_id  ("Supplier Currency")
    3) res.company.currency_id                    (عملة الشركة)

ونفس الحقل رقم (2) هو الافتراضي أيضًا لـ
``purchase.order._compute_currency_id`` و
``purchase.requisition._compute_currency_id`` ولعملة سطر
``supplierinfo`` عند إنشائه — أي أن ضبطًا واحدًا على المورّد كان يجرّ
النظام كلّه إلى الدولار.

ما الذي يفعله هذا الملف
-----------------------
يضيف إعدادًا واحدًا على الشركة: **Default Purchase Currency**
(``mq_purchase_currency_id``)، افتراضه عملة الشركة نفسها (الدينار
العراقي)، ثم يجعل هذا الإعداد هو الافتراضي في المواضع الثلاثة التي
تُحسم فيها عملة الشراء. الحقل ``purchase.order.currency_id`` معرَّف في
أودو أصلًا ``store=True, readonly=False`` — أي أنه قابل للتغيير يدويًا
تمامًا مثل عملة المبيعات، فلا شيء هنا يمنع اختيار الدولار عند الحاجة.

ملاحظة مهمّة عن سعر الصرف
--------------------------
عندما تختلف عملة البيع عن عملة الشراء في نفس اللحظة، يحوّل أودو بينهما
عبر ``res.currency.rate``. إن لم يكن للدولار سطر سعر صرف فإن أودو
يستخدم 1.0 (أي 1 دولار = 1 دينار) وستكون الأرباح وتقييم المخزون خاطئة
بمقدار هائل. لذلك يتحقّق ``_mq_get_purchase_currency`` من وجود سعر صرف
ويكتب تحذيرًا صريحًا في اللوق عند غيابه — ابحث في اللوق عن
``QSS [purchase_currency]``.
"""

import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    _inherit = 'res.company'

    mq_purchase_currency_id = fields.Many2one(
        'res.currency',
        string="Default Purchase Currency",
        help="العملة الافتراضية لأوامر الشراء واتفاقيات الشراء "
             "(بما فيها أوامر الشراء المتولّدة تلقائيًا في دورة "
             "الدروب-شيبنج). اتركها فارغة لاستخدام عملة الشركة. "
             "تبقى العملة قابلة للتغيير يدويًا على كل أمر شراء.",
    )

    def _mq_get_purchase_currency(self):
        """عملة الشراء الافتراضية لهذه الشركة (مع تحذير سعر الصرف)."""
        self.ensure_one()
        currency = self.mq_purchase_currency_id or self.currency_id
        if currency and currency != self.currency_id:
            rate = currency.with_context(
                company_id=self.id, date=fields.Date.context_today(self)
            ).rate
            if not rate or rate == 1.0:
                _logger.warning(
                    "QSS [purchase_currency] ⚠ عملة الشراء الافتراضية %s "
                    "تختلف عن عملة الشركة %s ولا يوجد لها سعر صرف صالح "
                    "(rate=%s). كل تحويل سيتم 1:1 — صحّح أسعار الصرف من "
                    "Accounting ▸ Configuration ▸ Currencies.",
                    currency.name, self.currency_id.name, rate,
                )
        return currency


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    mq_purchase_currency_id = fields.Many2one(
        related='company_id.mq_purchase_currency_id',
        string="Default Purchase Currency",
        readonly=False,
    )


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    @api.depends('partner_id', 'company_id')
    def _compute_currency_id(self):
        """الافتراضي = عملة الشراء المُعدّة للشركة، بدل عملة المورّد.

        الحقل نفسه يبقى ``readonly=False`` في أودو، فالمستخدم يستطيع
        تغييره إلى الدولار على أي أمر شراء يدوي.
        """
        super()._compute_currency_id()
        for order in self:
            if order.company_id:
                order.currency_id = order.company_id._mq_get_purchase_currency()


class PurchaseRequisition(models.Model):
    _inherit = 'purchase.requisition'

    @api.depends('vendor_id', 'company_id')
    def _compute_currency_id(self):
        super()._compute_currency_id()
        for requisition in self:
            if requisition.company_id:
                requisition.currency_id = (
                    requisition.company_id._mq_get_purchase_currency()
                )


class StockRule(models.Model):
    _inherit = 'stock.rule'

    def _prepare_purchase_order(self, company_id, origins, values):
        """أمر الشراء المتولّد تلقائيًا (دروب-شيبنج / إعادة التموين).

        هذه هي النقطة الحاسمة: المستخدم لا يرى أمر الشراء قبل إنشائه —
        «التأكيد رح يصير بيع وشراء بنفس اللحظة» — فيجب أن تكون العملة
        صحيحة لحظة الإنشاء لا بعدها.

        ملاحظة: أودو يحوّل سعر المورّد من عملة سطر ``supplierinfo`` إلى
        عملة أمر الشراء تلقائيًا في ``_prepare_purchase_order_line``
        (purchase_stock/models/stock_rule.py:309-311)، فسعر مسجَّل
        بالدولار سيصل إلى أمر الشراء محوَّلًا إلى الدينار — شرط وجود
        سعر صرف صحيح.
        """
        res = super()._prepare_purchase_order(company_id, origins, values)
        currency = company_id._mq_get_purchase_currency()
        if currency and res.get('currency_id') != currency.id:
            _logger.info(
                "QSS [purchase_currency] أمر شراء تلقائي: العملة %s ← %s",
                self.env['res.currency'].browse(res.get('currency_id')).name,
                currency.name,
            )
            res['currency_id'] = currency.id
        return res

    def _make_po_get_domain(self, company_id, values, partner):
        """مزامنة شرط العملة في البحث عن أمر شراء مسودة قابل للدمج.

        بدون هذا، قد يعثر أودو على أمر شراء مسودة قديم بالدولار ويضيف
        إليه السطر الجديد، فيلتفّ على التصحيح أعلاه.
        """
        domain = super()._make_po_get_domain(company_id, values, partner)
        currency = company_id._mq_get_purchase_currency()
        if not currency:
            return domain
        return tuple(
            ('currency_id', '=', currency.id)
            if (isinstance(clause, (tuple, list)) and clause[0] == 'currency_id')
            else clause
            for clause in domain
        )
