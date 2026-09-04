import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)

SHIPPING_PRODUCT_NAME = "أجور النقل والتخليص"


class SaleOrderLineAutomation(models.Model):
    _inherit = 'sale.order.line'

    x_studio_po_price = fields.Float(
        string="PO Price",
        help="Optional per-unit purchase price. When set, it overrides "
             "the automatically computed price on a dropship purchase "
             "order line created from this sale line.",
    )


class SaleOrderAutomation(models.Model):
    # ==================================================================
    # ملاحظة مهمة عن تاريخ هذا الملف - يرجى قراءتها قبل أي تعديل
    # ==================================================================
    # كانت هناك نسخة أولى من هذه الأتمتة (مبنية بإعادة استخدام آليات
    # الموديول الموجودة مسبقًا مثل action_calculate_scale_weight
    # و _create_invoices القياسية)، لكن تم استبدالها بناءً على طلب
    # المدير بمنطق الزميل كما ورد حرفيًا بدون أي تعديل اجتهادي.
    #
    # النسخة المُستبدَلة (القديمة) موجودة كاملة **معلَّقة** أسفل هذا
    # الملف مباشرة، تحت العنوان:
    #     "PREVIOUS IMPLEMENTATION (COMMENTED OUT - DO NOT DELETE)"
    #
    # للرجوع إليها لاحقًا:
    #   1) علّق (بإضافة #) الكود الحالي الممتد من تعريف الكلاس هذا حتى
    #      نهاية دالة _run_full_cycle_one أدناه.
    #   2) فُك التعليق عن الكتلة الموجودة أسفل الملف.
    #
    # تحديث (طلب إداري لاحق، سبتمبر 2026):
    #   - أصبح توزيع "الوزن الصافي" على سطور المنتجات توزيعًا تناسبيًا
    #     (نسبة كل سطر من إجمالي الكميات الأصلية) بدل تثبيت كل سطر على
    #     نفس قيمة net_weight بالكامل - هذا هو الفرق بين "محاكاة الفارق
    #     بين الوزن النظري ونتيجة القبان الحقيقية" الذي طلبه المدير.
    #   - أُضيف زر منفصل "Net Weight" (action_net_weight) يقوم بنفس
    #     منطق التوزيع + إضافة سطر أجور النقل، دون تأكيد الطلب - ليستخدمه
    #     العميل قبل الضغط على "تأكيد أمر البيع" لمعاينة التوزيع، تمامًا
    #     كما وصف المدير. زر "تنفيذ الدورة الكاملة" (Confirm SO) يستدعي
    #     نفس منطق التوزيع داخليًا تلقائيًا (في حال نسي المستخدم الضغط
    #     على Net Weight أولاً) عبر الميثود المشتركة
    #     ``_apply_net_weight_distribution`` أدناه، فلا يوجد أي ازدواجية
    #     أو احتمال تعارض بين الزرّين.
    # ==================================================================
    _inherit = 'sale.order'

    x_studio_net_weight = fields.Float(string="Net weight")
    x_studio_shipping_cost_ton = fields.Float(string="Shipping Cost (Ton)")
    x_studio_total_net_weight = fields.Float(
        string="Total Net Weight",
        compute="_compute_x_studio_total_net_weight",
        help="مجموع كميات سطور المنتجات المؤهلة (بعد استثناء الملاحظات "
             "والـ Sections والمنتجات الخدمية وسطر أجور النقل) - يجب أن "
             "يطابق قيمة Net Weight أعلاه بعد الضغط على زر Net Weight أو "
             "Confirm SO.",
    )

    @api.depends(
        'order_line.product_uom_qty',
        'order_line.display_type',
        'order_line.product_id.type',
        'order_line.name',
    )
    def _compute_x_studio_total_net_weight(self):
        for so in self:
            valid_lines = so.order_line.filtered(
                lambda l: l.display_type not in ('line_section', 'line_note')
                and l.product_id.type != 'service'
                and SHIPPING_PRODUCT_NAME not in (l.name or '')
            )
            so.x_studio_total_net_weight = sum(valid_lines.mapped('product_uom_qty'))

    # ------------------------------------------------------------------
    # Shared "Net Weight" logic - management's algorithm, ported literally:
    # proportionally distribute x_studio_net_weight across eligible lines
    # by their existing quantity ratio (simulating the difference between
    # theoretical weight and the real scale reading after impurities/dust
    # are removed), then (re)create the shipping/clearance fee line as
    # shipping_cost_ton * net_weight, always last by sequence.
    # ------------------------------------------------------------------
    def _apply_net_weight_distribution(self):
        self.ensure_one()
        so = self
        env = self.env

        net_weight = 0.0
        if 'x_studio_net_weight' in so._fields:
            net_weight = so.x_studio_net_weight or 0.0
        _logger.info(
            "QSS [net_weight] id=%s | x_studio_net_weight=%s", so.id, net_weight,
        )

        # الأسطر المؤهلة للتوزيع (تستثني الملاحظات والـ Sections والمنتجات
        # الخدمية وسطر أجور النقل نفسه)
        valid_lines = so.order_line.filtered(
            lambda l: l.display_type not in ('line_section', 'line_note')
            and l.product_id.type != 'service'
            and SHIPPING_PRODUCT_NAME not in (l.name or '')
        )

        if net_weight > 0 and valid_lines:
            total_original_qty = sum(valid_lines.mapped('product_uom_qty'))
            if total_original_qty > 0:
                for line in valid_lines:
                    proportion = line.product_uom_qty / total_original_qty
                    new_line_qty = net_weight * proportion
                    vals = {'product_uom_qty': new_line_qty}
                    if 'mq_quantity' in line._fields:
                        vals['mq_quantity'] = new_line_qty
                    elif 'x_studio_mq_quantity' in line._fields:
                        vals['x_studio_mq_quantity'] = new_line_qty
                    line.write(vals)
                    _logger.info(
                        "QSS [net_weight] id=%s | سطر %s: نسبة=%.4f ← كمية جديدة=%.4f",
                        so.id, line.id, proportion, new_line_qty,
                    )
            else:
                _logger.warning(
                    "QSS [net_weight] id=%s | مجموع الكميات الأصلية = صفر — "
                    "تعذّر التوزيع النسبي.", so.id,
                )
        else:
            _logger.warning(
                "QSS [net_weight] id=%s | الوزن الصافي = 0 أو لا توجد سطور "
                "مؤهلة — لن يتم أي توزيع.", so.id,
            )

        # أجور النقل والتخليص = shipping_cost_ton * net_weight
        shipping_cost_unit = 0.0
        if 'x_studio_shipping_cost_ton' in so._fields:
            shipping_cost_unit = so.x_studio_shipping_cost_ton or 0.0

        if shipping_cost_unit > 0 and net_weight > 0:
            total_shipping_fee = shipping_cost_unit * net_weight
            _logger.info(
                "QSS [net_weight] id=%s | إجمالي أجور النقل = %s × %s = %s",
                so.id, shipping_cost_unit, net_weight, total_shipping_fee,
            )
            shipping_product = env['product.product'].search(
                [('name', 'ilike', SHIPPING_PRODUCT_NAME)], limit=1
            )
            if not shipping_product:
                shipping_product = env['product.product'].create({
                    'name': SHIPPING_PRODUCT_NAME,
                    'type': 'service',
                    'invoice_policy': 'order',
                })
            # حذف السطر القديم إن وجد لضمان إعادة إنشائه في آخر القائمة
            existing_shipping_line = so.order_line.filtered(
                lambda l: l.product_id.id == shipping_product.id
            )
            if existing_shipping_line:
                existing_shipping_line.unlink()

            max_sequence = max(so.order_line.mapped('sequence'), default=10)
            env['sale.order.line'].create({
                'order_id': so.id,
                'product_id': shipping_product.id,
                'name': SHIPPING_PRODUCT_NAME,
                'product_uom_qty': 1.0,
                'price_unit': total_shipping_fee,
                'sequence': max_sequence + 1,
            })

    # ------------------------------------------------------------------
    # Smart button "هلال بابل" (fixed label, per management request -
    # replaces the Studio smart button that used to say "Drop-Shipping"
    # and always opened the dropship stock transfer for this order, whose
    # Contact is always the same fixed vendor "هلال بابل"). Since that
    # vendor relationship is configured on the purchase side (Studio),
    # this button simply reproduces the *navigation* behaviour with the
    # fixed label the manager asked for: it jumps straight to the
    # dropship picking(s) linked to this order's purchase orders.
    # ------------------------------------------------------------------
    x_studio_dropship_picking_count = fields.Integer(
        string="Dropship Pickings",
        compute="_compute_x_studio_dropship_picking_count",
    )

    @api.depends('order_line.product_id')
    def _compute_x_studio_dropship_picking_count(self):
        for so in self:
            po_lines = self.env['purchase.order.line'].search(
                [('sale_line_id', 'in', so.order_line.ids)]
            )
            so.x_studio_dropship_picking_count = len(po_lines.mapped('order_id.picking_ids'))

    def action_view_dropship_pickings(self):
        self.ensure_one()
        po_lines = self.env['purchase.order.line'].search(
            [('sale_line_id', 'in', self.order_line.ids)]
        )
        pickings = po_lines.mapped('order_id.picking_ids')
        action = self.env['ir.actions.act_window']._for_xml_id('stock.action_picking_tree_all')
        action['domain'] = [('id', 'in', pickings.ids)]
        if len(pickings) == 1:
            action['views'] = [(False, 'form')]
            action['res_id'] = pickings.id
        return action

    def action_net_weight(self):
        """زر 'Net Weight' المستقل: يوزّع الوزن الصافي تناسبيًا على سطور
        المنتجات ويضيف/يحدّث سطر أجور النقل والتخليص، دون تأكيد أمر
        البيع - لمعاينة التوزيع قبل التأكيد النهائي."""
        for so in self:
            so._apply_net_weight_distribution()

    def action_run_full_cycle(self):
        """تنفيذ حرفي لمنطق الزميل الأصلي (Studio Server Action) بدون أي
        تعديل في التسلسل أو الشروط - فقط أُعيدت كتابته كميثود Odoo عادية
        بدل سكربت execute code، تمامًا كما طلب المدير. منطق توزيع الوزن
        الصافي (زر Net Weight) مُضمَّن هنا تلقائيًا كخطوة أولى، تحسبًا
        لنسيان المستخدم الضغط عليه بشكل منفصل."""
        _logger.info(
            "QSS [full_cycle] ▶ تم استدعاء الإجراء على %s أمر/أوامر: ids=%s",
            len(self), self.ids,
        )
        for so in self:
            _logger.info(
                "QSS [full_cycle] ── بدء معالجة أمر البيع: id=%s name=%s state=%s",
                so.id, so.name, so.state,
            )
            so._run_full_cycle_one()
            _logger.info(
                "QSS [full_cycle] ✅ انتهت معالجة أمر البيع id=%s بنجاح.", so.id,
            )

    def _run_full_cycle_one(self):
        self.ensure_one()
        so = self
        env = self.env

        # 1-3. الخطوة الأساسية والأولى: توزيع الوزن الصافي تناسبيًا على
        #    سطور المنتجات + سطر أجور النقل - نفس منطق زر Net Weight
        #    بالضبط (مضمّن هنا كما طلب المدير).
        net_weight = 0.0
        if 'x_studio_net_weight' in so._fields:
            net_weight = so.x_studio_net_weight or 0.0
        so._apply_net_weight_distribution()

        # 4. تأكيد أمر المبيعات
        _logger.info("QSS [step4] id=%s | حالة أمر البيع = %s", so.id, so.state)
        if so.state in ['draft', 'sent']:
            so.action_confirm()
            _logger.info("QSS [step4] id=%s | تم تأكيد أمر البيع ✔", so.id)
        else:
            _logger.info("QSS [step4] id=%s | أمر البيع محدد مسبقًا — لا حاجة لتأكيد.", so.id)

        # 5. البحث الذكي عن أوامر الشراء المرتبطة (لو الحالة دروب شيبنج)
        po_lines = env['purchase.order.line'].search(
            [('sale_line_id', 'in', so.order_line.ids)]
        )
        purchase_orders = po_lines.mapped('order_id')
        _logger.info(
            "QSS [step5] id=%s | أوامر شراء مرتبطة = %s ids=%s",
            so.id, len(purchase_orders), purchase_orders.ids,
        )
        if purchase_orders:
            for po in purchase_orders:
                if po.partner_id and 'requisition_id' in po._fields:
                    open_requisition = env['purchase.requisition'].search([
                        ('vendor_id', '=', po.partner_id.id),
                        ('state', '=', 'confirmed'),
                        ('company_id', '=', po.company_id.id),
                    ], limit=1)
                    if open_requisition:
                        po.write({'requisition_id': open_requisition.id})
                if po.state in ['draft', 'sent', 'to approve']:
                    po.button_confirm()

        # 6. تجميع حركات المخزن واعتمادها
        all_pickings = so.picking_ids | purchase_orders.mapped('picking_ids')
        _logger.info(
            "QSS [step6] id=%s | حركات مخزن (pickings) = %s ids=%s",
            so.id, len(all_pickings), all_pickings.ids,
        )
        for picking in all_pickings:
            if picking.state not in ['done', 'cancel']:
                if picking.state in ['confirmed', 'waiting']:
                    picking.action_assign()
                for move in picking.move_ids:
                    if move.state not in ['done', 'cancel']:
                        qty_to_set = (
                            move.sale_line_id.product_uom_qty if move.sale_line_id
                            else (net_weight if net_weight > 0 else move.product_uom_qty)
                        )
                        move.write({
                            'product_uom_qty': qty_to_set,
                            'quantity': qty_to_set,
                        })
                res = picking.with_context(
                    skip_backorder=True, cancel_backorder=True, skip_immediate=True,
                ).button_validate()
                if isinstance(res, dict) and res.get('res_model') == 'stock.backorder.confirmation':
                    env['stock.backorder.confirmation'].browse(
                        res.get('res_id')
                    ).process_cancel_backorder()

        # 7. تحديث كميات وأسعار أوامر الشراء بناءً على الكميات الموزعة
        #    تناسبيًا لكل سطر (نفس نسبة سطر أمر البيع المقابل)
        _logger.info("QSS [step7] id=%s | تحديث أوامر الشراء...", so.id)
        if purchase_orders:
            for po in purchase_orders:
                for po_line in po.order_line:
                    if po_line.display_type not in ['line_section', 'line_note']:
                        po_vals = {}
                        sale_line = po_line.sale_line_id

                        if sale_line:
                            po_vals['product_qty'] = sale_line.product_uom_qty
                            if 'mq_quantity' in po_line._fields:
                                po_vals['mq_quantity'] = sale_line.product_uom_qty
                            elif 'x_studio_mq_quantity' in po_line._fields:
                                po_vals['x_studio_mq_quantity'] = sale_line.product_uom_qty
                        if (sale_line and 'x_studio_po_price' in sale_line._fields
                                and sale_line.x_studio_po_price > 0):
                            po_vals['price_unit'] = sale_line.x_studio_po_price

                        if po_vals:
                            po_line.write(po_vals)
                            if 'qty_received' in po_line._fields:
                                po_line.write({'qty_received': po_line.product_qty})

        # 8. التعامل مع فاتورة المبيعات (التحقق إذا كانت منشأة مسبقاً أو
        #    إنشاؤها مرة واحدة وترحيلها)
        _logger.info(
            "QSS [step8] id=%s | فواتير موجودة مسبقًا = %s ids=%s",
            so.id, len(so.invoice_ids), so.invoice_ids.ids,
        )
        if not so.invoice_ids:
            invoice_date = so.date_order
            invoice_line_vals = []
            for line in so.order_line:
                if line.display_type in ['line_section', 'line_note']:
                    continue
                tax_ids = []
                if 'tax_id' in line._fields and line.tax_id:
                    tax_ids = [(6, 0, line.tax_id.ids)]
                elif 'tax_ids' in line._fields and line.tax_ids:
                    tax_ids = [(6, 0, line.tax_ids.ids)]
                invoice_line_vals.append((0, 0, {
                    'product_id': line.product_id.id,
                    'name': line.name,
                    'quantity': line.product_uom_qty,
                    'price_unit': line.price_unit,
                    'tax_ids': tax_ids,
                    'sale_line_ids': [(6, 0, [line.id])],
                }))
            if invoice_line_vals:
                inv_vals = {
                    'move_type': 'out_invoice',
                    'partner_id': so.partner_invoice_id.id or so.partner_id.id,
                    'invoice_date': invoice_date,
                    'currency_id': so.currency_id.id,
                    'invoice_line_ids': invoice_line_vals,
                    'invoice_origin': so.name,
                }
                new_invoice = env['account.move'].create(inv_vals)
                new_invoice.action_post()
        else:
            for inv in so.invoice_ids.filtered(lambda i: i.state == 'draft'):
                inv.action_post()

        # 9. إنشاء فاتورة المشتريات (Vendor Bill) مرة واحدة فقط لكل أمر
        #    شراء (لو وُجد دروب شيبنج)
        _logger.info("QSS [step9] id=%s | إنشاء فواتير المورد...", so.id)
        if purchase_orders:
            for po in purchase_orders:
                if not po.invoice_ids:
                    bill_line_vals = []
                    for po_line in po.order_line:
                        if po_line.display_type in ['line_section', 'line_note']:
                            continue
                        po_tax_ids = []
                        if 'taxes_id' in po_line._fields and po_line.taxes_id:
                            po_tax_ids = [(6, 0, po_line.taxes_id.ids)]
                        elif 'tax_id' in po_line._fields and po_line.tax_id:
                            po_tax_ids = [(6, 0, po_line.tax_id.ids)]
                        bill_line_vals.append((0, 0, {
                            'product_id': po_line.product_id.id,
                            'name': po_line.name,
                            'quantity': po_line.product_qty,
                            'price_unit': po_line.price_unit,
                            'tax_ids': po_tax_ids,
                            'purchase_line_id': po_line.id,
                        }))
                    if bill_line_vals:
                        bill_vals = {
                            'move_type': 'in_invoice',
                            'partner_id': po.partner_id.id,
                            'invoice_date': so.date_order,
                            'currency_id': po.currency_id.id,
                            'invoice_line_ids': bill_line_vals,
                            'invoice_origin': po.name,
                        }
                        new_bill = env['account.move'].create(bill_vals)
                        new_bill.action_post()
                else:
                    for bill in po.invoice_ids.filtered(lambda b: b.state == 'draft'):
                        bill.action_post()

