# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class ConsignmentOrder(models.Model):
    _name = 'consignment.order'
    _description = 'Consignment Order'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name desc'
    _check_company_auto = True

    name = fields.Char(string='Reference', tracking=True, readonly=True, copy=False, default="New")
    title = fields.Char(string="Consignment", readonly=True, copy=False)
    customer_id = fields.Many2one('res.partner', string='Customer', required=True)
    date = fields.Date(string='Date', default=fields.Date.context_today)
    pricelist_id = fields.Many2one('product.pricelist', string='Pricelist')
    payment_term_id = fields.Many2one('account.payment.term', string='Payment Terms')
    picking_type_id = fields.Many2one(
        'stock.picking.type',
        string='Operation Type',
        required=True,
        domain=[('code', '=', 'internal')],
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        required=True,
        default=lambda self: self.env.company.currency_id,
        company_dependent=True,
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
        tracking=True,
        index=True,
    )
    amount_total = fields.Monetary(
        string='Total Amount',
        compute='_compute_amount_total',
        store=True,
        currency_field='currency_id',
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)

    order_line = fields.One2many('consignment.order.line', 'order_id', string='Order Lines')
    picking_ids = fields.One2many('stock.picking', 'consignment_order_id', string='Internal Transfers')
    transfer_count = fields.Integer(string='Internal Transfers', compute='_compute_transfer_count')

    # New Sale Order Count field
    sale_order_count = fields.Integer(string='Sale Orders', compute='_compute_sale_order_count')

    @api.depends('order_line.price_subtotal')
    def _compute_amount_total(self):
        for order in self:
            order.amount_total = sum(line.price_subtotal for line in order.order_line)

    @api.depends('picking_ids')
    def _compute_transfer_count(self):
        for order in self:
            order.transfer_count = len(order.picking_ids.filtered(lambda p: p.picking_type_code == 'internal'))

    # Compute sale order count related to this consignment
    def _compute_sale_order_count(self):
        for order in self:
            order.sale_order_count = self.env['sale.order'].search_count([('consignment_id', '=', order.id)])

    @api.model
    def _get_sequence(self):
        return self.env['ir.sequence'].next_by_code('consignment.order') or 'CO00001'

    @api.model
    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)
        company = self.env.company

        if 'payment_term_id' in fields_list:
            pt = self.env['account.payment.term'].search([('name', 'ilike', 'Immediate Payment')], limit=1)
            if pt:
                defaults['payment_term_id'] = pt.id

        if 'pricelist_id' in fields_list:
            pl = self.env['product.pricelist'].search([('name', 'ilike', 'Public Pricelist')], limit=1)
            if pl:
                defaults['pricelist_id'] = pl.id

        if 'picking_type_id' in fields_list:
            pt = self.env['stock.picking.type'].search([
                ('code', '=', 'internal'),
                ('company_id', '=', company.id),
            ], limit=1)
            if pt:
                defaults['picking_type_id'] = pt.id

        defaults.setdefault('company_id', company.id)
        return defaults

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('company_id'):
                vals['company_id'] = self.env.company.id
            if vals.get('name') == 'New':
                vals['name'] = self._get_sequence()
        return super().create(vals_list)

    def action_confirm(self):
        for record in self:
            if record.name == "New":
                record.name = self._get_sequence()

            record.state = 'confirmed'

            if not record.picking_ids:
                picking_type = record.picking_type_id
                warehouse = record.company_id.consignment_warehouse_setting_id

                if not warehouse:
                    raise UserError("Please configure a consignment warehouse in company settings.")

                src_location = picking_type.default_location_src_id
                dest_location = warehouse.lot_stock_id

                for obj, label in [
                    (picking_type, "Operation Type"),
                    (src_location, "Source Location"),
                    (dest_location, "Destination Location")
                ]:
                    if obj.company_id and obj.company_id != record.company_id:
                        raise UserError(f"{label} belongs to a different company than the consignment order.")

                move_lines = []
                for line in record.order_line:
                    move_lines.append((0, 0, {
                        'name': line.product_id.name,
                        'product_id': line.product_id.id,
                        'product_uom_qty': line.quantity,
                        'product_uom': line.uom_id.id or line.product_id.uom_id.id,
                        'location_id': src_location.id,
                        'location_dest_id': dest_location.id,
                        'consignment_order_line_id': line.id,
                        'company_id': record.company_id.id,
                    }))

                picking = self.env['stock.picking'].create({
                    'partner_id': record.customer_id.id,
                    'picking_type_id': picking_type.id,
                    'location_id': src_location.id,
                    'location_dest_id': dest_location.id,
                    'consignment_order_id': record.id,
                    'origin': record.name,
                    'company_id': record.company_id.id,
                    'move_ids_without_package': move_lines,
                })
                picking.action_confirm()

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_reset_to_draft(self):
        self.write({'state': 'draft'})

    def action_internal_transfer_list(self):
        self.ensure_one()
        action = self.env.ref('stock.action_picking_tree_all').read()[0]
        action['domain'] = [
            ('consignment_order_id', '=', self.id),
            ('picking_type_code', '=', 'internal'),
        ]
        action['context'] = {'default_consignment_order_id': self.id}
        return action

    # New method to open sale orders related to this consignment
    def action_view_sale_orders(self):
        self.ensure_one()
        return {
            'name': 'Sale Orders',
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'view_mode': 'list,form',
            'domain': [('consignment_id', '=', self.id)],
            'context': {'default_consignment_id': self.id},
        }


