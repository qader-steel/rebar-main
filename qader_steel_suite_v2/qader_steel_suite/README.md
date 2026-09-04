# Qader Steel Suite (`qader_steel_suite`)

Odoo 19.0. This module merges four previously-separate addons into a single
installable module, at the request of management, so they ship, upgrade and
version together instead of as four independent addons.

| Merged from (old technical name)     | What it does |
|---------------------------------------|--------------|
| `mq_bundle_wieghing_calculator`       | Bundle Qty → Total Weight calculation on Sale/Purchase/Delivery/Invoice, with a "calculate scale weight" button that distributes a scale ticket's net weight across bundled lines. |
| `mq_delivery_driver_info`             | Driver name / phone / car plate / border crossing / scale number on Sale, Purchase, Delivery and Invoice, kept in sync between an order and its delivery/invoice, plus report layout tweaks (driver-info block, no-taxes layout, forced report language). |
| `partner_ledger_currency`             | Fixes the Partner Ledger's "Amount Currency" column so company-currency lines show their amount too (Odoo Enterprise, needs `account_reports`). |
| `customer_statement_report`           | Multi-currency Customer/Vendor Statement report with product-level detail, one section per currency plus a consolidated company-currency total. |

## ⚠️ Before you install: Enterprise requirement

`partner_ledger_currency` depends on `account_reports`, which is an
**Odoo Enterprise** app. Because everything is now one module, the *whole*
suite requires Enterprise to install — even the parts (bundle weighing,
driver info, statement report) that have nothing to do with accounting
reports and used to install fine on Community. If this database is on
Community edition, this merged module will fail to install; in that case
either add Enterprise, or pull `models/account_partner_ledger.py`,
`data/partner_ledger_columns.xml`, `tests/test_partner_ledger_currency.py`
and `account_reports` out of `depends` before installing.

## What did NOT change

The four modules already shared data before this merge — the bundle
calculator already depended on the driver-info module in the original
`__manifest__.py`. So this merge does not change any business logic; it only
combines code, views, security and data into one module. In particular:

* **Load order is preserved on purpose.** In `__manifest__.py`, all
  "driver info" data files are listed before all "bundle weighing" data
  files, exactly reproducing the old install order (driver info module was
  a dependency of the bundle module). This matters because several printed
  reports (Sale Order, Invoice, Purchase Order, Delivery Slip) inject a
  colored info block "before" the same anchor element from two different
  views — the driver-info block must render first so the bundle
  totals block appears directly below it, as before.
* **No model, field or XML-id collisions** — verified programmatically
  (see "Sanity checks" below). The four modules never touched the same
  model with the same field name, and no two `<record>`/`<template>`/
  `<menuitem>` share an id.
* `data/partner_ledger_columns.xml` (the extra "Currency" column on the
  Partner Ledger) is still commented out of `data` in the manifest, exactly
  as it was in the original `partner_ledger_currency` module. The "Amount
  Currency" fix itself is independent of this file and is always active.

## What DID have to change (and why)

Merging modules is not just "copy files into one folder." Two categories of
changes were required so nothing breaks after the merge:

1. **Filename collisions.** Both the driver-info and bundle modules shipped
   files with the same names (`sale_order_views.xml`,
   `purchase_order_views.xml`, `stock_picking_views.xml`,
   `account_move_views.xml`). They're now prefixed `driver_info_*` and
   `bundle_*` respectively so both can live in one `views/` folder.
2. **Hard-coded module name in the Statement report.** The original
   `customer_statement_report` module referenced its own technical name in
   several places that Odoo resolves as literal identifiers at runtime:
   the `report_name`/`report_file` fields, the `t-call` between its two
   QWeb templates, the wizard's `self.env.ref(...)` call to fetch the
   report action, and the processing model's `_name` (Odoo's report engine
   requires that name to equal `report.<report_name>` exactly). All of
   these were updated from `customer_statement_report.*` to
   `qader_steel_suite.*`. This was the one part of the merge that could
   have silently broken "Print Statement" if left as-is — it's covered by
   `tests/test_multi_currency_statement.py`.

## Structure

```
qader_steel_suite/
├── __manifest__.py
├── __init__.py
├── models/               # driver info, bundle weighing, partner ledger patch
├── wizard/                # customer/vendor statement engine + wizard
├── views/                 # driver_info_*.xml, bundle_*.xml, statement_*.xml
├── report/                # statement report actions, QWeb templates, css
├── data/                  # partner_ledger_columns.xml (inactive by default)
├── security/ir.model.access.csv
├── i18n/ar.po
└── tests/
```

## Update (Sept 2026) - management's refinement requests on the Sale Order + Purchase Agreement automation

