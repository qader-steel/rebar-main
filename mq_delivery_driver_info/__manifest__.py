{
    "name": "MQ Delivery Driver Info",
    "version": "19.0.1.0.0",
    "depends": ["sale", "sale_stock", "stock", "account", "purchase"],
    "data": [
        "security/ir.model.access.csv",
        "views/mq_delivery_driver_info_views.xml",
        "views/sale_order_views.xml",
        "views/stock_picking_views.xml",
        "views/account_move_views.xml",
        "views/purchase_order_views.xml",
        "views/report_templates.xml",
        "views/report_no_taxes.xml",
    ],
    "license": "LGPL-3",
    "application": False,
    "installable": True,
}

