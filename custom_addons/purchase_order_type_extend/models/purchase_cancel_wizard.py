from odoo import models, fields
class PurchaseCancelWizard(models.TransientModel):
    _name = 'purchase.cancel.wizard'
    _description = 'Wizard for Canceling Purchase Order'

    reason_id = fields.Many2one('purchase.cancel.reason', required=True)

    def action_confirm_cancel(self):
        order = self.env['purchase.order'].browse(self.env.context.get('active_id'))
        if order:
            # Log the cancel reason
            order.message_post(body=f"Purchase Order cancelled with reason: {self.reason_id.name}")

            # Call the real cancel function that changes the state
            order.do_cancel()
