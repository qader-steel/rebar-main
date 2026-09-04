from odoo import models, fields, api

class SaleOrderLine(models.Model):
    """
    Inherited to handle bundle quantity logic for sale order lines.
    """
    _inherit = 'sale.order.line'

    mq_bundle_qty = fields.Float(string="كمية الحزم", digits='Product Unit of Measure')
    mq_quantity = fields.Float(string="الكمية", digits='Product Unit of Measure')

    # ==================================================================
    # طلب إداري (سبتمبر 2026) - سلوك "Bundle Qty"
    # ------------------------------------------------------------------
    # "البندل كوانتيتي الموجود على كل سطر منتج ضمن أمر البيع تتغير يدويًا،
    #  بينما الباقي خارج هذه الأسطر فهو الإجمالي لكل البندل لكل أسطر
    #  المنتجات."
    #
    # أي: mq_bundle_qty على كل سطر = إدخال يدوي بحت يكتبه المستخدم، ولا
    # يجوز لأي كود أن يكتب فوقه. و mq_total_bundle_qty على مستوى أمر
    # البيع = مجموع هذه القيم اليدوية (محسوب أدناه في SaleOrder).
    #
    # سبب المشكلة السابقة ("الباندل كوانتيتي محطوطة افتراضيًا 1 وما عم
    # تتغير"): كانت الـ onchange الثلاث تعيد كتابة mq_bundle_qty من
    # product_uom_qty في كل مرة عندما لا يكون المنتج مُعلَّمًا بـ
    # "Bundle Weight" - وهو الوضع الافتراضي لكل المنتجات. فبمجرد ما
    # يكتب المستخدم رقمًا، تنطلق الـ onchange وتُرجعه فورًا إلى 1.
    # هذا الـ "snap back" أُزيل بالكامل أدناه.
    # ==================================================================
    @api.onchange('mq_bundle_qty', 'product_id')
    def _onchange_mq_bundle_qty(self):
        """كمية الحزم تقود الكمية لكل المنتجات:
        - منتج مُعلَّم "Bundle Weight": الكمية = كمية الحزم × المُعامِل
        - أي منتج آخر: الكمية = كمية الحزم (مُعامِل ضمني = 1)
        هذا يضمن أن نسب التوزيع عند الضغط على زر "الوزن الصافي" تكون
        مبنية على كمية الحزم المُدخلة يدويًا."""
        for line in self:
            if line.product_id and line.product_id.mq_is_bundle_weight:
                multiplier = line.product_id.mq_bundle_multiplier or 1.0
                line.mq_quantity = line.mq_bundle_qty * multiplier
                line.product_uom_qty = line.mq_quantity
            else:
                # مُعامِل ضمني = 1: كمية الحزم = الكمية مباشرة
                line.mq_quantity = line.mq_bundle_qty
                line.product_uom_qty = line.mq_bundle_qty

    @api.onchange('mq_quantity')
    def _onchange_mq_quantity(self):
        """عمود "Quantity" يقود product_uom_qty. mq_bundle_qty إدخال يدوي
        ولا يُمَس هنا إطلاقًا."""
        for line in self:
            line.product_uom_qty = line.mq_quantity

    @api.onchange('product_uom_qty', 'product_id')
    def _onchange_product_uom_qty(self):
        """يبقي عمود "Quantity" الظاهر متطابقًا مع الكمية الحقيقية.
        mq_bundle_qty إدخال يدوي ولا يُمَس هنا إطلاقًا."""
        for line in self:
            if line.product_uom_qty != line.mq_quantity:
                line.mq_quantity = line.product_uom_qty

    def _prepare_invoice_line(self, **optional_values):
        res = super(SaleOrderLine, self)._prepare_invoice_line(**optional_values)
        res['mq_bundle_qty'] = self.mq_bundle_qty
        res['mq_quantity'] = self.mq_quantity
        return res

class SaleOrder(models.Model):
    """
    Inherited to compute total bundle quantity and total weight for the order.
    """
    _inherit = 'sale.order'

    # NOTE (management request, Sept 2026): on the Sale Order specifically,
    # "Scale Net Weight" is no longer entered/calculated by hand - it must
    # always mirror the "Net Weight" field (x_studio_net_weight, defined in
    # sale_order_automation.py) so downstream consumers of this field
    # (stock.picking.mq_scale_net_weight below, printed reports, etc.) stay
    # correct automatically. The manual "احتساب وزن القبان الصافي" button
    # and its distribute-by-bundle-ratio logic were removed from the Sale
    # Order form for this reason (still present, unchanged, on Purchase
    # Order and Stock Picking).
    mq_scale_net_weight = fields.Float(
        string="صافي وزن الميزان",
        compute="_compute_mq_scale_net_weight",
        store=True,
    )
    mq_total_bundle_qty = fields.Float(string="إجمالي كمية الحزم", compute="_compute_mq_total_bundle", store=True)
    mq_total_weight = fields.Float(string="إجمالي الوزن (طن)", compute="_compute_mq_total_weight", store=True)

    @api.depends('x_studio_net_weight')
    def _compute_mq_scale_net_weight(self):
        for order in self:
            order.mq_scale_net_weight = order.x_studio_net_weight or 0.0

    @api.depends('order_line.mq_bundle_qty')
    def _compute_mq_total_bundle(self):
        for order in self:
            order.mq_total_bundle_qty = sum(order.order_line.mapped('mq_bundle_qty'))

    @api.depends('picking_ids.mq_scale_net_weight', 'picking_ids.state')
    def _compute_mq_total_weight(self):
        for order in self:
            # We sum the scale net weight from related active deliveries
            valid_pickings = order.picking_ids.filtered(lambda p: p.state != 'cancel')
            order.mq_total_weight = sum(valid_pickings.mapped('mq_scale_net_weight'))