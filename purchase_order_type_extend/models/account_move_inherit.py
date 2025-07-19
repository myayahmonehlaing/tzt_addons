from odoo import models, fields

class AccountMove(models.Model):
    _inherit = 'account.move'

    order_type_id = fields.Many2one('purchase.order.type', string="Order Type")
