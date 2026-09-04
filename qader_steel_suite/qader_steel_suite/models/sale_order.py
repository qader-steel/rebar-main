# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_round


class SaleOrderLine(models.Model):
    """Sale-line quantity and bundle helpers used by the net-weight workflow."""

    _inherit = 'sale.order.line'

    mq_bundle_qty = fields.Float(
        string="Bundle Qty",
        digits='Product Unit of Measure',
    )
    mq_quantity = fields.Float(
        string="Quantity",
        digits='Product Unit of Measure',
    )
    qss_weight_base_qty = fields.Float(
        string="Net Weight Base Qty",
        digits='Product Unit of Measure',
        copy=False,
        readonly=True,
        help=(
            "Original theoretical quantity used as the basis for proportional "
            "net-weight distribution. It is intentionally kept unchanged "
            "while the net-weight calculation updates the order line."
        ),
    )

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for line in records:
            if not line.display_type and line.product_id:
                base_qty = line._qss_theoretical_qty()
                line.qss_weight_base_qty = base_qty
        return records

    def write(self, vals):
        """Keep a stable theoretical quantity for future recalculations.

        When the user edits an order line manually, the new value becomes the
        theoretical basis. Writes performed by the net-weight algorithm are
        excluded through a context flag so the already calculated basis is not
        overwritten by the calculated result.
        """
        result = super().write(vals)
        if self.env.context.get('qss_distributing_net_weight'):
            return result

        watched = {'product_uom_qty', 'mq_quantity', 'mq_bundle_qty', 'product_id'}
        if watched.intersection(vals):
            for line in self:
                if not line.display_type and line.product_id:
                    line.qss_weight_base_qty = line._qss_theoretical_qty()
        return result

    def _qss_theoretical_qty(self):
        self.ensure_one()
        if not self.product_id:
            return 0.0
        if self.product_id.mq_is_bundle_weight:
            multiplier = self.product_id.mq_bundle_multiplier or 1.0
            return max(self.mq_bundle_qty, 0.0) * multiplier
        if self.qss_weight_base_qty > 0:
            return self.qss_weight_base_qty
        return max(self.product_uom_qty or self.mq_quantity or 0.0, 0.0)

    @api.onchange('mq_bundle_qty', 'product_id')
    def _onchange_mq_bundle_qty(self):
        for line in self:
            if line.product_id and line.product_id.mq_is_bundle_weight:
                multiplier = line.product_id.mq_bundle_multiplier or 1.0
                line.mq_quantity = line.mq_bundle_qty * multiplier
                line.product_uom_qty = line.mq_quantity
            else:
                line.mq_bundle_qty = line.product_uom_qty

    @api.onchange('mq_quantity', 'product_id')
    def _onchange_mq_quantity(self):
        for line in self:
            line.product_uom_qty = line.mq_quantity
            if not (line.product_id and line.product_id.mq_is_bundle_weight):
                line.mq_bundle_qty = line.mq_quantity

    @api.onchange('product_uom_qty', 'product_id')
    def _onchange_product_uom_qty(self):
        for line in self:
            if line.product_uom_qty != line.mq_quantity:
                line.mq_quantity = line.product_uom_qty
            if not (line.product_id and line.product_id.mq_is_bundle_weight):
                line.mq_bundle_qty = line.product_uom_qty

    def _prepare_invoice_line(self, **optional_values):
        res = super()._prepare_invoice_line(**optional_values)
        res['mq_bundle_qty'] = self.mq_bundle_qty
        res['mq_quantity'] = self.mq_quantity
        return res