# ======================================================================
# PREVIOUS IMPLEMENTATION (COMMENTED OUT - DO NOT DELETE)
# ----------------------------------------------------------------------
# هذه هي النسخة السابقة الكاملة (قبل طلب المدير)، والتي كانت تعيد
# استخدام آليات الموديول الجاهزة (توزيع الوزن النسبي عبر
# action_calculate_scale_weight، والفوترة عبر _create_invoices /
# action_create_invoice القياسية، وعزل كل أمر بيع داخل savepoint خاص
# به عند التشغيل الجماعي). تُركت هنا معلّقة بالكامل للرجوع إليها متى
# احتجتم ذلك - راجعوا الملاحظة أعلى الملف لطريقة التبديل بينها وبين
# النسخة المُفعَّلة حاليًا.
#
# للاستخدام: احذفوا علامات "#" من بداية كل سطر بالأسفل، وعلّقوا
# (بإضافة #) الكود المُفعَّل أعلاه بدلاً منه.
# ======================================================================
#
# from odoo.exceptions import UserError
#
# class SaleOrderAutomation(models.Model):
#     """Formalizes the manual 'full cycle' Server Action into a proper,
#     reviewable method.
#
#     Design notes / deliberate differences from the original ad-hoc code -
#     see chat for the full explanation:
#
#     * Net-weight sync (step 1) now reuses the module's own, existing
#       ``action_calculate_scale_weight`` (on sale.order / purchase.order /
#       stock.picking), which distributes the scale weight *proportionally*
#       across lines flagged "Bundle Weight" on the product, instead of
#       blindly forcing every non-service line to the exact same quantity.
#       It reads the weight from the existing ``mq_scale_net_weight`` field
#       rather than introducing a second, competing "net weight" field.
#     * Stock quantities (step 6) are set the same way, via
#       ``picking.action_calculate_scale_weight()``, instead of writing the
#       same quantity onto every move in a picking regardless of product.
#     * Customer invoice (step 8) and vendor bill (step 9) are created with
#       Odoo's own ``_create_invoices()`` / ``action_create_invoice()``
#       instead of hand-built invoice lines, so taxes, discounts and
#       invoicing policy are computed exactly the way they are everywhere
#       else in the database.
#     * ``qty_received`` on the purchase line is no longer force-written -
#       it's a computed field that Odoo already recalculates correctly from
#       the validated receipt, so a manual write to it would just be
#       overwritten again (and was dropped as a no-op / anti-pattern).
#     * Each order in a bulk selection runs inside its own DB savepoint: if
#       one order fails partway through, only that order's changes are
#       rolled back, the rest of the selection still gets processed, and a
#       summary of any failures is raised at the end instead of failing
#       silently or losing every record's progress.
#     """
#     _inherit = 'sale.order'
#
#     x_studio_shipping_cost_ton = fields.Float(string="Shipping Cost (Ton)")
#
#     # ------------------------------------------------------------------
#     # Helpers
#     # ------------------------------------------------------------------
#     def _get_shipping_service_product(self):
#         """Fetch (or create once) the generic shipping/clearance service
#         product used for the auto-added shipping fee line."""
#         Product = self.env['product.product']
#         product = Product.search([('name', '=', SHIPPING_PRODUCT_NAME)], limit=1)
#         if not product:
#             product = Product.create({
#                 'name': SHIPPING_PRODUCT_NAME,
#                 'type': 'service',
#                 'invoice_policy': 'order',
#             })
#         return product
#
#     def _sync_shipping_fee_line(self, net_weight):
#         """Add or update the shipping fee line as
#         x_studio_shipping_cost_ton * net_weight. No-op if either is 0."""
#         self.ensure_one()
#         if not (self.x_studio_shipping_cost_ton > 0 and net_weight > 0):
#             return
#         total_fee = self.x_studio_shipping_cost_ton * net_weight
#         shipping_product = self._get_shipping_service_product()
#         shipping_line = self.order_line.filtered(lambda l: l.product_id == shipping_product)
#         if shipping_line:
#             shipping_line.write({'product_uom_qty': 1.0, 'price_unit': total_fee})
#         else:
#             self.env['sale.order.line'].create({
#                 'order_id': self.id,
#                 'product_id': shipping_product.id,
#                 'name': shipping_product.name,
#                 'product_uom_qty': 1.0,
#                 'price_unit': total_fee,
#             })
#
#     # ------------------------------------------------------------------
#     # Main entry point
#     # ------------------------------------------------------------------
#     def action_run_full_cycle(self):
#         """Runs quote-to-cash + dropship procure-to-pay for each selected
#         order: sync the scale weight, add the shipping fee, confirm the
#         sale, confirm & link any dropship purchase orders, validate all
#         transfers, then create and post the customer invoice and any
#         vendor bill(s).
#         """
#         errors = []
#         for so in self:
#             try:
#                 with self.env.cr.savepoint():
#                     so._run_full_cycle_one()
#             except Exception as exc:  # noqa: BLE001 - see docstring: isolate failures per order
#                 _logger.exception(
#                     "qader_steel_suite: full-cycle automation failed for %s",
#                     so.display_name,
#                 )
#                 errors.append(f"{so.display_name}: {exc}")
#         if errors:
#             raise UserError(
#                 "تعذّرت المعالجة الكاملة للأوامر التالية (تم التراجع عن "
#                 "تغييراتها فقط، وبقية الأوامر المختارة تمّت معالجتها "
#                 "بنجاح):\n\n" + "\n".join(errors)
#             )
#
#     def _run_full_cycle_one(self):
#         self.ensure_one()
#         so = self
#
#         # 1) Sync the scale weight to the order lines - reuses the
#         #    existing proportional bundle-weight distribution.
#         net_weight = so.mq_scale_net_weight or 0.0
#         if net_weight > 0:
#             so.action_calculate_scale_weight()
#
#         # 2-3) Shipping / clearance fee line
#         so._sync_shipping_fee_line(net_weight)
#
#         # 4) Confirm the sale order
#         if so.state in ('draft', 'sent'):
#             so.action_confirm()
#
#         # 5) Find any dropship purchase orders linked through this
#         #    order's lines, attach an open requisition if one matches,
#         #    apply the custom PO price override, then confirm.
#         po_lines = self.env['purchase.order.line'].search(
#             [('sale_line_id', 'in', so.order_line.ids)]
#         )
#         purchase_orders = po_lines.mapped('order_id')
#         for po in purchase_orders:
#             if po.partner_id and not po.requisition_id:
#                 open_requisition = self.env['purchase.requisition'].search([
#                     ('vendor_id', '=', po.partner_id.id),
#                     ('state', '=', 'confirmed'),
#                     ('company_id', '=', po.company_id.id),
#                 ], limit=1)
#                 if open_requisition:
#                     po.requisition_id = open_requisition.id
#
#             # 7) PO price override from the sale line (must happen before
#             #    confirming, so the confirmed PO carries the right price).
#             for po_line in po.order_line.filtered(
#                 lambda l: l.display_type not in ('line_section', 'line_note')
#             ):
#                 sale_line = po_line.sale_line_id
#                 if sale_line and sale_line.x_studio_po_price > 0:
#                     po_line.price_unit = sale_line.x_studio_po_price
#
#             if po.state in ('draft', 'sent', 'to approve'):
#                 po.button_confirm()
#
#         # 6) Validate deliveries & receipts, reusing the same proportional
#         #    weight distribution wherever the picking carries bundle
#         #    weight products.
#         all_pickings = so.picking_ids | purchase_orders.mapped('picking_ids')
#         for picking in all_pickings:
#             if picking.state in ('done', 'cancel'):
#                 continue
#             if picking.state in ('confirmed', 'waiting'):
#                 picking.action_assign()
#             if net_weight > 0:
#                 picking.action_calculate_scale_weight()
#             picking.with_context(
#                 skip_backorder=True, cancel_backorder=True, skip_immediate=True,
#             ).button_validate()
#
#         # 8) Customer invoice - via Odoo's own invoicing method so taxes,
#         #    discounts and invoicing policy are computed as everywhere else.
#         if not so.invoice_ids:
#             invoices = so._create_invoices()
#             invoices.action_post()
#         else:
#             so.invoice_ids.filtered(lambda i: i.state == 'draft').action_post()
#
#         # 9) Vendor bill(s) for any dropship purchase orders - same idea,
#         #    via the standard purchase-side method.
#         for po in purchase_orders:
#             if not po.invoice_ids:
#                 po.action_create_invoice()
#                 po.invoice_ids.filtered(lambda b: b.state == 'draft').action_post()
#             else:
#                 po.invoice_ids.filtered(lambda b: b.state == 'draft').action_post()
