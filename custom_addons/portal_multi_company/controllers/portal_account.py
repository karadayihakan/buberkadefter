from odoo.addons.account.controllers.portal import CustomerPortal
from odoo.http import request


class CustomerPortalMultiCompany(CustomerPortal):

    def _get_invoices_domain(self):
        partner = request.env.user.partner_id
        all_partners = partner._get_all_related_partners()
        return [
            ("move_type", "in", ("out_invoice", "out_refund", "in_invoice", "in_refund", "out_receipt", "in_receipt")),
            ("partner_id", "in", all_partners.ids),
        ]

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if "invoice_count" in counters:
            partner = request.env.user.partner_id
            all_partners = partner._get_all_related_partners()
            values["invoice_count"] = request.env["account.move"].sudo().search_count([
                ("move_type", "in", ("out_invoice", "out_refund", "in_invoice", "in_refund", "out_receipt", "in_receipt")),
                ("partner_id", "in", all_partners.ids),
            ])
        return values
