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


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    driver_name_id = fields.Many2one("mq.driver.name", string="Driver Name")
    driver_phone_id = fields.Many2one("mq.driver.phone", string="Driver Phone No")
    car_plate_id = fields.Many2one("mq.car.plate", string="Car Plate No")
    border_crossing_id = fields.Many2one("mq.border.crossing", string="Border Crossing")
    scale_no_id = fields.Many2one("mq.scale.no", string="Scale No")


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
