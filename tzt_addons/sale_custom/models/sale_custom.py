from odoo import models, fields, api

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    department = fields.Many2one('hr.department', string='Department', compute='_compute_department', store=True)

    @api.depends('user_id')
    def _compute_department(self):
        for order in self:
            order.department = order.user_id.employee_id.department_id
