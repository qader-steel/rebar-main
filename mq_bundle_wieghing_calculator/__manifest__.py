{
    "name": "MQ Bundle Weighing Calculator",
    "version": "19.0.1.0.0",
    "category": "Sales",
    "summary": "Calculate Total Weight based on Bundle Quantity. Adds Bundle Qty & Custom Quantity to Sales, Delivery, and Invoices.",
    "depends": ["sale_management", "stock", "account", "purchase", "purchase_stock", "mq_delivery_driver_info"],
    "data": [
        "views/product_template_views.xml",
        "views/sale_order_views.xml",
        "views/purchase_order_views.xml",
        "views/stock_picking_views.xml",
        "views/account_move_views.xml",
        "views/sale_report_templates.xml",
        "views/purchase_report_templates.xml",
        "views/account_report_templates.xml",
        "views/stock_report_templates.xml"
    ],
    "license": "LGPL-3",
    "installable": True,
    "application": False,
}
