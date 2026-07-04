from odoo import models, fields, api

class AccountMoveLine(models.Model):
    """
    Inherited to handle bundle quantities and delivered quantity computation in invoices.
    """
    _inherit = 'account.move.line'

    mq_bundle_qty = fields.Float(string="Bundle Qty", digits='Product Unit of Measure')
    mq_quantity = fields.Float(string="Quantity", digits='Product Unit of Measure')

    @api.onchange('mq_quantity')
    def _onchange_mq_quantity(self):
        for line in self:
            line.quantity = line.mq_quantity
            if line.product_id and not line.product_id.mq_is_bundle_weight:
                line.mq_bundle_qty = 0.0

    @api.onchange('quantity')
    def _onchange_quantity_base(self):
        for line in self:
            if line.quantity != line.mq_quantity:
                line.mq_quantity = line.quantity
            if line.product_id and not line.product_id.mq_is_bundle_weight:
                line.mq_bundle_qty = 0.0

    mq_qty_delivered = fields.Float(string="Delivered", compute="_compute_mq_qty_delivered", digits='Product Unit of Measure')

    @api.depends('sale_line_ids.qty_delivered')
    def _compute_mq_qty_delivered(self):
        for line in self:
            line.mq_qty_delivered = sum(line.sale_line_ids.mapped('qty_delivered')) if line.sale_line_ids else 0.0

    mq_qty_received = fields.Float(string="Received", compute="_compute_mq_qty_received", digits='Product Unit of Measure')

    @api.depends('purchase_line_id.qty_received')
    def _compute_mq_qty_received(self):
        for line in self:
            line.mq_qty_received = line.purchase_line_id.qty_received if line.purchase_line_id else 0.0

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            product = self.env['product.product'].browse(vals.get('product_id'))
            if product.exists() and not product.mq_is_bundle_weight:
                vals['mq_bundle_qty'] = 0.0
                if 'quantity' in vals:
                    vals['mq_quantity'] = vals['quantity']
        return super().create(vals_list)

    def write(self, vals):
        if self.env.context.get('skip_sync'):
            return super().write(vals)
        res = super().write(vals)
        for line in self:
            if line.product_id and not line.product_id.mq_is_bundle_weight:
                if line.mq_bundle_qty != 0.0 or line.mq_quantity != line.quantity:
                    line.with_context(skip_sync=True).write({
                        'mq_bundle_qty': 0.0,
                        'mq_quantity': line.quantity,
                    })
        return res

class AccountMove(models.Model):
    """
    Inherited to compute total bundle quantity and total weight for invoices/bills.
    """
    _inherit = 'account.move'

    mq_total_bundle_qty = fields.Float(string="Total Bundle Qty", compute="_compute_mq_totals", store=True)
    mq_total_weight = fields.Float(string="Total Weight (Ton)", compute="_compute_mq_totals", store=True)

    @api.depends('invoice_line_ids.mq_bundle_qty', 'invoice_line_ids.sale_line_ids', 'invoice_line_ids.purchase_line_id')
    def _compute_mq_totals(self):
        for move in self:
            total_bundle = sum(move.invoice_line_ids.mapped('mq_bundle_qty'))
            
            # Fetch total weight from associated sale or purchase orders
            total_weight = 0.0
            sale_orders = move.invoice_line_ids.mapped('sale_line_ids.order_id')
            if sale_orders:
                total_weight = sum(sale_orders.mapped('mq_total_weight'))
            else:
                purchase_orders = move.invoice_line_ids.mapped('purchase_line_id.order_id')
                if purchase_orders:
                    total_weight = sum(purchase_orders.mapped('mq_total_weight'))

            move.mq_total_bundle_qty = total_bundle
            move.mq_total_weight = total_weight
