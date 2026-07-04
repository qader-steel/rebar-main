from odoo import models, fields, api

class StockMove(models.Model):
    """
    Inherited to transfer bundle quantity data from sale orders to delivery stock moves.
    """
    _inherit = 'stock.move'

    mq_bundle_qty = fields.Float(string="Bundle Qty", digits='Product Unit of Measure')
    mq_quantity = fields.Float(string="Quantity", digits='Product Unit of Measure')

    @api.onchange('mq_quantity')
    def _onchange_mq_quantity(self):
        for move in self:
            move.product_uom_qty = move.mq_quantity

    @api.onchange('product_uom_qty')
    def _onchange_product_uom_qty_base(self):
        for move in self:
            if move.product_uom_qty != move.mq_quantity:
                move.mq_quantity = move.product_uom_qty
            if move.product_id and not move.product_id.mq_is_bundle_weight:
                move.mq_bundle_qty = 0.0

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            product = self.env['product.product'].browse(vals.get('product_id'))
            if not product.exists():
                continue
            if not product.mq_is_bundle_weight:
                vals['mq_bundle_qty'] = 0.0
                if 'product_uom_qty' in vals:
                    vals['mq_quantity'] = vals['product_uom_qty']
                continue
            if 'sale_line_id' in vals and vals['sale_line_id']:
                sale_line = self.env['sale.order.line'].browse(vals['sale_line_id'])
                if sale_line.exists():
                    if 'mq_bundle_qty' not in vals or not vals['mq_bundle_qty']:
                        vals['mq_bundle_qty'] = sale_line.mq_bundle_qty
                    if 'mq_quantity' not in vals or not vals['mq_quantity']:
                        vals['mq_quantity'] = sale_line.mq_quantity
            elif 'purchase_line_id' in vals and vals['purchase_line_id']:
                purchase_line = self.env['purchase.order.line'].browse(vals['purchase_line_id'])
                if purchase_line.exists():
                    if 'mq_bundle_qty' not in vals or not vals['mq_bundle_qty']:
                        vals['mq_bundle_qty'] = purchase_line.mq_bundle_qty
                    if 'mq_quantity' not in vals or not vals['mq_quantity']:
                        vals['mq_quantity'] = purchase_line.mq_quantity
        return super().create(vals_list)

    def _get_linked_sale_lines(self):
        sale_lines = self.env['sale.order.line']
        if hasattr(self, 'sale_line_id') and self.sale_line_id:
            sale_lines |= self.sale_line_id
        return sale_lines.filtered(lambda l: l.exists())

    def _get_linked_purchase_lines(self):
        purchase_lines = self.env['purchase.order.line']
        if hasattr(self, 'purchase_line_id') and self.purchase_line_id:
            purchase_lines |= self.purchase_line_id
        return purchase_lines.filtered(lambda l: l.exists())

    def write(self, vals):
        if self.env.context.get('skip_sync'):
            return super().write(vals)
        res = super().write(vals)
        for move in self:
            if move.product_id and not move.product_id.mq_is_bundle_weight:
                if move.mq_bundle_qty != 0.0 or move.mq_quantity != move.product_uom_qty:
                    move.with_context(skip_sync=True).write({
                        'mq_bundle_qty': 0.0,
                        'mq_quantity': move.product_uom_qty,
                    })
        if 'mq_bundle_qty' in vals or 'mq_quantity' in vals:
            for move in self:
                if move.product_id.mq_is_bundle_weight:
                    for so_line in move._get_linked_sale_lines():
                        so_vals = {}
                        if 'mq_bundle_qty' in vals and so_line.mq_bundle_qty != move.mq_bundle_qty:
                            so_vals['mq_bundle_qty'] = move.mq_bundle_qty
                        if 'mq_quantity' in vals and so_line.mq_quantity != move.mq_quantity:
                            so_vals['mq_quantity'] = move.mq_quantity
                        if so_vals:
                            so_line.with_context(skip_sync=True).write(so_vals)
                    for po_line in move._get_linked_purchase_lines():
                        po_vals = {}
                        if 'mq_bundle_qty' in vals and po_line.mq_bundle_qty != move.mq_bundle_qty:
                            po_vals['mq_bundle_qty'] = move.mq_bundle_qty
                        if 'mq_quantity' in vals and po_line.mq_quantity != move.mq_quantity:
                            po_vals['mq_quantity'] = move.mq_quantity
                        if po_vals:
                            po_line.with_context(skip_sync=True).write(po_vals)
        return res


class StockPicking(models.Model):
    """
    Inherited to manage scale net weight distribution and total bundle calculation.
    """
    _inherit = 'stock.picking'

    mq_scale_net_weight = fields.Float(string="Scale Net Weight")
    mq_total_bundle_qty = fields.Float(string="Total Bundle Qty", compute="_compute_mq_total_bundle", store=True)

    @api.depends('move_ids.mq_bundle_qty')
    def _compute_mq_total_bundle(self):
        for picking in self:
            picking.mq_total_bundle_qty = sum(picking.move_ids.mapped('mq_bundle_qty'))

    def action_calculate_scale_weight(self):
        for picking in self:
            if picking.mq_scale_net_weight <= 0:
                continue
            
            # Only distribute scale weight to bundled products
            bundle_moves = picking.move_ids.filtered(lambda m: m.product_id.mq_is_bundle_weight)
            total_demand = sum(bundle_moves.mapped('product_uom_qty'))
            
            if total_demand <= 0:
                continue

            for move in bundle_moves:
                if move.product_uom_qty > 0:
                    distributed_qty = (move.product_uom_qty / total_demand) * picking.mq_scale_net_weight
                    move.quantity = distributed_qty

class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    def _get_aggregated_properties(self, move_line=False, move=False):
        """
        Override to include 'Bundle Qty' in the aggregation key so that lines
        with different bundle quantities are NOT squashed together on the delivery slip.
        """
        properties = super()._get_aggregated_properties(move_line=move_line, move=move)
        
        m = move or (move_line and move_line.move_id)
        if m and getattr(m, 'mq_bundle_qty', False):
            # Append bundle qty to uniquely separate these rows on the printed report
            properties['line_key'] += f"_{m.mq_bundle_qty}"
            
        return properties
