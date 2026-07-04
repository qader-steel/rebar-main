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
                line.mq_bundle_qty = 0.0

    @api.onchange('mq_quantity', 'product_id')
    def _onchange_mq_quantity(self):
        for line in self:
            line.product_qty = line.mq_quantity

    @api.onchange('product_qty', 'product_id')
    def _onchange_product_qty(self):
        for line in self:
            if line.product_qty != line.mq_quantity:
                line.mq_quantity = line.product_qty
            if line.product_id and not line.product_id.mq_is_bundle_weight:
                line.mq_bundle_qty = 0.0

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

    def _get_linked_sale_lines(self):
        sale_lines = self.env['sale.order.line']
        if hasattr(self, 'sale_line_id') and self.sale_line_id:
            sale_lines |= self.sale_line_id
        if hasattr(self, 'move_ids') and self.move_ids:
            sale_lines |= self.move_ids.mapped('sale_line_id')
        return sale_lines.filtered(lambda l: l.exists())

    def _get_linked_moves(self):
        moves = self.env['stock.move']
        if hasattr(self, 'move_ids') and self.move_ids:
            moves |= self.move_ids
        return moves.filtered(lambda m: m.exists())

    def write(self, vals):
        if self.env.context.get('skip_sync'):
            return super().write(vals)
        res = super().write(vals)
        for line in self:
            if line.product_id and not line.product_id.mq_is_bundle_weight:
                if line.mq_bundle_qty != 0.0 or line.mq_quantity != line.product_qty:
                    line.with_context(skip_sync=True).write({
                        'mq_bundle_qty': 0.0,
                        'mq_quantity': line.product_qty,
                    })
        if 'mq_bundle_qty' in vals or 'mq_quantity' in vals:
            for line in self:
                if line.product_id.mq_is_bundle_weight:
                    for so_line in line._get_linked_sale_lines():
                        so_vals = {}
                        if 'mq_bundle_qty' in vals and so_line.mq_bundle_qty != line.mq_bundle_qty:
                            so_vals['mq_bundle_qty'] = line.mq_bundle_qty
                        if 'mq_quantity' in vals and so_line.mq_quantity != line.mq_quantity:
                            so_vals['mq_quantity'] = line.mq_quantity
                        if so_vals:
                            so_line.with_context(skip_sync=True).write(so_vals)
                    for move in line._get_linked_moves():
                        move_vals = {}
                        if 'mq_bundle_qty' in vals and move.mq_bundle_qty != line.mq_bundle_qty:
                            move_vals['mq_bundle_qty'] = line.mq_bundle_qty
                        if 'mq_quantity' in vals and move.mq_quantity != line.mq_quantity:
                            move_vals['mq_quantity'] = line.mq_quantity
                        if move_vals:
                            move.with_context(skip_sync=True).write(move_vals)
        return res

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            product = self.env['product.product'].browse(vals.get('product_id'))
            if product.exists() and not product.mq_is_bundle_weight:
                vals['mq_bundle_qty'] = 0.0
                if 'product_qty' in vals:
                    vals['mq_quantity'] = vals['product_qty']
        lines = super().create(vals_list)
        for line in lines:
            if line.product_id.mq_is_bundle_weight:
                if not line.mq_bundle_qty or not line.mq_quantity:
                    so_lines = line._get_linked_sale_lines()
                    if so_lines:
                        line.write({
                            'mq_bundle_qty': so_lines[0].mq_bundle_qty,
                            'mq_quantity': so_lines[0].mq_quantity,
                        })
        return lines

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
