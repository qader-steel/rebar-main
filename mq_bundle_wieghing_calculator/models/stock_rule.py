from odoo import models


class StockRule(models.Model):
    """
    Inherited to propagate bundle quantity fields from sale order lines
    to purchase order lines created via dropshipping procurement.
    """
    _inherit = 'stock.rule'

    def _get_sale_line_from_values(self, values, product_id=False):
        # Debug logging to a file in the workspace
        try:
            with open(r"c:\Users\elysi\OneDrive\Desktop\Operation-2\mqt-19\mq_bundle_wieghing_calculator\procurement.log", "a") as f:
                f.write(f"VALUES: {repr(values)}\n")
        except Exception:
            pass

        sale_line = self.env['sale.order.line']
        sale_line_id = values.get('sale_line_id')
        if sale_line_id:
            sale_line = self.env['sale.order.line'].browse(sale_line_id)
        
        if not sale_line or not sale_line.exists():
            if values.get('move_dest_ids'):
                moves = self.env['stock.move'].browse(values.get('move_dest_ids'))
                sale_lines = moves.mapped('sale_line_id')
                if sale_lines:
                    sale_line = sale_lines[0]

        if not sale_line or not sale_line.exists():
            if values.get('group_id'):
                group = self.env['procurement.group'].browse(values.get('group_id'))
                if group.exists():
                    sale_order = self.env['sale.order'].search([('procurement_group_id', '=', group.id)], limit=1)
                    if not sale_order and hasattr(group, 'sale_id') and group.sale_id:
                        sale_order = group.sale_id
                    if sale_order and product_id:
                        prod_id = product_id.id if isinstance(product_id, models.BaseModel) else product_id
                        sale_line = sale_order.order_line.filtered(lambda l: l.product_id.id == prod_id)[:1]

        return sale_line if sale_line.exists() else False

    def _prepare_purchase_order_line(self, product_id, product_qty, product_uom, company_id, values, po):
        res = super()._prepare_purchase_order_line(product_id, product_qty, product_uom, company_id, values, po)
        sale_line = self._get_sale_line_from_values(values, product_id)
        if sale_line and sale_line.product_id.mq_is_bundle_weight:
            res['mq_bundle_qty'] = sale_line.mq_bundle_qty
            res['mq_quantity'] = sale_line.mq_quantity
        return res

    def _update_purchase_order_line(self, product_id, product_qty, product_uom, company_id, values, po_line):
        res = super()._update_purchase_order_line(product_id, product_qty, product_uom, company_id, values, po_line)
        if not res:
            res = {}
        sale_line = self._get_sale_line_from_values(values, product_id)
        if sale_line and sale_line.product_id.mq_is_bundle_weight:
            res['mq_bundle_qty'] = sale_line.mq_bundle_qty
            res['mq_quantity'] = sale_line.mq_quantity
        return res

    def _make_po_get_domain(self, company_id, values, partner):
        domain = super()._make_po_get_domain(company_id, values, partner)
        group_id = values.get('group_id')
        if group_id:
            partner_id = partner.id if isinstance(partner, models.BaseModel) else partner
            existing_po = self.env['purchase.order'].search([
                ('group_id', '=', group_id),
                ('partner_id', '=', partner_id),
                ('state', 'in', ('draft', 'sent'))
            ], limit=1)
            if existing_po:
                domain = [('id', '=', existing_po.id)]
        return domain
