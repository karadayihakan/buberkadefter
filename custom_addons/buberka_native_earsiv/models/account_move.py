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
                and move.gib_status == 'draft'
            )

    def action_send_to_gib(self):
        """GIB e-Arsiv portalina fatura gonder."""
        self.ensure_one()
        if not self.gib_can_send:
            raise UserError('Bu fatura GIB portalina gonderilemez.')

        company = self.company_id
        if not company.gib_user or not company.gib_password:
            raise UserError(
                'GIB kullanici bilgileri tanimlanmamis. '
                'Ayarlar > Sirketler > GIB Kullanici Kodu ve Sifre alanlari doldurulmali.'
            )

        try:
            from ..services.gib_client import GIBClient
            client = GIBClient(company.gib_user, company.gib_password)
            client.login()

            invoice_data = client.map_odoo_invoice(self)
            uuid = client.send_invoice(invoice_data)

            self.write({
                'gib_uuid': uuid,
                'gib_status': 'sent',
                'gib_error_message': False,
            })

            # Download and attach PDF
            try:
                pdf_data = client.download_pdf(uuid)
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
            except Exception as pdf_err:
                _logger.warning('GIB PDF indirilemedi: %s', pdf_err)

        except ImportError:
            raise UserError(
                'fatura kutuphanesi yuklu degil. '
                'Sunucuda: pip install fatura komutunu calistirin.'
            )
        except Exception as e:
            self.write({
                'gib_status': 'error',
                'gib_error_message': str(e),
            })
            _logger.error('GIB gonderim hatasi: %s', e)
            raise UserError('GIB gonderim hatasi: %s' % e)

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

    def _get_report_base_filename(self):
        """Eger GIB PDF varsa dosya adini override et."""
        if self.gib_pdf_id:
            return 'e-arsiv-%s' % self.name.replace('/', '-')
        return super()._get_report_base_filename()
