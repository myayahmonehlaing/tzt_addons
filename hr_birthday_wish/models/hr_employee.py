from odoo import models, api
from datetime import date

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    @api.model
    def _create_birthday_activity(self):
        today = date.today()

        activity_type = self.env.ref('mail.mail_activity_data_todo')
        res_model = 'hr.employee'

        birthday_employees = self.search([
            ('birthday', '!=', False),
            ('birthday', 'like', f'%-{today.month:02d}-{today.day:02d}')
        ])

        if not birthday_employees:
            return

        # Only include employees with valid user_ids
        all_employees = self.search([('user_id', '!=', False)])
        other_employees = all_employees - birthday_employees

        for birthday_person in birthday_employees:
            # 1. Activity for birthday person
            existing = self.env['mail.activity'].search([
                ('res_model', '=', res_model),
                ('res_id', '=', birthday_person.id),
                ('activity_type_id', '=', activity_type.id),
                ('date_deadline', '=', today),
                ('summary', '=', 'Happy Birthday!')
            ])
            if not existing:
                self.env['mail.activity'].create({
                    'res_model': res_model,
                    'res_id': birthday_person.id,
                    'activity_type_id': activity_type.id,
                    'summary': 'Happy Birthday!',
                    'note': f'🎉 Happy Birthday, {birthday_person.name}! 🎂🎈',
                    'date_deadline': today,
                    'user_id': birthday_person.user_id.id or self.env.user.id,
                })

            # 2. Notify other employees
            for other in other_employees:
                if not other.user_id:
                    continue

                already_created = self.env['mail.activity'].search([
                    ('res_model', '=', res_model),
                    ('res_id', '=', other.id),
                    ('activity_type_id', '=', activity_type.id),
                    ('date_deadline', '=', today),
                    ('summary', '=', f"Wish {birthday_person.name} a Happy Birthday!")
                ])
                if not already_created:
                    self.env['mail.activity'].create({
                        'res_model': res_model,
                        'res_id': other.id,
                        'activity_type_id': activity_type.id,
                        'summary': f"Wish {birthday_person.name} a Happy Birthday!",
                        'note': f"🎉 Please wish {birthday_person.name} a Happy Birthday today! 🎂",
                        'date_deadline': today,
                        'user_id': other.user_id.id,
                    })
