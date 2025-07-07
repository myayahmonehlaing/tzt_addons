from odoo import models, fields


class MeovvMem(models.Model):
    _name="meovv.mem"
    _description="Welcome! Meow's new member"
    _table="meovv_mem"

    name=fields.Char(string="Stage Name", required="True")
    image = fields.Binary(string="Image")
    apply_job = fields.Char(string="Apply Job")
    salary = fields.Integer(string="Expect Salary")
    dob = fields.Date(string="Date of Birth")
    nrc = fields.Char(string="NRC")
    nationality = fields.Char(string="Nationality")
    phone = fields.Char(string="Phone")
    email = fields.Char(string="Email")
    address = fields.Char(string="Address")
    gender = fields.Selection([('male', 'Male'), ('female', 'Female')], string="Gender")
    marital = fields.Selection([('single', 'Single'), ('married', 'Married')], string="Marital Status")
    objective = fields.Text(string="Career Objectives")