# -*- coding: utf-8 -*-
{
    "name": "Qader Steel Suite - Sales, Purchase, Delivery & Accounting",
    "version": "19.0.1.0.0",
    "category": "Sales",
    "summary": "All-in-one operations suite: bundle/weight calculator, driver & "
               "transportation info, multi-currency partner ledger and "
               "customer/vendor statement report.",
    "description": """
Qader Steel Suite
==================
A single consolidated module that merges four previously separate addons
into one, so they can be installed, upgraded and maintained together:

1. **Bundle Weighing Calculator** (formerly ``mq_bundle_wieghing_calculator``)
   Calculates total weight from bundle quantity on Sales, Purchase,
   Delivery and Invoicing documents, with a scale-weight distribution
   button on orders and transfers.

2. **Delivery Driver Info** (formerly ``mq_delivery_driver_info``)
   Adds driver name, phone, car plate, border crossing and scale number
   to Sales Orders, Purchase Orders, Deliveries and Invoices, with
   auto-sync between the delivery/invoice and its source order, plus
   report layout extensions (driver info block, no-taxes layout,
   forced report language).

3. **Partner Ledger - Amount in Document Currency** (formerly
   ``partner_ledger_currency``, requires Odoo Enterprise ``account_reports``)
   Fills the "Amount Currency" column of the Partner Ledger for every
   line (including company-currency lines) and can optionally add a
   "Currency" column - see the Notes section below, this extra column
   is shipped disabled by default exactly as in the original module.

4. **Customer / Vendor Statement Report** (formerly
   ``customer_statement_report``)
   Multi-currency partner statement with product-level detail, split
   into one section per currency, plus a consolidated company-currency
   total.

5. **Net-Weight Sales Automation & Requisition Auto-Populate**
   Net Weight is distributed proportionally across eligible non-service sale
   lines; Scale Net Weight mirrors Net Weight; Shipping Cost/Ton creates one
   total transport/clearance service line; Confirm SO runs the same calculation
   before standard confirmation, then completes dropship purchase, stock
   validation and customer/vendor invoicing using Odoo standard methods.
   Purchase Agreements auto-populate saleable, purchasable, storable products
   at the configured per-ton price when the agreement is first saved.


Notes
-----
* The four original modules already shared data (the bundle calculator
  depended on the driver-info module), so merging them does not change
  any business logic - it only combines the code, views and data files
  into a single installable unit. Load order between the "driver info"
  and "bundle" groups of views is preserved on purpose so printed
  reports stack in the same visual order as before.
* ``data/partner_ledger_columns.xml`` (the extra "Currency" column) is
  kept commented out of ``data`` below, exactly as it was in the
  original ``partner_ledger_currency`` module - the Amount Currency
  fix is independent of it and always active.
* Because part 3 depends on the Enterprise-only ``account_reports``
  app, this merged module as a whole now requires Odoo Enterprise to
  install, even for the parts that don't use it. The four modules used
  to be installable independently of one another.
    """,
    "author": "Magic Quantum",
    "license": "LGPL-3",
    "depends": [
        "sale_management",
        "sale",
        "sale_stock",
        "purchase",
        "purchase_stock",
        "purchase_requisition",
        "stock",
        "account",
        "account_reports",
    ],
    "data": [
        "security/ir.model.access.csv",

        # --- Delivery / Driver Info (loads first) ------------------------
        "views/driver_info_master_views.xml",
        "views/driver_info_sale_order_views.xml",
        "views/driver_info_purchase_order_views.xml",
        "views/driver_info_stock_picking_views.xml",
        "views/driver_info_account_move_views.xml",
        "views/driver_info_report_templates.xml",
        "views/driver_info_report_no_taxes.xml",

        # --- Bundle Weighing Calculator (loads after driver info, so its -
        # --- printed blocks stack directly below the driver info block) --
        "views/bundle_product_template_views.xml",
        "views/bundle_sale_order_views.xml",
        "views/bundle_purchase_order_views.xml",
        "views/bundle_stock_picking_views.xml",
        "views/bundle_account_move_views.xml",
        "views/bundle_sale_report_templates.xml",
        "views/bundle_purchase_report_templates.xml",
        "views/bundle_account_report_templates.xml",
        "views/bundle_stock_report_templates.xml",

        # --- Partner Ledger - Amount in Document Currency -----------------
        # "data/partner_ledger_columns.xml",  # disabled by default, see description

        # --- Customer / Vendor Statement Report ---------------------------
        "views/statement_account_move_line_views.xml",
        "views/statement_wizard_views.xml",
        "report/customer_statement_report.xml",
        "report/customer_statement_templates.xml",

        # --- Full-cycle sale automation + requisition auto-populate -------
        "views/automation_sale_order_views.xml",
        "views/automation_server_actions.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
