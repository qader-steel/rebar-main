from odoo import api, fields, models

# --- History Dictionary Models ---
class MQDriverName(models.Model):
    _name = "mq.driver.name"
    _description = "Driver Name History"
    name = fields.Char(string="Driver Name", required=True)

class MQDriverPhone(models.Model):
    _name = "mq.driver.phone"
    _description = "Driver Phone History"
    name = fields.Char(string="Phone Number", required=True)

class MQCarPlate(models.Model):
    _name = "mq.car.plate"
    _description = "Car Plate History"
    name = fields.Char(string="Car Plate No", required=True)

class MQBorderCrossing(models.Model):
    _name = "mq.border.crossing"
    _description = "Border Crossing History"
    name = fields.Char(string="Border Crossing", required=True)

class MQScaleNo(models.Model):
    _name = "mq.scale.no"
    _description = "Scale No History"
    name = fields.Char(string="Scale No", required=True)


# --- Document Models ---
class SaleOrder(models.Model):
    _inherit = "sale.order"

    driver_name_id = fields.Many2one("mq.driver.name", string="Driver Name")
    driver_phone_id = fields.Many2one("mq.driver.phone", string="Driver Phone No")
    car_plate_id = fields.Many2one("mq.car.plate", string="Car Plate No")
    border_crossing_id = fields.Many2one("mq.border.crossing", string="Border Crossing")
    scale_no_id = fields.Many2one("mq.scale.no", string="Scale No")

    def _get_linked_dropship_pos(self):
        """Return dropship POs linked via stock.move sale_line_id → purchase_line_id.
        This is the same mechanic used by mq_bundle_wieghing_calculator."""
        self.ensure_one()
        so_line_ids = self.order_line.ids
        if not so_line_ids:
            return self.env['purchase.order']
        moves = self.env['stock.move'].search([('sale_line_id', 'in', so_line_ids)])
        po_lines = moves.mapped('purchase_line_id').filtered(lambda l: l.exists())
        return po_lines.mapped('order_id')

    def action_confirm(self):
        res = super().action_confirm()
        # Push driver info to newly created dropship POs after confirmation
        driver_fields = ['driver_name_id', 'driver_phone_id', 'car_plate_id', 'border_crossing_id', 'scale_no_id']
        for order in self:
            if any(order[f] for f in driver_fields):
                purchase_orders = order._get_linked_dropship_pos()
                if purchase_orders:
                    purchase_orders.with_context(skip_driver_sync=True).write({
                        f: order[f].id if order[f] else False for f in driver_fields
                    })
        return res

    def write(self, vals):
        if self.env.context.get('skip_driver_sync'):
            return super().write(vals)
        res = super().write(vals)
        driver_fields = ['driver_name_id', 'driver_phone_id', 'car_plate_id', 'border_crossing_id', 'scale_no_id']
        if any(f in vals for f in driver_fields):
            for order in self:
                purchase_orders = order._get_linked_dropship_pos()
                if purchase_orders:
                    po_vals = {f: order[f].id if order[f] else False for f in driver_fields if f in vals}
                    purchase_orders.with_context(skip_driver_sync=True).write(po_vals)
        return res


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    driver_name_id = fields.Many2one("mq.driver.name", string="Driver Name")
    driver_phone_id = fields.Many2one("mq.driver.phone", string="Driver Phone No")
    car_plate_id = fields.Many2one("mq.car.plate", string="Car Plate No")
    border_crossing_id = fields.Many2one("mq.border.crossing", string="Border Crossing")
    scale_no_id = fields.Many2one("mq.scale.no", string="Scale No")

    def _get_linked_sale_orders(self):
        """Return sale orders linked via stock.move purchase_line_id → sale_line_id.
        This is the same mechanic used by mq_bundle_wieghing_calculator."""
        self.ensure_one()
        po_line_ids = self.order_line.ids
        if not po_line_ids:
            return self.env['sale.order']
        moves = self.env['stock.move'].search([('purchase_line_id', 'in', po_line_ids)])
        so_lines = moves.mapped('sale_line_id').filtered(lambda l: l.exists())
        return so_lines.mapped('order_id')

    def write(self, vals):
        if self.env.context.get('skip_driver_sync'):
            return super().write(vals)
        res = super().write(vals)
        driver_fields = ['driver_name_id', 'driver_phone_id', 'car_plate_id', 'border_crossing_id', 'scale_no_id']
        if any(f in vals for f in driver_fields):
            for order in self:
                sale_orders = order._get_linked_sale_orders()
                if sale_orders:
                    so_vals = {f: order[f].id if order[f] else False for f in driver_fields if f in vals}
                    sale_orders.with_context(skip_driver_sync=True).write(so_vals)
        return res




