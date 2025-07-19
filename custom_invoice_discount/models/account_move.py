from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def get_custom_invoice_values(self):
        self.ensure_one()
        discount_total = 0.0

        for line in self.invoice_line_ids:
            if line.price_subtotal < 0:
                discount_total += -(line.price_subtotal)

        if self.env.context.get('report_generation'):
            self.invoice_line_ids = self.invoice_line_ids.filtered(lambda l: l.price_subtotal >= 0)

        subtotal = (self.amount_untaxed or 0.0) + discount_total
        tax = self.amount_tax or 0.0
        total = subtotal - discount_total + tax

        return {
            'custom_subtotal': float(subtotal),
            'custom_discount': float(discount_total),
            'custom_total': float(total),
        }
