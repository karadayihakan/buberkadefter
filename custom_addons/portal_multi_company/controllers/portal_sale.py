from odoo.addons.sale.controllers.portal import CustomerPortal
from odoo.http import request


class SalePortalMultiCompany(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if "quotation_count" in counters:
            partner = request.env.user.partner_id
            all_partners = partner._get_all_related_partners()
            values["quotation_count"] = request.env["sale.order"].sudo().search_count([
                ("partner_id", "in", all_partners.ids),
                ("state", "in", ["sent", "cancel"]),
            ])
        if "order_count" in counters:
            partner = request.env.user.partner_id
            all_partners = partner._get_all_related_partners()
            values["order_count"] = request.env["sale.order"].sudo().search_count([
                ("partner_id", "in", all_partners.ids),
                ("state", "in", ["sale", "done"]),
            ])
        return values
