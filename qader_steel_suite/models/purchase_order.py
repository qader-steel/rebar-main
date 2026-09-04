from odoo import models, fields, api

class PurchaseOrderLine(models.Model):
    """
    Inherited to handle bundle quantity logic for purchase order lines.
    """
    _inherit = 'purchase.order.line'

    mq_bundle_qty = fields.Float(string="كمية الحزم", digits='Product Unit of Measure')
    mq_quantity = fields.Float(string="الكمية", digits='Product Unit of Measure')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'sale_line_id' in vals and vals['sale_line_id']:
                sale_line = self.env['sale.order.line'].browse(vals['sale_line_id'])
                if sale_line.exists():
                    if 'mq_bundle_qty' not in vals or not vals['mq_bundle_qty']:
                        vals['mq_bundle_qty'] = sale_line.mq_bundle_qty
                    if 'mq_quantity' not in vals or not vals['mq_quantity']:
                        vals['mq_quantity'] = sale_line.mq_quantity
        return super(PurchaseOrderLine, self).create(vals_list)


    @api.onchange('mq_bundle_qty', 'product_id')
    def _onchange_mq_bundle_qty(self):
        for line in self:
            if line.product_id and line.product_id.mq_is_bundle_weight:
                multiplier = line.product_id.mq_bundle_multiplier or 1.0
                line.mq_quantity = line.mq_bundle_qty * multiplier
                line.product_qty = line.mq_quantity
            else:
                # Snap back to normal quantity to forbid manual overrides on non-bundles
                line.mq_bundle_qty = line.product_qty

    @api.onchange('mq_quantity', 'product_id')
    def _onchange_mq_quantity(self):
        for line in self:
            line.product_qty = line.mq_quantity
            if not (line.product_id and line.product_id.mq_is_bundle_weight):
                line.mq_bundle_qty = line.mq_quantity

    @api.onchange('product_qty', 'product_id')
    def _onchange_product_qty(self):
        for line in self:
            if line.product_qty != line.mq_quantity:
                line.mq_quantity = line.product_qty
            if not (line.product_id and line.product_id.mq_is_bundle_weight):
                line.mq_bundle_qty = line.product_qty

    def _prepare_account_move_line(self, move=False):
        res = super()._prepare_account_move_line(move=move)
        res['mq_bundle_qty'] = self.mq_bundle_qty
        res['mq_quantity'] = self.mq_quantity
        return res

    def _prepare_stock_move_vals(self, picking, price_unit, product_uom_qty, product_uom):
        res = super()._prepare_stock_move_vals(picking, price_unit, product_uom_qty, product_uom)
        res['mq_bundle_qty'] = self.mq_bundle_qty
        res['mq_quantity'] = self.mq_quantity
        return res

class PurchaseOrder(models.Model):
    """
    Inherited to compute total bundle quantity and total weight for the purchase order.
    """
    _inherit = 'purchase.order'

    mq_scale_net_weight = fields.Float(
        string="صافي وزن الميزان",
        compute="_compute_mq_scale_net_weight",
        store=True,
        readonly=False
    )
    mq_total_bundle_qty = fields.Float(string="إجمالي كمية الحزم", compute="_compute_mq_total_bundle", store=True)
    mq_total_weight = fields.Float(string="إجمالي الوزن (طن)", compute="_compute_mq_total_weight", store=True)

    @api.depends('order_line.sale_line_id.order_id.mq_scale_net_weight')
    def _compute_mq_scale_net_weight(self):
        for order in self:
            sale_orders = order.order_line.mapped('sale_line_id.order_id')
            if sale_orders:
                order.mq_scale_net_weight = sale_orders[0].mq_scale_net_weight
            else:
                if not order.mq_scale_net_weight:
                    order.mq_scale_net_weight = 0.0


    @api.depends('order_line.mq_bundle_qty')
    def _compute_mq_total_bundle(self):
        for order in self:
            order.mq_total_bundle_qty = sum(order.order_line.mapped('mq_bundle_qty'))

    @api.depends('picking_ids.mq_scale_net_weight', 'picking_ids.state')
    def _compute_mq_total_weight(self):
        for order in self:
            # We sum the scale net weight from related active receipts (Incoming Shipments)
            valid_pickings = order.picking_ids.filtered(lambda p: p.state != 'cancel')
            order.mq_total_weight = sum(valid_pickings.mapped('mq_scale_net_weight'))

    def action_calculate_scale_weight(self):
        for order in self:
            if order.mq_scale_net_weight <= 0:
                continue
            
            # Only distribute scale weight to bundled products
            bundle_lines = order.order_line.filtered(lambda l: l.product_id.mq_is_bundle_weight)
            total_demand = sum(bundle_lines.mapped('product_qty'))
            
            if total_demand <= 0:
                continue

            for line in bundle_lines:
                if line.product_qty > 0:
                    distributed_qty = (line.product_qty / total_demand) * order.mq_scale_net_weight
                    line.product_qty = distributed_qty
                    line.mq_quantity = distributed_qty


class StockRule(models.Model):
    _inherit = 'stock.rule'

    def _prepare_purchase_order_line(self, product_id, product_qty, product_uom, company_id, values, po):
        res = super()._prepare_purchase_order_line(product_id, product_qty, product_uom, company_id, values, po)
        if values.get('sale_line_id'):
            sale_line = self.env['sale.order.line'].browse(values['sale_line_id'])
            if sale_line.exists():
                res['mq_bundle_qty'] = sale_line.mq_bundle_qty
                res['mq_quantity'] = sale_line.mq_quantity
        return res