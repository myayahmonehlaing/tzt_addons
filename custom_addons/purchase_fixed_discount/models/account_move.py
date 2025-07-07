from odoo import models, api


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _prepare_product_base_line_for_taxes_computation(self, product_line):
        self.ensure_one()
        is_invoice = self.is_invoice(include_receipts=True)
        sign = self.direction_sign if is_invoice else 1

        rate = self.invoice_currency_rate if is_invoice else (
            abs(product_line.amount_currency) / abs(product_line.balance) if product_line.balance else 0.0
        )

        discount = product_line.discount or 0.0
        fixed_discount = product_line.fixed_discount or 0.0
        quantity = product_line.quantity or 1.0

        price_unit = product_line.price_unit * (1 - discount / 100.0)
        total_price = price_unit * quantity
        total_price_after_fixed = max(total_price - fixed_discount, 0.0)
        adjusted_price_unit = total_price_after_fixed / quantity if quantity else 0.0

        return self.env['account.tax']._prepare_base_line_for_taxes_computation(
            product_line,
            price_unit=adjusted_price_unit,
            quantity=quantity,
            discount=0.0,
            rate=rate,
            sign=sign,
            special_mode=False if is_invoice else 'total_excluded',
        )
