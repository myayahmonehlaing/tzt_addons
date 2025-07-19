from odoo import tools
from odoo import fields, models

class PurchaseReport(models.Model):
    _inherit = 'purchase.report'

    order_type_id = fields.Many2one('purchase.order.type', string='Order Type', readonly=True)

    def _select(self):
        return tools.sql.SQL("""
            %s,
            po.order_type_id AS order_type_id
        """, super()._select())

    def _group_by(self):
        return tools.sql.SQL("""
            %s,
            po.order_type_id
        """, super()._group_by())
