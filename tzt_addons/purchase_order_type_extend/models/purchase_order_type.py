from odoo import models, fields

class PurchaseOrderType(models.Model):
    _name = 'purchase.order.type'
    _description = 'Purchase Order Type'

    name = fields.Char(string="Order Type", required=True)
