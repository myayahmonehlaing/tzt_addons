from odoo import models, fields

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'
    order_type_id = fields.Many2one('purchase.order.type', string="Order Type", store=True)
    def button_cancel(self):
        # Instead of canceling here, show the wizard popup
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.cancel.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'active_id': self.id},
        }

    def do_cancel(self):
        # Call the original Odoo cancel method to update status
        return super(PurchaseOrder, self).button_cancel()

    def _prepare_invoice(self):
        invoice_vals = super()._prepare_invoice()
        invoice_vals['order_type_id'] = self.order_type_id.id
        return invoice_vals

    def _prepare_picking(self):
        res = super()._prepare_picking()

        res['order_type_id'] = self.order_type_id.id
        return res

    # def button_confirm(self):
    #     res = super().button_confirm()
    #     for order in self:
    #         for picking in order.picking_ids:
    #             picking.order_type_id = order.order_type_id.id
    #     return res


