from odoo import models, fields

class PurchaseCancelReason(models.Model):
    _name = 'purchase.cancel.reason'
    _description = 'Purchase Cancel Reason'

    name = fields.Char(string="Reason", required=True)