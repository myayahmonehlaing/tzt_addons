from odoo import models, fields, api

class MaintenanceBill(models.Model):
    _name = 'property.maintenance.bill'
    _description = 'Maintenance Bill'

    name = fields.Char(required=True)
    request_id = fields.Many2one('property.maintenance.request', string="Related Request", required=True)
    bill_date = fields.Date(default=fields.Date.today, string="Bill Date")
    line_ids = fields.One2many('property.maintenance.line', 'bill_id', string="Bill Lines")
    total_amount = fields.Float(compute="_compute_total", store=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('paid', 'Paid'),
        ('cancelled', 'Cancelled')
    ], default='draft', tracking=True)

    @api.depends('line_ids.amount')
    def _compute_total(self):
        for record in self:
            record.total_amount = sum(line.amount for line in record.line_ids)
