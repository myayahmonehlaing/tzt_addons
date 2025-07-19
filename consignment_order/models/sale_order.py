from odoo import models, fields, api
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    consignment_id = fields.Many2one(
        'consignment.order',
        string="Consignment Order",
        domain=[('state', '=', 'confirmed')],
        tracking=True,
    )

    @api.onchange('consignment_id')
    def _onchange_consignment_id(self):
        if not self.consignment_id:
            self.order_line = [(5, 0, 0)]
            return

        # Switch to consignment company context
        self = self.with_company(self.consignment_id.company_id)

        self.partner_id = self.consignment_id.customer_id
        self.company_id = self.consignment_id.company_id

        self.order_line = [(5, 0, 0)]
        lines = []

        for line in self.consignment_id.order_line:
            remaining_qty = line.quantity - line.qty_ordered
            if remaining_qty > 0:
                lines.append((0, 0, {
                    'product_id': line.product_id.id,
                    'product_uom_qty': remaining_qty,
                    'price_unit': line.price_unit,
                    'product_uom': line.uom_id.id,
                    'name': line.product_id.name or '',
                }))

        self.order_line = lines

        warehouse = self.consignment_id.company_id.consignment_warehouse_setting_id
        if warehouse:
            self.warehouse_id = warehouse.id

    def action_confirm(self):
        res = super().action_confirm()
        for order in self:
            if order.consignment_id:
                for so_line in order.order_line:
                    consignment_lines = order.consignment_id.order_line.filtered(
                        lambda l: l.product_id == so_line.product_id)
                    for cl in consignment_lines:
                        cl.qty_ordered += so_line.product_uom_qty
        return res

