from odoo import models, fields

class SampleTest(models.Model):
    _name = 'sample.test'
    _description = 'Sample Test Model'

    name = fields.Char(string='Name')
    apply_job = fields.Char(string='Apply Job')
    dob = fields.Date(string='Date of Birth')
    image = fields.Binary(string='Image')
