from odoo import models, fields, api, _
from odoo.tools import frozendict


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    fixed_discount = fields.Monetary(string='Fixed Discount', currency_field='currency_id')

    price_subtotal = fields.Monetary(
        string='Subtotal',
        store=True, readonly=True, compute='_compute_totals',
        currency_field='currency_id'
    )

    price_total = fields.Monetary(
        string='Total',
        store=True, readonly=True, compute='_compute_totals',
        currency_field='currency_id'
    )

    @api.depends('quantity', 'price_unit', 'discount', 'fixed_discount', 'tax_ids')
    def _compute_totals(self):
        for line in self:
            quantity = line.quantity or 1.0
            discount_pct = (line.discount or 0.0) / 100.0
            fixed_discount = line.fixed_discount or 0.0

            # Apply percentage discount
            effective_price_unit = line.price_unit * (1 - discount_pct)
            total_price = effective_price_unit * quantity

            # Apply fixed discount
            total_price_after_fixed = max(total_price - fixed_discount, 0.0)

            # Final price per unit
            adjusted_price_unit = total_price_after_fixed / quantity if quantity else 0.0

            # Compute taxes
            taxes = line.tax_ids.compute_all(
                adjusted_price_unit,
                quantity=quantity,
                product=line.product_id,
                partner=line.partner_id
            )

            line.price_subtotal = taxes['total_excluded']
            line.price_total = taxes['total_included']

    @api.depends('account_id', 'company_id', 'discount', 'fixed_discount', 'price_unit', 'quantity', 'currency_rate')
    def _compute_discount_allocation_needed(self):
        for line in self:
            line.discount_allocation_dirty = True
            discount_allocation_account = line.move_id._get_discount_allocation_account()

            if (
                    not discount_allocation_account or
                    line.display_type != 'product' or
                    (
                            line.currency_id.is_zero(line.discount) and
                            line.currency_id.is_zero(line.fixed_discount)
                    )
            ):
                line.discount_allocation_needed = False
                continue

            percent_discount_currency = line.currency_id.round(
                line.move_id.direction_sign * line.quantity * line.price_unit * (line.discount or 0.0) / 100.0
            )

            fixed_discount_currency = line.currency_id.round(
                line.move_id.direction_sign * (line.fixed_discount or 0.0)
            )

            total_discount_currency = percent_discount_currency + fixed_discount_currency

            discount_allocation_needed = {}

            decrease_key = frozendict({
                'account_id': line.account_id.id,
                'move_id': line.move_id.id,
                'currency_rate': line.currency_rate,
            })
            discount_allocation_needed[decrease_key] = {
                'display_type': 'discount',
                'name': _("Discount"),
                'amount_currency': total_discount_currency,
            }

            increase_key = frozendict({
                'move_id': line.move_id.id,
                'account_id': discount_allocation_account.id,
                'currency_rate': line.currency_rate,
            })
            discount_allocation_needed[increase_key] = {
                'display_type': 'discount',
                'name': _("Discount"),
                'amount_currency': -total_discount_currency,
            }

            line.discount_allocation_needed = {
                k: frozendict(v) for k, v in discount_allocation_needed.items()
            }

    def _prepare_base_line_for_taxes_computation(self):
        self.ensure_one()
        unit = self.price_unit * (1 - (self.discount or 0.0) / 100.0)
        total = (unit * self.quantity) - (self.fixed_discount or 0.0)
        total = max(total, 0.0)
        adjusted_unit = total / self.quantity if self.quantity else 0.0

        return self.env['account.tax']._prepare_base_line_for_taxes_computation(
            self,
            tax_ids=self.tax_ids,
            price_unit=adjusted_unit,
            quantity=self.quantity,
            discount=0.0,
            partner_id=self.partner_id,
            currency_id=self.currency_id,
            rate=self.currency_rate,
        )
