from odoo import fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    earsiv_pdf = fields.Binary(string='E-Arsiv PDF', attachment=True)
    earsiv_pdf_name = fields.Char(string='E-Arsiv PDF Dosya Adi')
    earsiv_uploaded = fields.Boolean(compute='_compute_earsiv_uploaded')

    def _compute_earsiv_uploaded(self):
        for rec in self:
            rec.earsiv_uploaded = bool(rec.earsiv_pdf)

    def action_download_earsiv(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content?model=account.move&id=%d&field=earsiv_pdf&filename_field=earsiv_pdf_name&download=true' % self.id,
            'target': 'new',
        }