class SaleOrder(models.Model):
    """Net-weight workflow fields and calculations for Sales Orders."""

    _inherit = 'sale.order'

    # These are the existing Studio-facing technical fields used by the
    # implementation. They are kept so existing databases do not need a data
    # migration just to adopt the new Python workflow.
    x_studio_net_weight = fields.Float(string="Net weight")
    x_studio_shipping_cost_ton = fields.Float(string="Shipping Cost (Ton)")

    mq_scale_net_weight = fields.Float(
        string="Scale Net Weight",
        related='x_studio_net_weight',
        store=True,
        readonly=True,
    )
    mq_total_bundle_qty = fields.Float(
        string="Total Bundle Qty",
        compute="_compute_mq_total_bundle",
        store=True,
    )
    mq_total_weight = fields.Float(
        string="Total Net Weight (Ton)",
        compute="_compute_mq_total_weight",
        store=True,
    )

    @api.depends('order_line.mq_bundle_qty')
    def _compute_mq_total_bundle(self):
        for order in self:
            order.mq_total_bundle_qty = sum(order.order_line.mapped('mq_bundle_qty'))

    @api.depends('x_studio_net_weight')
    def _compute_mq_total_weight(self):
        for order in self:
            order.mq_total_weight = order.x_studio_net_weight or 0.0

    def _qss_net_weight_lines(self):
        """Return only product lines eligible for proportional distribution."""
        self.ensure_one()
        return self.order_line.filtered(
            lambda line: (
                line.display_type not in ('line_section', 'line_note')
                and line.product_id
                and line.product_id.type != 'service'
                and not self._qss_is_shipping_line(line)
            )
        )

    @staticmethod
    def _qss_is_shipping_line(line):
        name = (line.name or '').strip()
        return name == 'أجور النقل والتخليص' or 'أجور النقل' in name

    def _qss_sync_shipping_fee_line(self):
        """Synchronise exactly one shipping/clearance service line."""
        self.ensure_one()
        ShippingProduct = self.env['product.product']
        shipping_product = ShippingProduct.search([
            ('name', '=', 'أجور النقل والتخليص'),
            ('type', '=', 'service'),
            '|',
            ('company_id', '=', False),
            ('company_id', '=', self.company_id.id),
        ], limit=1)
        existing = self.order_line.filtered(self._qss_is_shipping_line)
        net_weight = self.x_studio_net_weight or 0.0
        shipping_cost_ton = self.x_studio_shipping_cost_ton or 0.0

        # Clear old shipping lines when the shipping cost is removed.
        if net_weight <= 0 or shipping_cost_ton <= 0:
            if existing:
                existing.unlink()
            return

        if not shipping_product:
            shipping_product = ShippingProduct.create({
                'name': 'أجور النقل والتخليص',
                'type': 'service',
                'invoice_policy': 'order',
            })

        total_fee = shipping_cost_ton * net_weight
        shipping_line = existing[:1]
        if shipping_line:
            shipping_line.with_context(
                qss_distributing_net_weight=True
            ).write({
                'product_id': shipping_product.id,
                'name': 'أجور النقل والتخليص',
                'product_uom_qty': 1.0,
                'price_unit': total_fee,
            })
            (existing - shipping_line).unlink()
        else:
            self.env['sale.order.line'].create({
                'order_id': self.id,
                'product_id': shipping_product.id,
                'name': 'أجور النقل والتخليص',
                'product_uom_qty': 1.0,
                'price_unit': total_fee,
                'sequence': max(self.order_line.mapped('sequence') or [10]) + 1,
            })

    def action_calculate_net_weight(self):
        """Distribute entered Net Weight proportionally across product lines."""
        for order in self:
            net_weight = order.x_studio_net_weight or 0.0
            if net_weight <= 0:
                raise UserError("يجب إدخال قيمة Net Weight أكبر من صفر.")

            lines = order._qss_net_weight_lines()
            if not lines:
                raise UserError("لا توجد منتجات مؤهلة لتوزيع Net Weight عليها.")

            bases = {line.id: line._qss_theoretical_qty() for line in lines}
            total_base = sum(bases.values())
            if total_base <= 0:
                raise UserError(
                    "يجب أن تكون الكميات النظرية للمنتجات أكبر من صفر قبل حساب Net Weight."
                )

            # Use the order-line UoM precision where possible, and assign the
            # final residual to the last line so the total is exactly the
            # entered net weight rather than being off by rounding fractions.
            rounded_weight = float_round(net_weight, precision_digits=6)
            running = 0.0
            ordered_lines = lines.sorted('sequence,id')
            for index, line in enumerate(ordered_lines):
                if index == len(ordered_lines) - 1:
                    distributed = rounded_weight - running
                else:
                    proportion = bases[line.id] / total_base
                    distributed = float_round(
                        rounded_weight * proportion,
                        precision_digits=6,
                    )
                    running += distributed

                distributed = max(distributed, 0.0)
                line.with_context(qss_distributing_net_weight=True).write({
                    'product_uom_qty': distributed,
                    'mq_quantity': distributed,
                })

            order._qss_sync_shipping_fee_line()
        return True

    def action_calculate_scale_weight(self):
        """Backward-compatible alias for existing Studio/server actions."""
        return self.action_calculate_net_weight()






























