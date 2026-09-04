from odoo import models, fields, api

class ProductTemplate(models.Model):
    """
    Inherited to add bundle weight configuration to products.
    """
    _inherit = 'product.template'

    mq_is_bundle_weight = fields.Boolean(string="Bundle Weight")
    mq_bundle_multiplier = fields.Float(string="Bundle Multiplier", default=1.0)
