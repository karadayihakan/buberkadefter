from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    gib_user = fields.Char(string='GIB Kullanici Kodu', groups='base.group_system')
    gib_password = fields.Char(string='GIB Sifre', groups='base.group_system')
