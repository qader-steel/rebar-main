# -*- coding: utf-8 -*-
{
    "name": "Qader Steel Suite - Sales, Purchase, Delivery & Accounting",
    "version": "19.0.1.3.0",
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

3. **Per-currency totals on the accounting reports** (formerly
   ``partner_ledger_currency``, requires Odoo Enterprise ``account_reports``)
   Fills the "Amount Currency" column of the **Partner Ledger** and the
   **General Ledger** for every line - including company-currency lines,
   which Odoo leaves blank because it stores their value in ``balance``
   instead of ``amount_currency`` - and adds one "<CUR> Total" row per
   currency under each partner (Partner Ledger) and under each account
   (General Ledger). A partner holding both IQD and USD documents
   therefore shows an IQD total on its own and a USD total on its own.
   Can optionally add a "Currency" column - see the Notes section below,
   this extra column is shipped disabled by default exactly as in the
   original module.

4. **Customer / Vendor Statement Report** (formerly
   ``customer_statement_report``)
   Multi-currency partner statement with product-level detail, split
   into one section per currency, opened by a "Balances by Currency"
   summary table, plus a consolidated company-currency total. Supports
   both the customer and the vendor side (``party_type`` on the wizard).

5. **Full-Cycle Sale Automation & Requisition Auto-Populate**
   A "Run Full Cycle" button/action on Sale Orders that, per management's
   explicit request, ports the original hand-off automation code
   literally: syncs the net weight to every non-service order line,
   adds a shipping fee line, confirms the sale, confirms & links any
   dropship purchase orders, force-validates every related transfer,
   then creates and posts the customer invoice and any vendor bill.
   A safer earlier draft (reusing the module's proportional bundle-weight
   distribution and Odoo's standard invoicing methods) is kept fully
   commented out at the bottom of ``models/sale_order_automation.py`` for
   reference / rollback - see that file's header comment. Plus an action
   on Purchase Requisitions that bulk-adds one line per purchasable
   product at a flat per-ton price.

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
        "views/purchase_agreement_views.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}