class StockPicking(models.Model):
    _inherit = "stock.picking"

    # Delivery inherits from Sale Order or Purchase Order
    driver_name_id = fields.Many2one("mq.driver.name", string="Driver Name", compute="_compute_driver_info", inverse="_inverse_driver_info", store=True, readonly=False)
    driver_phone_id = fields.Many2one("mq.driver.phone", string="Driver Phone No", compute="_compute_driver_info", inverse="_inverse_driver_info", store=True, readonly=False)
    car_plate_id = fields.Many2one("mq.car.plate", string="Car Plate No", compute="_compute_driver_info", inverse="_inverse_driver_info", store=True, readonly=False)
    border_crossing_id = fields.Many2one("mq.border.crossing", string="Border Crossing", compute="_compute_driver_info", inverse="_inverse_driver_info", store=True, readonly=False)
    scale_no_id = fields.Many2one("mq.scale.no", string="Scale No", compute="_compute_driver_info", inverse="_inverse_driver_info", store=True, readonly=False)

    @api.depends('sale_id.driver_name_id', 'purchase_id.driver_name_id', 
                'sale_id.driver_phone_id', 'purchase_id.driver_phone_id',
                'sale_id.car_plate_id', 'purchase_id.car_plate_id',
                'sale_id.border_crossing_id', 'purchase_id.border_crossing_id',
                'sale_id.scale_no_id', 'purchase_id.scale_no_id')
    def _compute_driver_info(self):
        for picking in self:
            source = picking.sale_id or picking.purchase_id
            if source:
                picking.driver_name_id = source.driver_name_id
                picking.driver_phone_id = source.driver_phone_id
                picking.car_plate_id = source.car_plate_id
                picking.border_crossing_id = source.border_crossing_id
                picking.scale_no_id = source.scale_no_id
            else:
                pass

    def _inverse_driver_info(self):
        """Propagate changes back to the source order so invoices stay in sync."""
        for picking in self:
            source = picking.sale_id or picking.purchase_id
            if source:
                source.driver_name_id = picking.driver_name_id
                source.driver_phone_id = picking.driver_phone_id
                source.car_plate_id = picking.car_plate_id
                source.border_crossing_id = picking.border_crossing_id
                source.scale_no_id = picking.scale_no_id

    def _action_done(self):
        """Automatically create an invoice when a delivery order is validated."""
        res = super()._action_done()
        for picking in self:
            # We only generate an invoice automatically for outgoing deliveries linked to a Sale Order
            if picking.sale_id and picking.picking_type_id.code == 'outgoing':
                # Check if there are any lines ready to be invoiced (e.g. based on delivered quantities)
                invoiceable_lines = picking.sale_id.order_line.filtered(lambda l: l.qty_to_invoice > 0)
                if invoiceable_lines:
                    try:
                        picking.sale_id._create_invoices()
                    except Exception:
                        pass
        return res


class AccountMove(models.Model):
    _inherit = "account.move"

    sale_order_ids = fields.Many2many(
        comodel_name="sale.order",
        compute="_compute_order_ids",
        string="Related Sales Orders"
    )
    
    sale_order_id = fields.Many2one(
        comodel_name="sale.order",
        compute="_compute_order_ids",
        store=True,
        string="Source Sales Order",
    )

    purchase_order_ids = fields.Many2many(
        comodel_name="purchase.order",
        compute="_compute_order_ids",
        string="Related Purchase Orders"
    )

    purchase_order_id = fields.Many2one(
        comodel_name="purchase.order",
        compute="_compute_order_ids",
        store=True,
        string="Source Purchase Order",
    )

    # Invoice inherits from Sale Order or Purchase Order
    driver_name_id = fields.Many2one("mq.driver.name", string="Driver Name", compute="_compute_driver_info", inverse="_inverse_driver_info", store=True, readonly=False)
    driver_phone_id = fields.Many2one("mq.driver.phone", string="Driver Phone No", compute="_compute_driver_info", inverse="_inverse_driver_info", store=True, readonly=False)
    car_plate_id = fields.Many2one("mq.car.plate", string="Car Plate No", compute="_compute_driver_info", inverse="_inverse_driver_info", store=True, readonly=False)
    border_crossing_id = fields.Many2one("mq.border.crossing", string="Border Crossing", compute="_compute_driver_info", inverse="_inverse_driver_info", store=True, readonly=False)
    scale_no_id = fields.Many2one("mq.scale.no", string="Scale No", compute="_compute_driver_info", inverse="_inverse_driver_info", store=True, readonly=False)

    @api.depends("invoice_line_ids.sale_line_ids.order_id", "invoice_line_ids.purchase_line_id.order_id")
    def _compute_order_ids(self):
        for move in self:
            sales = move.invoice_line_ids.mapped('sale_line_ids.order_id')
            move.sale_order_ids = sales
            move.sale_order_id = sales[0] if sales else False

            purchases = move.invoice_line_ids.mapped('purchase_line_id.order_id')
            move.purchase_order_ids = purchases
            move.purchase_order_id = purchases[0] if purchases else False

    @api.depends('sale_order_id.driver_name_id', 'purchase_order_id.driver_name_id',
                'sale_order_id.driver_phone_id', 'purchase_order_id.driver_phone_id',
                'sale_order_id.car_plate_id', 'purchase_order_id.car_plate_id',
                'sale_order_id.border_crossing_id', 'purchase_order_id.border_crossing_id',
                'sale_order_id.scale_no_id', 'purchase_order_id.scale_no_id')
    def _compute_driver_info(self):
        for move in self:
            source = move.sale_order_id or move.purchase_order_id
            if source:
                move.driver_name_id = source.driver_name_id
                move.driver_phone_id = source.driver_phone_id
                move.car_plate_id = source.car_plate_id
                move.border_crossing_id = source.border_crossing_id
                move.scale_no_id = source.scale_no_id
            else:
                pass

    def _inverse_driver_info(self):
        """Propagate changes back to the source order to keep documents in sync."""
        for move in self:
            source = move.sale_order_id or move.purchase_order_id
            if source:
                source.driver_name_id = move.driver_name_id
                source.driver_phone_id = move.driver_phone_id
                source.car_plate_id = move.car_plate_id
                source.border_crossing_id = move.border_crossing_id
                source.scale_no_id = move.scale_no_id
