import base64
import logging
from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    gib_uuid = fields.Char(
        string='ETTN', readonly=True, copy=False,
        help='GIB tarafindan atanan benzersiz fatura numarasi',
    )
    gib_status = fields.Selection([
        ('draft', 'Taslak'),
        ('sent', 'Gonderildi'),
        ('error', 'Hata'),
    ], string='GIB Durumu', default='draft', readonly=True, copy=False)
    gib_error_message = fields.Text(
        string='GIB Hata Mesaji', readonly=True, copy=False,
    )
    gib_pdf_id = fields.Many2one(
        'ir.attachment', string='GIB e-Arsiv PDF',
        readonly=True, copy=False,
    )
    gib_can_send = fields.Boolean(
        compute='_compute_gib_can_send',
    )

    @api.depends('state', 'move_type', 'gib_status')
    def _compute_gib_can_send(self):
        for move in self:
            move.gib_can_send = (
                move.state == 'posted'
                and move.move_type in ('out_invoice', 'out_refund')
                and move.gib_status in ('draft', 'error')
            )

    def action_send_to_gib(self):
        """GIB e-Arsiv portalina fatura gonder. Ekrani kilitlemez."""
        self.ensure_one()
        if not self.gib_can_send:
            raise UserError('Bu fatura GIB portalina gonderilemez.')

        company = self.company_id
        if not company.gib_user or not company.gib_password:
            raise UserError(
                'GIB kullanici bilgileri tanimlanmamis. '
                'Ayarlar > Sirketler > GIB Kullanici Kodu ve Sifre doldurulmali.'
            )

        from ..services.gib_client import GIBClient

        client = GIBClient(company.gib_user, company.gib_password)

        # Login
        login_result = client.login()
        if not login_result.success:
            self.write({
                'gib_status': 'error',
                'gib_error_message': login_result.error_msg,
            })
            self.message_post(
                body='<b>GIB Giris Hatasi:</b> %s' % login_result.error_msg,
                message_type='comment',
                subtype_xmlid='mail.mt_note',
            )
            return  # Ekrani kilitleme, sadece chatter'a yaz

        # Map and send
        try:
            invoice_data = client.map_odoo_invoice(self)
        except Exception as e:
            msg = 'Fatura verisi hazirlama hatasi: %s' % e
            self.write({
                'gib_status': 'error',
                'gib_error_message': msg,
            })
            self.message_post(
                body='<b>GIB Veri Hatasi:</b> %s' % msg,
                message_type='comment',
                subtype_xmlid='mail.mt_note',
            )
            return

        send_result = client.send_invoice(invoice_data)

        if send_result.success:
            self.write({
                'gib_uuid': send_result.uuid,
                'gib_status': 'sent',
                'gib_error_message': False,
            })
            self.message_post(
                body='<b>GIB e-Arsiv fatura basariyla gonderildi.</b><br/>'
                     'ETTN: %s' % send_result.uuid,
                message_type='comment',
                subtype_xmlid='mail.mt_note',
            )

            # PDF varsa ekle
            if send_result.pdf_data:
                attachment = self.env['ir.attachment'].create({
                    'name': 'e-arsiv-%s.pdf' % self.name.replace('/', '-'),
                    'type': 'binary',
                    'datas': base64.b64encode(send_result.pdf_data),
                    'res_model': 'account.move',
                    'res_id': self.id,
                    'mimetype': 'application/pdf',
                })
                self.gib_pdf_id = attachment.id
        else:
            self.write({
                'gib_status': 'error',
                'gib_error_message': send_result.error_msg,
            })
            self.message_post(
                body='<b>GIB Gonderim Hatasi:</b> %s' % send_result.error_msg,
                message_type='comment',
                subtype_xmlid='mail.mt_note',
            )
            # Ekrani kilitleme! Hata chatter'da gorunur.

        # Logout
        client.logout()

    def action_download_gib_pdf(self):
        """GIB PDF indir."""
        self.ensure_one()
        if not self.gib_pdf_id:
            raise UserError('GIB PDF bulunamadi.')
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s?download=true' % self.gib_pdf_id.id,
            'target': 'new',
        }

    def action_match_from_gib(self):
        """GIB portalindan faturalari cekip ref alaniyla eslestir."""
        self.ensure_one()
        if not self.ref:
            raise UserError('Musteri Referansi (ref) alani bos. GIB fatura numarasi girilmeli.')
        if self.gib_status == 'sent':
            raise UserError('Bu fatura zaten GIB ile eslestirilmis.')

        company = self.company_id
        if not company.gib_user or not company.gib_password:
            raise UserError('GIB kullanici bilgileri tanimlanmamis.')

        from ..services.gib_client import GIBClient
        import base64

        client = GIBClient(company.gib_user, company.gib_password)
        login_result = client.login()
        if not login_result.success:
            self.message_post(
                body='<b>GIB Giris Hatasi:</b> %s' % login_result.error_msg,
                message_type='comment', subtype_xmlid='mail.mt_note',
            )
            return

        # Son 1 yil icinde ara
        from datetime import timedelta
        end_date = fields.Date.today()
        start_date = end_date - timedelta(days=365)

        fetch_result = client.fetch_invoices(start_date, end_date)
        if not fetch_result.success:
            self.message_post(
                body='<b>GIB Fatura Listesi Hatasi:</b> %s' % fetch_result.error_msg,
                message_type='comment', subtype_xmlid='mail.mt_note',
            )
            client.logout()
            return

        gib_invoices = fetch_result.uuid  # list of dicts
        if not gib_invoices:
            self.message_post(
                body='GIB portalinda son 1 yilda fatura bulunamadi.',
                message_type='comment', subtype_xmlid='mail.mt_note',
            )
            client.logout()
            return

        # ref alanindaki GIB numarasiyla eslestir
        ref_clean = (self.ref or '').strip().upper()
        matched = None
        for gib_inv in gib_invoices:
            gib_no = ''
            if isinstance(gib_inv, dict):
                gib_no = (
                    gib_inv.get('belgeNumarasi', '')
                    or gib_inv.get('faturaNo', '')
                    or gib_inv.get('ettn', '')
                    or ''
                ).strip().upper()
                gib_ettn = (gib_inv.get('ettn', '') or '').strip()
            else:
                continue

            if ref_clean and (ref_clean in gib_no or gib_no in ref_clean):
                matched = gib_inv
                break

        if not matched:
            self.message_post(
                body='GIB portalinda "%s" referansiyla eslesen fatura bulunamadi. '
                     '%d fatura kontrol edildi.' % (self.ref, len(gib_invoices)),
                message_type='comment', subtype_xmlid='mail.mt_note',
            )
            client.logout()
            return

        # Eslesti! UUID al
        ettn = (matched.get('ettn', '') or '').strip()
        self.write({
            'gib_uuid': ettn,
            'gib_status': 'sent',
            'gib_error_message': False,
        })

        # PDF indir
        if ettn:
            pdf_data = client.download_html(ettn)
            if pdf_data:
                attachment = self.env['ir.attachment'].create({
                    'name': 'e-arsiv-%s.pdf' % self.name.replace('/', '-'),
                    'type': 'binary',
                    'datas': base64.b64encode(pdf_data),
                    'res_model': 'account.move',
                    'res_id': self.id,
                    'mimetype': 'application/pdf',
                })
                self.gib_pdf_id = attachment.id

        self.message_post(
            body='<b>GIB Eslestirme Basarili!</b><br/>'
                 'ETTN: %s<br/>GIB Fatura No: %s' % (
                     ettn, matched.get('belgeNumarasi', '')),
            message_type='comment', subtype_xmlid='mail.mt_note',
        )
        client.logout()

    def _get_report_base_filename(self):
        """Eger GIB PDF varsa dosya adini override et."""
        if self.gib_pdf_id:
            return 'e-arsiv-%s' % self.name.replace('/', '-')
        return super()._get_report_base_filename()
