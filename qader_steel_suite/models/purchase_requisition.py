import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class PurchaseRequisition(models.Model):
    _inherit = 'purchase.requisition'

    x_studio_price_ton = fields.Float(string="Price (Ton)")

    # ------------------------------------------------------------------
    # حقول Purchase Agreement الإضافية (طلب إداري)
    # ------------------------------------------------------------------
    x_studio_total_ordered = fields.Float(
        string="Total Ordered",
        compute="_compute_x_studio_total_ordered",
        store=True,
        help="Sum of qty_ordered across all agreement lines.",
    )
    x_studio_value = fields.Monetary(
        string="Value",
        compute="_compute_x_studio_value",
        store=True,
        currency_field='currency_id',
        help="Price (Ton) × Total Ordered.",
    )
    x_studio_agreement_amount = fields.Monetary(
        string="Agreement Amount",
        currency_field='currency_id',
        help="السقف/القيمة الإجمالية المتفق عليها مع المورد - تُدخل يدويًا.",
    )
    x_studio_remaining_amount = fields.Monetary(
        string="Remaining Amount",
        compute="_compute_x_studio_remaining_amount",
        store=True,
        currency_field='currency_id',
        help="Agreement Amount − Value.",
    )

    # "Total Payable" - حقل مرتبط (Related Field) بقيمة "Total Payable"
    # القياسية على المورد (res.partner.debit، أي المبلغ المستحق دفعه لهذا
    # المورد حسب فواتير المشتريات المرحّلة)، بعملة المورد. هذا يطابق ما
    # أنشأه المنفذ عبر الاستديو (اسم تقني عشوائي x_studio_related_field_*
    # هو الشكل المعتاد لحقل Related في Studio؛ أعدنا إنشاءه هنا كحقلين
    # واضحي الاسم بدل الاسم العشوائي غير القابل للقراءة).
    x_studio_vendor_id_currency_id = fields.Many2one(
        'res.currency',
        string="Vendor Currency",
        related='vendor_id.currency_id',
        store=True,
        readonly=True,
    )
    # ملاحظة: بدون store=True عمدًا - res.partner.debit حقل محسوب غير
    # مخزَّن أصلًا (Odoo)، فتخزين حقل related عليه قد يُبقي قيمة قديمة.
    # تُقرأ هنا مباشرة في كل مرة لضمان أنها دائمًا القيمة الحيّة.
    x_studio_total_payable = fields.Monetary(
        string="Total Payable",
        related='vendor_id.debit',
        currency_field='x_studio_vendor_id_currency_id',
        readonly=True,
        help="The total amount payable to this vendor overall (res.partner.debit) - same as the 'Total Payable' field on the contact form.",
    )

    @api.depends('line_ids.qty_ordered')
    def _compute_x_studio_total_ordered(self):
        for record in self:
            record.x_studio_total_ordered = sum(record.line_ids.mapped('qty_ordered'))

    @api.depends('x_studio_price_ton', 'x_studio_total_ordered')
    def _compute_x_studio_value(self):
        for record in self:
            price = record.x_studio_price_ton or 0.0
            total = record.x_studio_total_ordered or 0.0
            record.x_studio_value = price * total

    @api.depends('x_studio_agreement_amount', 'x_studio_value')
    def _compute_x_studio_remaining_amount(self):
        for record in self:
            record.x_studio_remaining_amount = (
                (record.x_studio_agreement_amount or 0.0) - (record.x_studio_value or 0.0)
            )

    # ------------------------------------------------------------------
    # تعبئة شجرة المنتجات تلقائيًا عند الحفظ (طلب إداري: "اول ماضغط
    # save" - سابقًا كانت تُنفَّذ يدويًا فقط من زر/Server Action). نُبقي
    # على action_populate_all_products أدناه كخيار احتياطي يدوي، لكن
    # create()/write() هما ما يُطبّقان السلوك التلقائي فعليًا الآن.
    # الشرط كما ورد من المدير حرفيًا: لا تُنفَّذ إلا إن كانت line_ids
    # فارغة وقت الحفظ (لا تكرار ولا استبدال لسطور موجودة).
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._auto_populate_products_if_empty()
        return records

    def write(self, vals):
        res = super().write(vals)
        # لا داعي لإعادة الفحص إن كانت الكتابة الحالية هي نفسها ملأت
        # line_ids (لتفادي أي تكرار غير ضروري)، لكن الفحص بحد ذاته آمن
        # ورخيص لأنه لا يفعل شيئًا إن كانت السطور غير فارغة.
        if 'line_ids' not in vals:
            self._auto_populate_products_if_empty()
        return res

    def _auto_populate_products_if_empty(self):
        """نفس منطق action_populate_all_products أدناه حرفيًا، لكن بدون
        استدعاء يدوي - تُستدعى تلقائيًا من create()/write()."""
        Product = self.env['product.product']
        for record in self:
            if record.line_ids:
                continue
            unit_price = record.x_studio_price_ton or 0.0
            products = Product.search([
                ('purchase_ok', '=', True),
                ('type', '!=', 'service'),
            ])
            if not products:
                continue
            _logger.info(
                "QSS [auto_populate_products] ✏ سجل id=%s: إضافة %s سطر "
                "تلقائيًا عند الحفظ (سعر الطن=%.4f).",
                record.id, len(products), unit_price,
            )
            record.write({
                'line_ids': [
                    (0, 0, {
                        'product_id': product.id,
                        'product_qty': 100.0,
                        'price_unit': unit_price,
                    })
                    for product in products
                ],
            })

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