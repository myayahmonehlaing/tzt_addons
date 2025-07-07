from odoo import models, fields

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    # order_type_id = fields.Many2one('purchase.order.type', string='Order Type')
    order_type_id = fields.Many2one( 'purchase.order.type', string='Order Type', store=True, readonly=True )

