import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class PurchaseRequisition(models.Model):
    _inherit = 'purchase.requisition'

    x_studio_price_ton = fields.Float(string="Price (Ton)")

    def action_populate_all_products(self):
        _logger.info(
            "QSS [populate_products] ▶ تم استدعاء الإجراء على %s سجل/سجلات: ids=%s",
            len(self), self.ids,
        )

        Product = self.env['product.product']

        for requisition in self:
            _logger.info(
                "QSS [populate_products] ── فحص السجل: id=%s name=%s",
                requisition.id, requisition.display_name,
            )

            # ── شرط 1: هل يوجد سطور مسبقًا؟ ─────────────────────────────
            if requisition.line_ids:
                _logger.warning(
                    "QSS [populate_products] ⛔ تم تخطي السجل id=%s لأنه يحوي "
                    "%s سطر/سطور مسبقة — الكود يشترط أن تكون السطور فارغة.",
                    requisition.id, len(requisition.line_ids),
                )
                continue

            unit_price = requisition.x_studio_price_ton or 0.0
            _logger.info(
                "QSS [populate_products] ✔ السجل id=%s فارغ من السطور، "
                "سعر الطن المُقروء = %.4f",
                requisition.id, unit_price,
            )

            # ── شرط 2: هل توجد منتجات قابلة للشراء؟ ─────────────────────
            products = Product.search([
                ('purchase_ok', '=', True),
                ('type', '!=', 'service'),
            ])
            _logger.info(
                "QSS [populate_products] 🔍 عدد المنتجات القابلة للشراء "
                "(غير الخدمية) في قاعدة البيانات = %s",
                len(products),
            )

            if not products:
                _logger.warning(
                    "QSS [populate_products] ⛔ لم يُعثر على أي منتج قابل "
                    "للشراء وغير خدمي — لن يُضاف أي سطر للسجل id=%s.",
                    requisition.id,
                )
                continue

            # ── كتابة السطور ──────────────────────────────────────────────
            _logger.info(
                "QSS [populate_products] ✏ جاري إضافة %s سطر للسجل id=%s ...",
                len(products), requisition.id,
            )
            try:
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
                    "QSS [populate_products] ✅ تمت إضافة %s سطر بنجاح "
                    "للسجل id=%s اسم=%s بسعر %.4f لكل طن.",
                    len(products), requisition.id,
                    requisition.display_name, unit_price,
                )
            except Exception as exc:
                _logger.exception(
                    "QSS [populate_products] ❌ فشلت الكتابة للسجل id=%s — %s",
                    requisition.id, exc,
                )
                raise

        _logger.info("QSS [populate_products] ■ انتهى تنفيذ الإجراء.")
