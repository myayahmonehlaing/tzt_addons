from odoo import models
import re


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def get_product_name_and_description(self):
        self.ensure_one()
        name = self.name or ''
        # Remove [CODE] at beginning
        cleaned_name = re.sub(r'^\[.*?\]\s*', '', name)
        lines = cleaned_name.split('\n')
        product_name = lines[0] if lines else ''
        description_lines = lines[1:] if len(lines) > 1 else []
        return product_name, description_lines
