import base64
from odoo import http
from odoo.http import request


class GIBPortalController(http.Controller):

    @http.route('/my/invoices/<int:invoice_id>/earsiv', type='http', auth='public', website=True)
    def download_earsiv(self, invoice_id, access_token=None, **kw):
        invoice = request.env['account.move'].sudo().browse(invoice_id)
        if not invoice.exists() or not invoice.gib_pdf_id:
            return request.redirect('/my/invoices')
        attachment = invoice.gib_pdf_id
        pdf_content = base64.b64decode(attachment.datas)
        filename = attachment.name or 'e-arsiv-%s.pdf' % invoice.name.replace('/', '-')
        return request.make_response(
            pdf_content,
            headers=[
                ('Content-Type', 'application/pdf'),
                ('Content-Disposition', 'attachment; filename=%s' % filename),
            ]
        )
