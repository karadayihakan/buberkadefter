import base64
from odoo import http
from odoo.http import request


class GIBPortalController(http.Controller):

    @http.route('/my/invoices/<int:invoice_id>/earsiv', type='http', auth='public', website=True)
    def download_earsiv(self, invoice_id, access_token=None, **kw):
        invoice = request.env['account.move'].sudo().browse(invoice_id)
        if not invoice.exists():
            return request.redirect('/my/invoices')

        # GIB PDF oncelikli, yoksa manuel yuklenen
        if invoice.gib_pdf_id:
            attachment = invoice.gib_pdf_id
            pdf_content = base64.b64decode(attachment.datas)
            filename = attachment.name
        elif invoice.earsiv_pdf:
            pdf_content = base64.b64decode(invoice.earsiv_pdf)
            filename = invoice.earsiv_pdf_name or 'e-arsiv-%s.pdf' % invoice.name.replace('/', '-')
        else:
            return request.redirect('/my/invoices')

        return request.make_response(
            pdf_content,
            headers=[
                ('Content-Type', 'application/pdf'),
                ('Content-Disposition', 'attachment; filename=%s' % filename),
            ]
        )
