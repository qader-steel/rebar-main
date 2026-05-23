from odoo import models, fields, api

class PurchaseOrderLine(models.Model):
    """
    Inherited to handle bundle quantity logic for purchase order lines.
    """
    _inherit = 'purchase.order.line'

    mq_bundle_qty = fields.Float(string="Bundle Qty", digits='Product Unit of Measure')
    mq_quantity = fields.Float(string="Quantity", digits='Product Unit of Measure')

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

    mq_total_bundle_qty = fields.Float(string="Total Bundle Qty", compute="_compute_mq_total_bundle", store=True)
    mq_total_weight = fields.Float(string="Total Weight (Ton)", compute="_compute_mq_total_weight", store=True)

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