class ConsignmentOrderLine(models.Model):
    _name = 'consignment.order.line'
    _description = 'Consignment Order Line'
    _check_company_auto = True

    order_id = fields.Many2one('consignment.order', string='Consignment Order', required=True, ondelete='cascade')
    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        related='order_id.customer_id',
        store=True,
        readonly=True,
    )
    company_id = fields.Many2one(related='order_id.company_id', string='Company', store=True, readonly=True, index=True)
    product_id = fields.Many2one('product.product', string='Product', required=True)
    quantity = fields.Float(string='Quantity', required=True, default=1.0)
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure')
    price_unit = fields.Float(string='Unit Price', required=True)
    price_subtotal = fields.Float(string='Amount', compute='_compute_price_subtotal', store=True)
    qty_ordered = fields.Float(string="Sold Quantity", readonly=True)
    remaining_qty = fields.Float(string="Remaining Quantity", readonly=True, compute="_compute_remaining_qty", store=True)

    @api.depends('quantity', 'qty_ordered')
    def _compute_remaining_qty(self):
        for line in self:
            line.remaining_qty = max(line.quantity - line.qty_ordered, 0)

    # @api.depends('order_id.customer_id', 'product_id')
    # def _compute_qty_ordered(self):
    #     for line in self:
    #         if not line.product_id or not line.order_id.customer_id:
    #             line.qty_ordered = 0.0
    #             continue
    #         sale_lines = self.env['sale.order.line'].search([
    #             ('product_id', '=', line.product_id.id),
    #             ('order_id.partner_id', '=', line.order_id.customer_id.id),
    #             ('order_id.state', 'in', ['sale', 'done']),
    #         ])
    #         line.qty_ordered = sum(sale_lines.mapped('product_uom_qty'))

    @api.depends('quantity', 'price_unit')
    def _compute_price_subtotal(self):
        for line in self:
            line.price_subtotal = line.quantity * line.price_unit

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.uom_id = self.product_id.uom_id
            self.price_unit = self.product_id.lst_price


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    consignment_order_id = fields.Many2one('consignment.order', string='Consignment Order')


class StockMove(models.Model):
    _inherit = 'stock.move'

    consignment_order_line_id = fields.Many2one('consignment.order.line', string='Consignment Order Line')


class ResCompany(models.Model):
    _inherit = 'res.company'

    consignment_warehouse_setting_id = fields.Many2one('stock.warehouse', string='Consignment Warehouse')


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    consignment_warehouse_setting_id = fields.Many2one(
        'stock.warehouse',
        string='Consignment Warehouse',
        related='company_id.consignment_warehouse_setting_id',
        readonly=False,
    )