# from odoo import models, fields, api

# class SaleOrderLine(models.Model):
#     """
#     Inherited to handle bundle quantity logic for sale order lines.
#     """
#     _inherit = 'sale.order.line'

#     mq_bundle_qty = fields.Float(string="Bundle Qty", digits='Product Unit of Measure')
#     mq_quantity = fields.Float(string="Quantity", digits='Product Unit of Measure')

#     @api.onchange('mq_bundle_qty', 'product_id')
#     def _onchange_mq_bundle_qty(self):
#         for line in self:
#             if line.product_id and line.product_id.mq_is_bundle_weight:
#                 multiplier = line.product_id.mq_bundle_multiplier or 1.0
#                 line.mq_quantity = line.mq_bundle_qty * multiplier
#                 line.product_uom_qty = line.mq_quantity
#             else:
#                 # Snap back to normal quantity to forbid manual overrides on non-bundles
#                 line.mq_bundle_qty = line.product_uom_qty

#     @api.onchange('mq_quantity', 'product_id')
#     def _onchange_mq_quantity(self):
#         for line in self:
#             line.product_uom_qty = line.mq_quantity
#             if not (line.product_id and line.product_id.mq_is_bundle_weight):
#                 line.mq_bundle_qty = line.mq_quantity

#     @api.onchange('product_uom_qty', 'product_id')
#     def _onchange_product_uom_qty(self):
#         for line in self:
#             if line.product_uom_qty != line.mq_quantity:
#                 line.mq_quantity = line.product_uom_qty
#             if not (line.product_id and line.product_id.mq_is_bundle_weight):
#                 line.mq_bundle_qty = line.product_uom_qty

#     def _prepare_invoice_line(self, **optional_values):
#         res = super(SaleOrderLine, self)._prepare_invoice_line(**optional_values)
#         res['mq_bundle_qty'] = self.mq_bundle_qty
#         res['mq_quantity'] = self.mq_quantity
#         return res

# class SaleOrder(models.Model):
#     """
#     Inherited to compute total bundle quantity and total weight for the order.
#     """
#     _inherit = 'sale.order'

#     mq_scale_net_weight = fields.Float(string="Scale Net Weight")
#     mq_total_bundle_qty = fields.Float(string="Total Bundle Qty", compute="_compute_mq_total_bundle", store=True)
#     mq_total_weight = fields.Float(string="Total Weight (Ton)", compute="_compute_mq_total_weight", store=True)

#     @api.depends('order_line.mq_bundle_qty')
#     def _compute_mq_total_bundle(self):
#         for order in self:
#             order.mq_total_bundle_qty = sum(order.order_line.mapped('mq_bundle_qty'))

#     @api.depends('picking_ids.mq_scale_net_weight', 'picking_ids.state')
#     def _compute_mq_total_weight(self):
#         for order in self:
#             # We sum the scale net weight from related active deliveries
#             valid_pickings = order.picking_ids.filtered(lambda p: p.state != 'cancel')
#             order.mq_total_weight = sum(valid_pickings.mapped('mq_scale_net_weight'))

#     def action_calculate_scale_weight(self):
#         for order in self:
#             if order.mq_scale_net_weight <= 0:
#                 continue
            
#             # Only distribute scale weight to bundled products
#             bundle_lines = order.order_line.filtered(lambda l: l.product_id.mq_is_bundle_weight)
#             total_demand = sum(bundle_lines.mapped('product_uom_qty'))
            
#             if total_demand <= 0:
#                 continue

#             for line in bundle_lines:
#                 if line.product_uom_qty > 0:
#                     distributed_qty = (line.product_uom_qty / total_demand) * order.mq_scale_net_weight
#                     line.product_uom_qty = distributed_qty
#                     line.mq_quantity = distributed_qty


