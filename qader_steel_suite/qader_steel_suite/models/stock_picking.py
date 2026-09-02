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

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'sale_line_id' in vals and vals['sale_line_id']:
                sale_line = self.env['sale.order.line'].browse(vals['sale_line_id'])
                if sale_line.exists() and False not in (sale_line.mq_bundle_qty, sale_line.mq_quantity):
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
        return super(StockMove, self).create(vals_list)


class StockPicking(models.Model):
    """
    Inherited to manage scale net weight distribution and total bundle calculation.
    """
    _inherit = 'stock.picking'

    mq_scale_net_weight = fields.Float(
        string="Scale Net Weight",
        compute="_compute_mq_scale_net_weight",
        store=True,
        readonly=False
    )
    mq_total_bundle_qty = fields.Float(string="Total Bundle Qty", compute="_compute_mq_total_bundle", store=True)

    @api.depends('sale_id.mq_scale_net_weight', 'purchase_id.mq_scale_net_weight')
    def _compute_mq_scale_net_weight(self):
        for picking in self:
            if picking.sale_id:
                picking.mq_scale_net_weight = picking.sale_id.mq_scale_net_weight
            elif picking.purchase_id:
                picking.mq_scale_net_weight = picking.purchase_id.mq_scale_net_weight
            else:
                if not picking.mq_scale_net_weight:
                    picking.mq_scale_net_weight = 0.0


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

    def button_validate(self):
        res = super(StockPicking, self).button_validate()
        if isinstance(res, dict) and res.get('res_model') == 'stock.backorder.confirmation':
            wizard = self.env['stock.backorder.confirmation'].browse(res.get('res_id'))
            return wizard.process_cancel_backorder()
        return res


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
