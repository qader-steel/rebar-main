from odoo import models, fields, api

class SaleOrderLine(models.Model):
    """
    Inherited to handle bundle quantity logic for sale order lines.
    """
    _inherit = 'sale.order.line'

    mq_bundle_qty = fields.Float(string="Bundle Qty", digits='Product Unit of Measure')
    mq_quantity = fields.Float(string="Quantity", digits='Product Unit of Measure')

    # ------------------------------------------------------------------
    # For non-bundle lines, mq_bundle_qty must always equal product_uom_qty.
    # @api.onchange handles UI edits, but server-side writes (automation,
    # import, the Full Cycle button) skip onchange entirely.  The @api.depends
    # method below keeps the two fields in sync no matter how the qty changes.
    # For bundle products we leave mq_bundle_qty untouched here because the
    # user enters it in "bundles" and the onchange drives product_uom_qty via
    # the bundle-multiplier formula — overwriting it from depends would break
    # that direction.
    # ------------------------------------------------------------------
    @api.depends('product_uom_qty', 'product_id', 'product_id.mq_is_bundle_weight')
    def _sync_bundle_qty_non_bundle(self):
        for line in self:
            if not (line.product_id and line.product_id.mq_is_bundle_weight):
                if line.mq_bundle_qty != line.product_uom_qty:
                    line.mq_bundle_qty = line.product_uom_qty

    @api.onchange('mq_bundle_qty', 'product_id')
    def _onchange_mq_bundle_qty(self):
        for line in self:
            if line.product_id and line.product_id.mq_is_bundle_weight:
                multiplier = line.product_id.mq_bundle_multiplier or 1.0
                line.mq_quantity = line.mq_bundle_qty * multiplier
                line.product_uom_qty = line.mq_quantity
            else:
                # Snap back to normal quantity to forbid manual overrides on non-bundles
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
        string="Scale Net Weight",
        compute="_compute_mq_scale_net_weight",
        store=True,
    )
    mq_total_bundle_qty = fields.Float(string="Total Bundle Qty", compute="_compute_mq_total_bundle", store=True)
    mq_total_weight = fields.Float(string="Total Weight (Ton)", compute="_compute_mq_total_weight", store=True)

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


