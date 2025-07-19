from odoo import models, fields, api
from odoo.exceptions import ValidationError


class SaleAgreement(models.Model):
    _name = 'sale.agreement'
    _description = 'Sale Agreement'
    _inherit = ['mail.thread']

    name = fields.Char(string="Agreement Reference", tracking=True, readonly=True, copy=False, default="New")
    title = fields.Char(string="Agreement", readonly=True, copy=False)
    customer_id = fields.Many2one('res.partner', string="Customer", required=True, tracking=True)
    pricelist_id = fields.Many2one('product.pricelist', string="Pricelist", required=True, tracking=True)
    reference = fields.Char(string="Reference", placeholder="e.g. SO0025")
    date = fields.Date(string="Agreement Date", default=fields.Date.today, tracking=True)
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company, tracking=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('closed', 'Closed'),
        ('cancelled', 'Cancelled'),
    ], default='draft', tracking=True)

    line_ids = fields.One2many('sale.agreement.line', 'agreement_id', string="Agreement Lines")
    sale_order_ids = fields.One2many('sale.order', 'agreement_id', string="Related Sale Orders")
    order_count = fields.Integer(string="Sale Orders", compute="_compute_order_count")

    @api.model
    def _get_sequence(self):
        return self.env['ir.sequence'].next_by_code('sale.agreement') or 'SA00001'

    def action_confirm(self):
        for record in self:
            if record.name == "New":
                record.name = self._get_sequence()
            record.write({'state': 'confirmed'})

    def action_new_quotation(self):
        order_lines = [(0, 0, {
            'product_id': line.product_id.id,
            'product_uom_qty': line.product_qty,
            'price_unit': line.price_unit,
            'product_uom': line.product_uom_id.id,
        }) for line in self.line_ids]

        sale_order = self.env['sale.order'].create({
            'partner_id': self.customer_id.id,
            'pricelist_id': self.pricelist_id.id,
            'company_id': self.company_id.id,
            'agreement_id': self.id,
            'order_line': order_lines,
        })

        return {
            'name': 'New Quotation',
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'view_mode': 'form',
            'target': 'current',
            'res_id': sale_order.id,
        }

    def action_close(self):
        self.write({'state': 'closed'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_reset_to_draft(self):
        self.write({'state': 'draft'})

    def _compute_order_count(self):
        for record in self:
            record.order_count = self.env['sale.order'].search_count([('agreement_id', '=', record.id)])

    def action_sale_order_list(self):
        return {
            'name': 'Sale Orders',
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'view_mode': 'list,form',
            'domain': [('agreement_id', '=', self.id)],
            'context': {
                'default_agreement_id': self.id
            }
        }


class SaleAgreementLine(models.Model):
    _name = 'sale.agreement.line'
    _description = 'Sale Agreement Line'

    agreement_id = fields.Many2one('sale.agreement', string="Sale Agreement", required=True)
    product_id = fields.Many2one('product.product', string="Product", required=True)
    product_qty = fields.Float(string="Quantity", default=1)
    product_uom_id = fields.Many2one('uom.uom', string="UoM", required=True,
                                     default=lambda self: self.env.ref('uom.product_uom_unit').id)
    price_unit = fields.Float(string="Unit Price", readonly=False)
    qty_ordered = fields.Float(string="Sold Quantity", readonly=True, compute="_compute_qty_ordered")
    remaining_qty = fields.Float(string="Remaining Quantity", readonly=True, compute="_compute_remaining_qty")

    @api.depends('product_qty', 'qty_ordered')
    def _compute_remaining_qty(self):
        for line in self:
            line.remaining_qty = max(line.product_qty - line.qty_ordered, 0)

    @api.depends('agreement_id.sale_order_ids')
    def _compute_qty_ordered(self):
        for line in self:
            sale_lines = self.env['sale.order.line'].search([
                ('product_id', '=', line.product_id.id),
                ('order_id.agreement_id', '=', line.agreement_id.id),
                ('order_id.state', 'in', ['sale', 'done'])
            ])
            line.qty_ordered = sum(sale_lines.mapped('product_uom_qty'))

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.product_uom_id = self.product_id.uom_id
            self.price_unit = self.product_id.lst_price


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    agreement_id = fields.Many2one('sale.agreement', string="Sale Agreement", tracking=True)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        agreement_id = self.env.context.get('default_agreement_id')
        if agreement_id:
            res['agreement_id'] = agreement_id

        return res

    @api.onchange('agreement_id')
    def _onchange_agreement_id(self):
        if self.agreement_id:
            order_lines = []
            for line in self.agreement_id.line_ids:
                order_lines.append((0, 0, {
                    'product_id': line.product_id.id,
                    'product_uom_qty': line.product_qty,
                    'price_unit': line.price_unit,
                    'product_uom': line.product_uom_id.id,
                    'name': line.product_id.name or '',
                }))
            self.order_line = order_lines
            self.partner_id = self.agreement_id.customer_id.id
            self.pricelist_id = self.agreement_id.pricelist_id.id
        else:
            self.order_line = [(5, 0, 0)]

    @api.onchange('company_id')
    def _onchange_company_id_warning(self):
        if self.company_id and self._origin.company_id and self.company_id != self._origin.company_id:
            return {
                'warning': {
                    'title': "Warning for the change of your quotation's company",
                    'message': (
                        "Changing the company of an existing quotation might need some manual adjustments "
                        "in the details of the lines. You might consider updating the prices."
                    )
                }
            }
