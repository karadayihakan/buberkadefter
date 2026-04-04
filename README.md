# Buberka Defter - Odoo 18 Community Custom Modules

Odoo 18 Community icin ozel gelistirilmis moduller.

## Custom Moduller

### buberka_native_earsiv
GIB e-Arsiv portal entegrasyonu.
- GIB portalina otomatik fatura gonderimi (eArsivPortal kutuphanesi)
- ETTN (UUID) ve durum takibi
- GIB'den PDF indirme ve faturaya ekleme
- Mevcut faturalari ref alaniyla GIB'den eslestirme
- Portal: Proforma Indir / Fatura Indir butonlari (alt alta)
- Hata yakalama: JDBC, Timeout, 500 hatalari chatter'a yazilir, ekran kilitlenmez
- Sirket ayarlarinda GIB kullanici kodu ve sifre alanlari

### kdv_dashboard
Faturalama menusune ay bazli KDV ozet sayfasi ekler.
- Aylik / ceyreklik / yillik KDV hesaplama
- Hesaplanan KDV, indirilecek KDV, odenecek net KDV
- Mobil responsive: kart gorunumu

### portal_multi_company
Portal kullanicisinin birden fazla sirketin fatura ve siparislerini gormesini saglar.

## OCA Moduller (Kurulu)

- **contract** - Tekrarlayan sozlesme ve otomatik fatura (yillik/aylik)
- **product_contract** - Urunden otomatik sozlesme olusturma
- **web_responsive** - Mobil uyumlu arayuz, ikonlu uygulama menusu

## Kurulum

```bash
# Modulleri /opt/odoo/custom_addons/ altina kopyala
# eArsivPortal kutuphanesini kur:
sudo -u odoo /opt/odoo/venv/bin/pip install eArsivPortal
# Odoo'yu yeniden baslat
sudo systemctl restart odoo
```

## Lisans

LGPL-3
