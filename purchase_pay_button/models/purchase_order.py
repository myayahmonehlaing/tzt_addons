from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.model
    def create(self, vals):
        move = super().create(vals)
        _logger.info(" Invoice created with origin: %s", move.invoice_origin)
        return move

    def action_post(self):
        res = super().action_post()

        for move in self:
            if move.move_type == 'in_invoice' and move.invoice_origin:
                purchase_order = self.env['purchase.order'].search([
                    ('name', '=', move.invoice_origin)
                ], limit=1)

                if purchase_order and purchase_order.payment_ids:
                    account = move.partner_id.property_account_payable_id

                    payment_lines = purchase_order.payment_ids.mapped('move_id.line_ids').filtered(
                        lambda l: l.account_id == account and not l.reconciled and l.debit > 0
                    )

                    invoice_lines = move.line_ids.filtered(
                        lambda l: l.account_id == account and not l.reconciled and l.credit > 0
                    )

                    lines_to_reconcile = payment_lines + invoice_lines
                    if lines_to_reconcile:
                        _logger.info("Reconciling payment lines and invoice lines for vendor bill %s", move.name)
                        lines_to_reconcile.reconcile()

        return res


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    purchase_order_id = fields.Many2one('purchase.order', string='Purchase Order')


class PurchaseOrderPaymentWizard(models.TransientModel):
    _name = 'purchase.order.payment.wizard'
    _description = 'Purchase Order Payment Wizard'

    purchase_order_id = fields.Many2one('purchase.order', string="Purchase Order", required=True)
    partner_id = fields.Many2one('res.partner', string="Supplier", related="purchase_order_id.partner_id",
                                 readonly=True)
    amount = fields.Float(string="Amount", required=True)
    currency_id = fields.Many2one('res.currency', string="Currency", related="purchase_order_id.currency_id",
                                  readonly=True)

    payment_method_id = fields.Many2one('account.payment.method', string="Payment Method", required=True,
                                        default=lambda self: self._get_default_manual_payment_method())

    @api.model
    def _get_default_manual_payment_method(self):
        manual_method = self.env['account.payment.method'].search([('code', '=', 'manual')], limit=1)
        return manual_method.id if manual_method else False

    @api.onchange('journal_id')
    def _onchange_payment_method_id(self):
        if self.journal_id:
            return {
                'domain': {
                    'payment_method_id': [
                        ('code', '=', 'manual'),
                        ('payment_type', '=', self.payment_type),
                        ('available_for_invoices', '=', True),
                        ('company_id', '=', self.journal_id.company_id.id)
                    ]
                }
            }

    partner_bank_id = fields.Many2one('res.partner.bank', string="Recipient Bank Account")
    payment_date = fields.Date(string="Payment Date", default=fields.Date.context_today, required=True)
    journal_id = fields.Many2one('account.journal', string="Journal", required=True)

    communication = fields.Char(string="Memo", default=lambda self: self.env.context.get('default_communication'))
    payment_type = fields.Selection([('inbound', 'Inbound'), ('outbound', 'Outbound')], string="Payment Type",
                                    default="outbound")
    partner_type = fields.Selection([('customer', 'Customer'), ('supplier', 'Supplier')], string="Partner Type",
                                    default="supplier")

    source_amount = fields.Float(string="Source Amount", readonly=True)
    source_amount_currency = fields.Many2one('res.currency', string="Source Amount Currency", readonly=True)
    source_currency_id = fields.Many2one('res.currency', string="Source Currency", readonly=True)
    company_id = fields.Many2one('res.company', string="Company", readonly=True, default=lambda self: self.env.company)

    custom_user_amount = fields.Float(string="Custom User Amount")
    custom_user_currency_id = fields.Many2one('res.currency', string="Custom User Currency")
    can_edit_wizard = fields.Boolean(string="Can Edit Wizard", default=True)
    can_group_payments = fields.Boolean(string="Can Group Payments", default=False)
    early_payment_discount_mode = fields.Boolean(string="Early Payment Discount Mode", default=False)
    installments_mode = fields.Boolean(string="Installments Mode", default=False)
    installments_switch_amount = fields.Float(string="Installment Switch Amount")
    installments_switch_html = fields.Html(string="Installment Switch HTML")
    hide_writeoff_section = fields.Boolean(string="Hide Write-Off Section", default=False)
    writeoff_is_exchange_account = fields.Boolean(string="Write-Off is Exchange Account", default=False)

    payment_difference = fields.Float(string="Payment Difference", readonly=True, compute="_compute_payment_difference",
                                      store=True)

    payment_difference_handling = fields.Selection([
        ('open', 'Keep Open'),
        ('reconcile', 'Reconcile')
    ], string="Difference Handling", default="open")

    require_partner_bank_account = fields.Boolean(string="Require Partner Bank Account", default=False)
    show_partner_bank_account = fields.Boolean(string="Show Partner Bank Account", default=False)
    group_payment = fields.Boolean(string="Group Payment", default=False)

    @api.depends('amount', 'purchase_order_id.amount_total')
    def _compute_payment_difference(self):
        for wizard in self:
            po_total = wizard.purchase_order_id.amount_total or 0.0
            entered = wizard.amount or 0.0
            wizard.payment_difference = round(po_total - entered, 2) if entered < po_total else 0.0

    @api.constrains('payment_difference', 'payment_difference_handling')
    def _check_payment_difference_handling(self):
        for wizard in self:
            if wizard.payment_difference and not wizard.payment_difference_handling:
                raise ValidationError(_("Please specify how to handle the payment difference: Reconcile or Keep Open."))

    @api.onchange('amount')
    def _onchange_amount(self):
        if self.purchase_order_id:
            po_total = self.purchase_order_id.amount_total or 0.0
            entered = self.amount or 0.0
            self.payment_difference = round(po_total - entered, 2) if entered < po_total else 0.0
            if self.payment_difference == 0.0:
                self.payment_difference_handling = False

    @api.onchange('partner_id')
    def _onchange_partner_bank(self):
        if self.partner_id and self.partner_id.bank_ids:
            self.partner_bank_id = self.partner_id.bank_ids[0].id
            self.show_partner_bank_account = True
            self.require_partner_bank_account = True
        else:
            self.partner_bank_id = False
            self.show_partner_bank_account = False
            self.require_partner_bank_account = False
        return {'domain': {'partner_bank_id': [('partner_id', '=', self.partner_id.id)]}}

    def action_create_payment(self):
        self.ensure_one()

        if self.amount <= 0:
            raise UserError(_("Payment amount must be greater than zero."))
        if not self.journal_id:
            raise UserError(_("You must select a payment journal."))

        try:
            payment_vals = {
                'payment_type': self.payment_type,
                'partner_type': self.partner_type,
                'partner_id': self.partner_id.id,
                'amount': self.amount,
                'currency_id': self.currency_id.id,
                'company_id': self.company_id.id,
                'payment_method_id': self.payment_method_id.id,
                'journal_id': self.journal_id.id,
                'date': self.payment_date,
                'memo': self.communication or self.purchase_order_id.name,
                'payment_reference': self.communication or self.purchase_order_id.name,
                'partner_bank_id': self.partner_bank_id.id if self.partner_bank_id else False,
                'purchase_order_id': self.purchase_order_id.id,
            }

            payment = self.env['account.payment'].create(payment_vals)
            payment.action_post()
            self.purchase_order_id._compute_payment_count()

            # 🔁 Try reconciling all posted invoices after payment
            self.purchase_order_id.auto_reconcile_po_invoices()

            if hasattr(self.env.user, 'notify_info'):
                self.env.user.notify_info(_("Payment successfully created and linked to invoice(s)."))

            return {'type': 'ir.actions.act_window_close'}

        except Exception as e:
            _logger.exception("Payment processing failed for PO %s", self.purchase_order_id.id)
            raise UserError(_("Payment processing failed. Reason: %s") % str(e))


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    payment_ids = fields.One2many('account.payment', 'purchase_order_id', string='Payments')
    payment_count = fields.Integer(compute='_compute_payment_count', store=True)

    @api.depends('payment_ids')
    def _compute_payment_count(self):
        for order in self:
            order.payment_count = len(order.payment_ids)

    def action_view_payments(self):
        self.ensure_one()
        return {
            'name': 'Payments',
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'view_mode': 'list,form',
            'domain': [('purchase_order_id', '=', self.id), ('payment_type', '=', 'outbound')],
            'context': {
                'default_partner_id': self.partner_id.id,
                'default_payment_type': 'outbound',
                'default_purchase_order_id': self.id,
            }
        }

    def _get_payment_reference(self):
        bill = self.invoice_ids.filtered(lambda inv: inv.move_type == 'in_invoice')
        return bill[0].name if bill and bill[0].name else self.name or _("Payment for PO")

    def action_pay_order_primary(self):
        self.ensure_one()

        if not self.partner_id:
            raise UserError(_("No supplier is associated with this Purchase Order."))
        if self.amount_total <= 0:
            raise UserError(_("The Purchase Order amount must be greater than zero to proceed with payment."))

        default_journal = self.env['account.journal'].search([
            ('type', '=', 'bank'),
            ('company_id', '=', self.company_id.id)
        ], limit=1)

        if not default_journal:
            raise UserError(_("No bank journal found. Please configure a payment journal for this company."))

        return {
            'name': _('Register Payment'),
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order.payment.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_purchase_order_id': self.id,
                'default_partner_id': self.partner_id.id,
                'default_amount': self.amount_total,
                'default_currency_id': self.currency_id.id,
                'default_payment_date': fields.Date.context_today(self),
                'default_payment_type': 'outbound',
                'default_partner_type': 'supplier',
                'default_custom_user_amount': self.amount_total,
                'default_custom_user_currency_id': self.currency_id.id,
                'default_journal_id': default_journal.id,
                'default_communication': self._get_payment_reference(),
                'default_partner_bank_id': self.partner_id.bank_ids[0].id if self.partner_id.bank_ids else False,
                'default_show_partner_bank_account': bool(self.partner_id.bank_ids),
                'default_require_partner_bank_account': bool(self.partner_id.bank_ids),
            },
        }

    def auto_reconcile_po_invoices(self):
        for invoice in self.invoice_ids.filtered(lambda inv: inv.move_type == 'in_invoice' and inv.state == 'posted'):
            invoice._auto_reconcile_with_po_payments()
