# -*- coding: utf-8 -*-
import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class PurchaseRequisition(models.Model):
    _inherit = 'purchase.requisition'

    x_studio_price_ton = fields.Float(string="Price (Ton)")
    qss_products_auto_populated = fields.Boolean(
        string="QSS Products Auto Populated",
        default=False,
        copy=False,
        readonly=True,
    )

    def _qss_product_domain(self):
        """Odoo 19: saleable + purchasable + stock-tracked products only."""
        domain = [
            ('active', '=', True),
            ('sale_ok', '=', True),
            ('purchase_ok', '=', True),
            ('is_storable', '=', True),
        ]
        # Avoid mixing company-specific and shared products on a company PO.
        if self.company_id:
            domain.append(
                '|',
            )
            domain.extend([
                ('company_id', '=', False),
                ('company_id', '=', self.company_id.id),
            ])
        return domain

    def _qss_populate_products(self):
        Product = self.env['product.product']
        for requisition in self:
            if requisition.line_ids:
                continue

            products = Product.search(requisition._qss_product_domain(), order='id')
            if not products:
                _logger.info(
                    "QSS requisition %s: no saleable/purchasable storable products found.",
                    requisition.display_name,
                )
                continue

            unit_price = requisition.x_studio_price_ton or 0.0
            requisition.write({
                'line_ids': [
                    (0, 0, {
                        'product_id': product.id,
                        'product_qty': 100.0,
                        'price_unit': unit_price,
                    })
                    for product in products
                ],
                'qss_products_auto_populated': True,
            })

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._qss_populate_products()
        return records

    def write(self, vals):
        result = super().write(vals)
        if 'x_studio_price_ton' in vals:
            # Update prices only for lines that were created by this module.
            # Manually-created agreement lines remain untouched.
            for requisition in self.filtered('qss_products_auto_populated'):
                requisition.line_ids.filtered(
                    lambda line: line.display_type not in ('line_section', 'line_note')
                ).write({'price_unit': requisition.x_studio_price_ton or 0.0})
        return result

    def action_populate_all_products(self):
        self._qss_populate_products()
        return True



























# import logging

# from odoo import fields, models

# _logger = logging.getLogger(__name__)


# class PurchaseRequisition(models.Model):
#     _inherit = 'purchase.requisition'

#     x_studio_price_ton = fields.Float(string="Price (Ton)")

#     def action_populate_all_products(self):
#         _logger.info(
#             "QSS [populate_products] ▶ تم استدعاء الإجراء على %s سجل/سجلات: ids=%s",
#             len(self), self.ids,
#         )

#         Product = self.env['product.product']

#         for requisition in self:
#             _logger.info(
#                 "QSS [populate_products] ── فحص السجل: id=%s name=%s",
#                 requisition.id, requisition.display_name,
#             )

#             # ── شرط 1: هل يوجد سطور مسبقًا؟ ─────────────────────────────
#             if requisition.line_ids:
#                 _logger.warning(
#                     "QSS [populate_products] ⛔ تم تخطي السجل id=%s لأنه يحوي "
#                     "%s سطر/سطور مسبقة — الكود يشترط أن تكون السطور فارغة.",
#                     requisition.id, len(requisition.line_ids),
#                 )
#                 continue

#             unit_price = requisition.x_studio_price_ton or 0.0
#             _logger.info(
#                 "QSS [populate_products] ✔ السجل id=%s فارغ من السطور، "
#                 "سعر الطن المُقروء = %.4f",
#                 requisition.id, unit_price,
#             )

#             # ── شرط 2: هل توجد منتجات قابلة للشراء؟ ─────────────────────
#             products = Product.search([
#                 ('purchase_ok', '=', True),
#                 ('type', '!=', 'service'),
#             ])
#             _logger.info(
#                 "QSS [populate_products] 🔍 عدد المنتجات القابلة للشراء "
#                 "(غير الخدمية) في قاعدة البيانات = %s",
#                 len(products),
#             )

#             if not products:
#                 _logger.warning(
#                     "QSS [populate_products] ⛔ لم يُعثر على أي منتج قابل "
#                     "للشراء وغير خدمي — لن يُضاف أي سطر للسجل id=%s.",
#                     requisition.id,
#                 )
#                 continue

#             # ── كتابة السطور ──────────────────────────────────────────────
#             _logger.info(
#                 "QSS [populate_products] ✏ جاري إضافة %s سطر للسجل id=%s ...",
#                 len(products), requisition.id,
#             )
#             try:
#                 requisition.write({
#                     'line_ids': [
#                         (0, 0, {
#                             'product_id': product.id,
#                             'product_qty': 100.0,
#                             'price_unit': unit_price,
#                         })
#                         for product in products
#                     ],
#                 })
#                 _logger.info(
#                     "QSS [populate_products] ✅ تمت إضافة %s سطر بنجاح "
#                     "للسجل id=%s اسم=%s بسعر %.4f لكل طن.",
#                     len(products), requisition.id,
#                     requisition.display_name, unit_price,
#                 )
#             except Exception as exc:
#                 _logger.exception(
#                     "QSS [populate_products] ❌ فشلت الكتابة للسجل id=%s — %s",
#                     requisition.id, exc,
#                 )
#                 raise

#         _logger.info("QSS [populate_products] ■ انتهى تنفيذ الإجراء.")
