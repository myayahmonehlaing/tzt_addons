from odoo import models, fields, api


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    fixed_discount = fields.Float(string="Fixed Discount")
    currency_id = fields.Many2one(related='order_id.currency_id', store=True, readonly=True)

    price_subtotal = fields.Monetary(string="Subtotal", compute='_compute_amount', store=True,
                                     currency_field='currency_id')
    price_tax = fields.Float(string="Tax", compute='_compute_amount', store=True)
    price_total = fields.Monetary(string="Total", compute='_compute_amount', store=True, currency_field='currency_id')

    @api.depends('product_qty', 'price_unit', 'taxes_id', 'discount', 'fixed_discount')
    def _compute_amount(self):
        for line in self:
            if not line.order_id:
                line.price_subtotal = 0.0
                line.price_tax = 0.0
                line.price_total = 0.0
                continue

            # First apply percentage discount
            discounted_unit_price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)

            # Then subtract fixed discount from total line amount
            total_price = (discounted_unit_price * line.product_qty) - (line.fixed_discount or 0.0)
            total_price = max(total_price, 0.0)
            effective_unit_price = total_price / line.product_qty if line.product_qty else 0.0

            # Use compute_all with effective unit price
            taxes = line.taxes_id.compute_all(
                effective_unit_price,
                currency=line.order_id.currency_id,
                quantity=line.product_qty,
                product=line.product_id,
                partner=line.order_id.partner_id
            )
            line.price_subtotal = taxes['total_excluded']
            line.price_tax = taxes['total_included'] - taxes['total_excluded']
            line.price_total = taxes['total_included']

    @api.onchange('fixed_discount', 'discount', 'price_unit', 'product_qty')
    def _onchange_recalculate_discount(self):
        for line in self:
            line._compute_amount()

    def _prepare_base_line_for_taxes_computation(self):
        self.ensure_one()

        # Manually apply both percentage and fixed discounts
        price_unit = self.price_unit * (1 - (self.discount or 0.0) / 100.0)
        price_unit -= (self.fixed_discount or 0.0)
        price_unit = max(price_unit, 0.0)

        return self.env['account.tax']._prepare_base_line_for_taxes_computation(
            self,
            tax_ids=self.taxes_id,
            price_unit=price_unit,
            quantity=self.product_qty,
            discount=0.0,  # Tell tax engine to skip discount logic
            partner_id=self.order_id.partner_id,
            currency_id=self.order_id.currency_id,
            rate=self.order_id.currency_rate,
        )

    def _prepare_account_move_line(self, move=False):
        res = super()._prepare_account_move_line(move)
        res['fixed_discount'] = self.fixed_discount or 0.0
        return res
