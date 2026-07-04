from odoo import models, fields, api

class SaleOrderLine(models.Model):
    """
    Inherited to handle bundle quantity logic for sale order lines.
    """
    _inherit = 'sale.order.line'

    mq_bundle_qty = fields.Float(string="Bundle Qty", digits='Product Unit of Measure')
    mq_quantity = fields.Float(string="Quantity", digits='Product Unit of Measure')

    @api.onchange('mq_bundle_qty', 'product_id')
    def _onchange_mq_bundle_qty(self):
        for line in self:
            if line.product_id and line.product_id.mq_is_bundle_weight:
                multiplier = line.product_id.mq_bundle_multiplier or 1.0
                line.mq_quantity = line.mq_bundle_qty * multiplier
                line.product_uom_qty = line.mq_quantity
            else:
                line.mq_bundle_qty = 0.0

    @api.onchange('mq_quantity', 'product_id')
    def _onchange_mq_quantity(self):
        for line in self:
            line.product_uom_qty = line.mq_quantity

    @api.onchange('product_uom_qty', 'product_id')
    def _onchange_product_uom_qty(self):
        for line in self:
            if line.product_uom_qty != line.mq_quantity:
                line.mq_quantity = line.product_uom_qty
            if line.product_id and not line.product_id.mq_is_bundle_weight:
                line.mq_bundle_qty = 0.0

    def _prepare_invoice_line(self, **optional_values):
        res = super(SaleOrderLine, self)._prepare_invoice_line(**optional_values)
        res['mq_bundle_qty'] = self.mq_bundle_qty
        res['mq_quantity'] = self.mq_quantity
        return res

    def _get_linked_purchase_lines(self):
        purchase_lines = self.env['purchase.order.line']
        if hasattr(self, 'purchase_line_ids') and self.purchase_line_ids:
            purchase_lines |= self.purchase_line_ids
        moves = self.env['stock.move'].search([('sale_line_id', 'in', self.ids)])
        if moves:
            purchase_lines |= moves.mapped('purchase_line_id')
        return purchase_lines.filtered(lambda l: l.exists())

    def _get_linked_moves(self):
        moves = self.env['stock.move']
        if hasattr(self, 'move_ids') and self.move_ids:
            moves |= self.move_ids
        extra_moves = self.env['stock.move'].search([('sale_line_id', 'in', self.ids)])
        if extra_moves:
            moves |= extra_moves
        return moves.filtered(lambda m: m.exists())

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            product = self.env['product.product'].browse(vals.get('product_id'))
            if product.exists() and not product.mq_is_bundle_weight:
                vals['mq_bundle_qty'] = 0.0
                if 'product_uom_qty' in vals:
                    vals['mq_quantity'] = vals['product_uom_qty']
        return super().create(vals_list)

    def write(self, vals):
        if self.env.context.get('skip_sync'):
            return super().write(vals)
        res = super().write(vals)
        for line in self:
            if line.product_id and not line.product_id.mq_is_bundle_weight:
                if line.mq_bundle_qty != 0.0 or line.mq_quantity != line.product_uom_qty:
                    line.with_context(skip_sync=True).write({
                        'mq_bundle_qty': 0.0,
                        'mq_quantity': line.product_uom_qty,
                    })
        if 'mq_bundle_qty' in vals or 'mq_quantity' in vals:
            for line in self:
                if line.product_id.mq_is_bundle_weight:
                    for po_line in line._get_linked_purchase_lines():
                        po_vals = {}
                        if 'mq_bundle_qty' in vals and po_line.mq_bundle_qty != line.mq_bundle_qty:
                            po_vals['mq_bundle_qty'] = line.mq_bundle_qty
                        if 'mq_quantity' in vals and po_line.mq_quantity != line.mq_quantity:
                            po_vals['mq_quantity'] = line.mq_quantity
                        if po_vals:
                            po_line.with_context(skip_sync=True).write(po_vals)
                    for move in line._get_linked_moves():
                        move_vals = {}
                        if 'mq_bundle_qty' in vals and move.mq_bundle_qty != line.mq_bundle_qty:
                            move_vals['mq_bundle_qty'] = line.mq_bundle_qty
                        if 'mq_quantity' in vals and move.mq_quantity != line.mq_quantity:
                            move_vals['mq_quantity'] = line.mq_quantity
                        if move_vals:
                            move.with_context(skip_sync=True).write(move_vals)
        return res

class SaleOrder(models.Model):
    """
    Inherited to compute total bundle quantity and total weight for the order.
    """
    _inherit = 'sale.order'

    mq_total_bundle_qty = fields.Float(string="Total Bundle Qty", compute="_compute_mq_total_bundle", store=True)
    mq_total_weight = fields.Float(string="Total Weight (Ton)", compute="_compute_mq_total_weight", store=True)

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
