import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class PurchaseRequisition(models.Model):
    """Bulk-populate a Purchase Requisition (Purchase Agreement) with one
    line per purchasable product, at a flat per-ton price.

    NOTE: the field is kept under its original Studio technical name
    (``x_studio_price_ton``) on purpose, so any existing Studio view,
    filter or automation that already references it keeps working once
    this field becomes a "real" module field instead of a Studio-only one.
    """
    _inherit = 'purchase.requisition'

    x_studio_price_ton = fields.Float(string="Price (Ton)")

    def action_populate_all_products(self):
        """Add one requisition line per purchasable, non-service product,
        at quantity 100 and the per-ton price set on the requisition.

        Only acts on requisitions that don't already have lines, so it's
        safe to run more than once or on a bulk selection.

        IMPORTANT: this pulls in *every* purchasable, non-service product
        in the database - there is no category/vendor filter, exactly as
        in the original code. If only a specific subset of products
        should be quoted on this requisition, add a domain below (e.g.
        restrict to a product category) before using this in production.
        """
        Product = self.env['product.product']
        for requisition in self:
            if requisition.line_ids:
                continue
            unit_price = requisition.x_studio_price_ton or 0.0
            products = Product.search([
                ('purchase_ok', '=', True),
                ('type', '!=', 'service'),
            ])
            if not products:
                continue
            requisition.write({
                'line_ids': [
                    (0, 0, {
                        'product_id': product.id,
                        'product_qty': 100.0,
                        'price_unit': unit_price,
                    })
                    for product in products
                ],
            })
            _logger.info(
                "qader_steel_suite: populated %s requisition line(s) on "
                "%s at %.2f/ton",
                len(products), requisition.display_name, unit_price,
            )
