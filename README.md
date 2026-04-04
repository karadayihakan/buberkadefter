# Buberka Defter - Odoo 18 Community Custom Modules

Odoo 18 Community icin ozel gelistirilmis moduller.

## Custom Moduller

### kdv_dashboard
Faturalama menusune ay bazli KDV ozet sayfasi ekler.
- Aylik / ceyreklik / yillik KDV hesaplama
- Hesaplanan KDV (satis), indirilecek KDV (alis), odenecek net KDV
- En eski faturadan itibaren tum aylari listeler

### portal_multi_company
Portal kullanicisinin birden fazla sirketin fatura ve siparislerini gormesini saglar.
- Ayni e-posta ile birden fazla sirkete bagli kontaklar icin
- Fatura ve siparis listelerini tum iliskili sirketlerden gosterir
- Kontak gorunum adi: "Kisi Adi (Sirket)" formatinda

### invoice_earsiv
Fatura formuna E-Arsiv PDF ekleme ozelligi ekler.
- Fatura formunda PDF yukleme alani
- Yuklenen PDF icin indirme butonu
- GIB e-arsiv portalindan indirilen PDF'leri faturaya iliskilendirir

## Kurulum

```bash
# Modulleri /opt/odoo/custom_addons/ altina kopyala
# addons_path'e ekle (/etc/odoo.conf)
# Odoo'yu yeniden baslat
sudo systemctl restart odoo
# Uygulamalar'dan modulu yukle
```

## Bagimliliklar

- Odoo 18.0 Community
- account (Faturalama)
- spreadsheet_dashboard (KDV Dashboard icin)

## Lisans

LGPL-3
