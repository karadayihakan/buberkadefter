# BuberkaSmart Agent Connector (Odoo)

Odoo'nuzu **değiştirmeden**, veriniz **tesisten çıkmadan** BuberkaSmart ERP-üstü
yapay zeka veri ajanına bağlar. **Salt-okuma** — hiçbir şey yazmaz/silmez.

## Kurulum (SSH gerekmez)

1. Bu uygulamayı Odoo'ya yükleyin (Uygulamalar → Yükle, veya `.zip` içe aktar).
2. **Ayarlar → BuberkaSmart Agent** bölümüne gidin.
3. BuberkaSmart panelinizden aldığınız **Bağlantı Anahtarı**'nı yapıştırın + **Tenant Kodu**'nu girin.
4. Kaydedin. Ajan artık Odoo verinize bağlı.

## Uçlar (HMAC imzalı, salt-okuma)

| Uç | İş |
|---|---|
| `GET /agent/v1/saglik` | Bağlantı sağlık kontrolü |
| `GET /agent/v1/manifest` | Sunulan araç kataloğu |
| `POST /agent/v1/tools/<ad>` | Araç çağrısı (yalnız okuma) |

### Araçlar
- `acik_siparisler` — onaylı satış siparişleri (müşteri, tutar, tarih)

## Güvenlik
- Tüm istekler HMAC-SHA256 imzalı, zaman pencereli (replay koruması).
- Bağlantı anahtarı yalnız imza doğrulamada kullanılır, dışarı gitmez.
- Hiçbir yazma/silme işlemi yoktur (KVKK güvencesi).

## Lisans
LGPL-3