* **Sale Order — Scale Net Weight.** The manual "احتساب وزن القبان الصافي"
  button and its distribute-by-bundle-ratio logic were removed from the
  Sale Order form only (still present, unchanged, on Purchase Order and
  Stock Picking). `mq_scale_net_weight` on `sale.order` is now a
  read-only computed field that always mirrors `x_studio_net_weight`
  ("Net Weight").
* **Sale Order — two buttons, one shared algorithm.**
  * **"Net Weight"** (`action_net_weight`) — new standalone button.
    Proportionally distributes `x_studio_net_weight` across eligible
    order lines (by each line's existing quantity ratio — simulating the
    gap between theoretical weight and the real scale reading after
    impurities/dust are removed), then (re)creates the "أجور النقل
    والتخليص" line as `Shipping Cost (Ton) × Net Weight`, always last by
    sequence. Does not confirm the order.
  * **"تنفيذ الدورة الكاملة" / Confirm SO** (`action_run_full_cycle`) —
    runs the exact same distribution first (via the shared
    `_apply_net_weight_distribution()` method, so the two buttons can
    never drift out of sync), then confirms the sale order, confirms &
    links any dropship purchase orders, force-validates every related
    transfer (now using each line's own proportional quantity, not one
    flat number for every move/PO line), and creates + posts the
    customer invoice and any vendor bill.
  * A new read-only **"Total Net Weight"** field at the bottom of the
    order sums the eligible lines' quantities, so it can be visually
    checked against "Net Weight" after either button runs.
* **Sale Order — "هلال بابل" smart button.** Reproduces, with a fixed
  label as requested, the Studio smart button that always opened the
  dropship transfer for the order (whose vendor/contact is always the
  same fixed partner "هلال بابل"). It jumps to the dropship picking(s)
  linked through this order's purchase orders and is hidden when there
  are none. **This is a best-effort reconstruction of a Studio artifact
  the assistant could not open directly — verify the target/label match
  what's expected on a test order before relying on it in production.**
* **Purchase Agreement (`purchase.requisition`) — new fields:**
  `x_studio_price_ton` (Price/Ton, already existed), `x_studio_total_ordered`
  (compute, sum of `line_ids.qty_ordered`), `x_studio_value` (compute,
  Price × Total Ordered), `x_studio_agreement_amount` (manual entry),
  `x_studio_remaining_amount` (compute, Agreement Amount − Value), and
  `x_studio_total_payable` (related to the vendor's standard "Total
  Payable" field, `res.partner.debit`, in the vendor's own currency via
  `x_studio_vendor_id_currency_id`). **`x_studio_total_payable`'s exact
  meaning was reconstructed from a Studio-generated related-field
  technical name and a vendor-currency field name the user described —
  it was not independently verified against the live database; confirm
  it shows the expected number before relying on it.**
* **Purchase Agreement — auto-populate on save.** The products tree
  (`line_ids`) is now filled automatically from `create()`/`write()`
  whenever it is empty (one line per purchasable, non-service product,
  qty 100, price = Price/Ton) — no separate button click needed anymore.
  The original `action_populate_all_products()` / "تعبئة كل المنتجات
  تلقائيًا" gear-menu action stays available as a manual fallback (it is
  a no-op if lines already exist).
* New view file `views/purchase_agreement_views.xml` adds all of the
  above fields to the Purchase Agreement form. Its `<xpath>` anchors on
  `field[@name='vendor_id']` and `sheet/notebook` (present on every Odoo
  Purchase Agreement form) rather than a specific internal group id,
  since the exact standard view could not be inspected in this
  environment — **please open the form once after installing/upgrading
  to confirm the new fields land where you expect, and adjust the
  `<xpath>` in that file if not.**

## Install

```bash
# copy the qader_steel_suite folder next to your other addons, then:
odoo-bin -d <database> -i qader_steel_suite --stop-after-init
```

If the four original modules are already installed on this database,
installing `qader_steel_suite` will create duplicate models/menus unless you
first uninstall them (their data — driver history lists, statement wizard
runs, etc. — lives on separate models and is not touched by uninstalling
the old modules, so this is safe to do before installing the merged one).

## Tests

```bash
odoo-bin -d <db> -i qader_steel_suite --test-enable \
         --test-tags /qader_steel_suite --stop-after-init
```

Runs both test suites (Partner Ledger currency columns, multi-currency
statement) carried over unchanged from the original modules.

## Sanity checks performed while merging

* All XML files parse (well-formed).
* All Python files compile.
* `__manifest__.py` is a valid dict; every path in `data` exists on disk.
* No duplicate `<record>` / `<template>` / `<menuitem>` id across all views.
* No duplicate Odoo model `_name` across all files.
* No remaining hard-coded reference to any of the four old module technical
  names anywhere in the code (`report_name`, `t-call`, `env.ref`, `_name`).
