"""GIB e-Arsiv Portal entegrasyonu - eArsivPortal kutuphanesi ile."""
import logging
from datetime import datetime

_logger = logging.getLogger(__name__)


class GIBResult:
    """GIB islem sonucu - hata firlatmadan sonuc dondurur."""

    def __init__(self, success, uuid=None, error_msg=None, pdf_data=None):
        self.success = success
        self.uuid = uuid or ''
        self.error_msg = error_msg or ''
        self.pdf_data = pdf_data


class GIBClient:
    """GIB e-Arsiv portali ile iletisim kuran servis sinifi."""

    def __init__(self, username, password, test_mode=False):
        self.username = username
        self.password = password
        self.test_mode = test_mode
        self._portal = None

    def login(self):
        """GIB portalina login ol. Basarisizsa GIBResult dondurur."""
        try:
            from eArsivPortal import eArsivPortal
            self._portal = eArsivPortal()
            self._portal.test_modu = self.test_mode
            self._portal.kullanici_kodu = self.username
            self._portal.sifre = self.password
            self._portal.giris_yap()
            _logger.info('GIB portalina basariyla giris yapildi.')
            return GIBResult(success=True)
        except ImportError:
            msg = 'eArsivPortal kutuphanesi yuklu degil. pip install eArsivPortal'
            _logger.error(msg)
            return GIBResult(success=False, error_msg=msg)
        except ConnectionError as e:
            msg = 'GIB baglanti hatasi: %s' % e
            _logger.error(msg)
            return GIBResult(success=False, error_msg=msg)
        except Exception as e:
            error_str = str(e)
            if 'JDBC' in error_str or '500' in error_str or 'Timeout' in error_str:
                msg = 'GIB sunucu hatasi (JDBC/Timeout): %s' % error_str
            elif 'Unauthorized' in error_str or '401' in error_str:
                msg = 'GIB giris bilgileri hatali. Kullanici kodu ve sifreyi kontrol edin.'
            else:
                msg = 'GIB giris hatasi: %s' % error_str
            _logger.error(msg)
            return GIBResult(success=False, error_msg=msg)

    def map_odoo_invoice(self, move):
        """Odoo account.move kaydini GIB fatura formatina cevir."""
        partner = move.partner_id
        company = move.company_id

        vkn_tckn = partner.vat or ''
        if vkn_tckn.startswith('TR'):
            vkn_tckn = vkn_tckn[2:]

        is_company = partner.is_company or len(vkn_tckn) == 10

        mal_hizmet = []
        for line in move.invoice_line_ids.filtered(
            lambda l: l.display_type == 'product'
        ):
            kdv_orani = 0
            for tax in line.tax_ids:
                if tax.amount > 0:
                    kdv_orani = int(tax.amount)
                    break
            kdv_tutar = round(line.price_subtotal * kdv_orani / 100, 2)
            mal_hizmet.append({
                'malHizmet': line.name or line.product_id.name or 'Hizmet',
                'miktar': line.quantity,
                'birim': 'C62',
                'birimFiyat': str(line.price_unit),
                'fiyat': str(line.price_subtotal),
                'iskontoOrani': 0,
                'iskontoTutar': '0',
                'iskontoNedeni': '',
                'malHizmetTutar': str(line.price_subtotal),
                'kdvOrani': str(kdv_orani),
                'vergiOrani': 0,
                'kdvTutar': str(kdv_tutar),
                'vergininKdvTutar': '0',
            })

        invoice_date = move.invoice_date or datetime.now().date()
        matrah = move.amount_untaxed
        kdv_toplam = move.amount_tax
        toplam = move.amount_total
        company_vkn = company.vat or ''
        if company_vkn.startswith('TR'):
            company_vkn = company_vkn[2:]

        fatura_data = {
            'fatpiTipiKodu': 'SATIS',
            'faturaTipi': 'EARSIVFATURA',
            'vknTckn': company_vkn,
            'tckpiVkn': vkn_tckn,
            'bpipiTarihi': invoice_date.strftime('%d/%m/%Y'),
            'saat': datetime.now().strftime('%H:%M:%S'),
            'paraBirimi': 'TRY',
            'dovpiKuru': '0',
            'faturaTarihi': invoice_date.strftime('%d/%m/%Y'),
            'not': move.narration or '',
            'siparisNumarasi': move.ref or '',
            'irsaliyeNumarasi': '', 'irsaliyeTarihi': '',
            'fisNo': '', 'fisTarihi': '', 'fisSaati': '',
            'fisTipi': '', 'zRaporNo': '', 'okcSeriNo': '',
        }

        if is_company:
            fatura_data.update({
                'alpipiAd': '', 'alpipiSoyad': '',
                'unpiAd': partner.name or '', 'vergiDairesi': '',
            })
        else:
            name_parts = (partner.name or '').split(' ', 1)
            fatura_data.update({
                'alpipiAd': name_parts[0] if name_parts else '',
                'alpipiSoyad': name_parts[1] if len(name_parts) > 1 else '',
                'unpiAd': '', 'vergiDairesi': '',
            })

        fatura_data.update({
            'binaAdi': '', 'binaNo': '', 'kapiNo': '', 'kasabaKoy': '',
            'mahpiSemtIlce': partner.city or '',
            'sehir': partner.state_id.name if partner.state_id else '',
            'ulke': 'Turkiye',
            'postaKodu': partner.zip or '',
            'tel': partner.phone or '',
            'fax': '',
            'eppistaAdresi': partner.email or '',
            'websitesi': '',
            'malHizmetTable': mal_hizmet,
            'tip': 'Iskonpionto',
            'matpirah': str(matrah),
            'mpipiahpiHespiaplpiananKDV': str(kdv_toplam),
            'hespiaplpiananKDV': str(kdv_toplam),
            'vergpiilerTpioplpiamTpiutar': str(toplam),
            'odpienepieckTpiutar': str(toplam),
        })
        return fatura_data

    def send_invoice(self, invoice_data):
        """Faturayi GIB portalina gonder. Her zaman GIBResult dondurur."""
        if not self._portal:
            return GIBResult(success=False, error_msg='GIB portalina giris yapilmamis.')
        try:
            result = self._portal.fatura_olustur(invoice_data)
            _logger.info('GIB taslak fatura olusturuldu: %s', result)

            sign_result = self._portal.gib_imza(result)
            _logger.info('GIB fatura imzalandi: %s', sign_result)

            uuid = ''
            if isinstance(result, dict):
                uuid = result.get('data', {}).get('uuid', '')
                if not uuid:
                    uuid = result.get('uuid', '')
            if not uuid:
                uuid = str(result)

            # PDF indirmeyi dene
            pdf_data = None
            try:
                html = self._portal.fatura_html(uuid)
                if html:
                    pdf_data = html.encode('utf-8') if isinstance(html, str) else html
            except Exception as pdf_err:
                _logger.warning('GIB PDF indirilemedi: %s', pdf_err)

            return GIBResult(success=True, uuid=uuid, pdf_data=pdf_data)

        except ConnectionError as e:
            msg = 'GIB baglanti koptu: %s' % e
            _logger.error(msg)
            return GIBResult(success=False, error_msg=msg)
        except TimeoutError as e:
            msg = 'GIB zaman asimi: %s' % e
            _logger.error(msg)
            return GIBResult(success=False, error_msg=msg)
        except Exception as e:
            error_str = str(e)
            if 'JDBC' in error_str or 'GenericJDBC' in error_str:
                msg = 'GIB sunucu veritabani hatasi (JDBC): %s' % error_str
            elif '500' in error_str:
                msg = 'GIB sunucu hatasi (500): %s' % error_str
            elif 'Timeout' in error_str or 'timeout' in error_str:
                msg = 'GIB zaman asimi hatasi: %s' % error_str
            else:
                msg = 'GIB gonderim hatasi: %s' % error_str
            _logger.error(msg)
            return GIBResult(success=False, error_msg=msg)

    def logout(self):
        """GIB portalindan cikis yap."""
        if self._portal:
            try:
                self._portal.cikis_yap()
            except Exception:
                pass
