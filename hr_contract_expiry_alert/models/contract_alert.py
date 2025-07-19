from odoo import models, fields, api
from datetime import datetime, timedelta

class HrContract(models.Model):
    _inherit = 'hr.contract'

    def _check_expiring_contracts(self):
        today = fields.Date.context_today(self)
        expire_date = today + timedelta(days=3)

        contracts_expiring_soon = self.search([
            ('date_end', '=', expire_date)
        ])

        admin_user = self.env.ref('base.user_admin')

        for contract in contracts_expiring_soon:
            # Check if activity already exists for this contract and user to avoid duplicates
            existing_activity = self.env['mail.activity'].search([
                ('res_id', '=', contract.id),
                ('res_model', '=', 'hr.contract'),
                ('user_id', '=', admin_user.id),
                ('activity_type_id', '=', self.env.ref('mail.mail_activity_data_todo').id),
                ('date_deadline', '=', expire_date),
            ])
            if existing_activity:
                continue  # Skip creating duplicate activity

            # Create To-Do activity for admin
            self.env['mail.activity'].create({
                'res_id': contract.id,
                'res_model_id': self.env['ir.model']._get('hr.contract').id,
                'user_id': admin_user.id,
                'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,  # To-Do type
                'summary': 'Update contract expiring soon',
                'note': f'The contract for {contract.employee_id.name} expires on {contract.date_end}. Please review and update it.',
                'date_deadline': expire_date,
            })
