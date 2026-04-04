from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = "res.partner"

    def _get_all_related_partners(self):
        self.ensure_one()
        if not self.email:
            return self
        all_contacts = self.env["res.partner"].sudo().search([
            ("email", "=", self.email),
            ("id", "!=", self.id),
        ])
        companies = all_contacts.mapped("parent_id")
        if self.parent_id:
            companies |= self.parent_id
        if self.is_company:
            companies |= self
        return self | all_contacts | companies

    def _compute_display_name(self):
        for partner in self:
            if partner.is_company or not partner.parent_id:
                partner.display_name = partner.name or ""
            else:
                partner.display_name = partner.name + " (" + partner.parent_id.name + ")"
