# -*- coding: utf-8 -*-
"""BuberkaSmart Agent Connector — sozlesme ucu (SALT-OKUMA).

BuberkaSmart ERP-ustu AI ajani bu uclara imzali istek atar:
    GET  /agent/v1/saglik
    GET  /agent/v1/manifest
    POST /agent/v1/tools/<ad>

Imza (sozlesme §3) BuberkaSmart agent/crypto.py ile BIREBIR AYNI:
    canonical = "\\n".join([METHOD, PATH(sorgu dahil), TS, NONCE, SHA256_HEX(body), OBO])
    signature = hex(HMAC_SHA256(secret, canonical))

Secret Odoo ir.config_parameter'da tutulur (anahtar: buberka_agent.secret).
Bu addon HICBIR SEY YAZMAZ/SILMEZ — yalniz read/search_read.
"""
import base64
import hashlib
import hmac
import json
import logging
import secrets
import time

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

# Imza toleransi (saniye) — saat kaymasina karsi
_TS_TOLERANS = 300
_SECRET_PARAM = "buberka_agent.secret"


# ---------------------------------------------------------------------------
# Imza yardimcilari (BuberkaSmart agent/crypto.py ile birebir)
# ---------------------------------------------------------------------------
def _sha256_hex(body):
    return hashlib.sha256((body or "").encode("utf-8")).hexdigest()


def _canonical(method, path, ts, nonce, body, obo=""):
    return "\n".join([
        (method or "").upper(),
        path or "",
        str(ts or ""),
        nonce or "",
        _sha256_hex(body),
        obo or "",
    ])


def _sign(secret, method, path, ts, nonce, body, obo=""):
    canonical = _canonical(method, path, ts, nonce, body, obo)
    return hmac.new(
        secret.encode("utf-8"),
        canonical.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def _json(payload, status=200):
    """Her zaman HTTP 200 + JSON govde (sozlesme: is hatalari da 200).
    Gercek tasima/imza hatalari icin status parametresi."""
    return request.make_response(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        headers=[("Content-Type", "application/json; charset=utf-8")],
        status=status,
    )


def _sign_path():
    """Imzalanan PATH: istekteki path + (varsa) ?query. BuberkaSmart tarafi
    urlsplit ile path + '?' + query kuruyor; bos query'de '?' EKLENMEZ."""
    req = request.httprequest
    path = req.path
    qs = req.query_string.decode("utf-8") if req.query_string else ""
    return path + (("?" + qs) if qs else "")


def _dogrula():
    """Gelen istegin imzasini dogrular. (ok, hata_payload) doner.
    ok True ise hata None; degilse (False, payload) ile reddet."""
    ICP = request.env["ir.config_parameter"].sudo()
    # Musteri Ayarlar'dan agent'i kapatabilir
    aktif = ICP.get_param("buberka_agent.aktif", "True")
    if str(aktif).lower() in ("false", "0", ""):
        return False, _json({"ok": False, "kod": "kapali",
                             "hata": "Agent baglantisi kapali"}, status=503)
    secret = ICP.get_param(_SECRET_PARAM)
    if not secret:
        return False, _json({"ok": False, "kod": "yapilandirma",
                             "hata": "Agent secret tanimli degil"}, status=503)

    req = request.httprequest
    h = req.headers
    tenant = h.get("X-Nazsan-Tenant", "")
    ts = h.get("X-Nazsan-Timestamp", "")
    nonce = h.get("X-Nazsan-Nonce", "")
    sig = h.get("X-Nazsan-Signature", "")
    obo = h.get("X-Nazsan-On-Behalf-Of", "")

    if not (ts and nonce and sig):
        return False, _json({"ok": False, "kod": "imza",
                             "hata": "Imza basliklari eksik"}, status=401)

    # Zaman penceresi
    try:
        if abs(int(time.time()) - int(ts)) > _TS_TOLERANS:
            return False, _json({"ok": False, "kod": "zaman",
                                 "hata": "Zaman damgasi penceresi disinda"}, status=401)
    except (TypeError, ValueError):
        return False, _json({"ok": False, "kod": "imza",
                             "hata": "Gecersiz zaman damgasi"}, status=401)

    body = req.get_data(as_text=True) or ""
    beklenen = _sign(secret, req.method, _sign_path(), ts, nonce, body, obo)
    if not hmac.compare_digest(beklenen, sig):
        return False, _json({"ok": False, "kod": "imza",
                             "hata": "Imza dogrulanamadi"}, status=401)

    return True, None


def _obo_coz():
    """X-Nazsan-On-Behalf-Of base64url(JSON) -> dict (rol icin). Hata olursa {}."""
    import base64
    raw = request.httprequest.headers.get("X-Nazsan-On-Behalf-Of", "")
    if not raw:
        return {}
    try:
        pad = "=" * (-len(raw) % 4)
        return json.loads(base64.urlsafe_b64decode(raw + pad).decode("utf-8"))
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# Odoo-ici sohbet widget'i icin JETON uretimi (BuberkaSmart widget_token ile birebir).
# Bicim: base64url(JSON{exp,iat,jti,kanal:'widget',kullanici,rol,tenant}) + '.' +
#        hex(HMAC_SHA256(secret, 'widget-jeton\n' + base64url))
# JSON SIRALI, bosluksuz. Rol: admin|staff|muhasebe|kalite|uretim.
# ---------------------------------------------------------------------------
def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _widget_jeton_uret(secret, tenant, kullanici, rol):
    simdi = int(time.time())
    payload = {
        "exp": simdi + 180, "iat": simdi, "jti": secrets.token_hex(12),
        "kanal": "widget", "kullanici": kullanici or "", "rol": rol or "staff",
        "tenant": tenant,
    }
    b64 = _b64url(json.dumps(payload, sort_keys=True, separators=(",", ":"),
                             ensure_ascii=False).encode("utf-8"))
    sig = hmac.new(secret.encode("utf-8"),
                   ("widget-jeton\n" + b64).encode("utf-8"),
                   hashlib.sha256).hexdigest()
    return b64 + "." + sig


def _odoo_rol(env):
    """Odoo kullanicisini sozlesme rolune esle. Admin -> admin, digerleri -> staff.
    (Ileride Odoo gruplarina gore muhasebe/kalite/uretim ayrilabilir.)"""
    try:
        if env.user.has_group("base.group_system"):
            return "admin"
    except Exception:
        pass
    return "staff"


# ---------------------------------------------------------------------------
# Manifest — hangi araclari sunuyoruz (BuberkaSmart bunu okur, kod degismez)
# ---------------------------------------------------------------------------
def _manifest():
    return {
        "ok": True,
        "kaynak": "odoo",
        "surum": "18.0",
        "araclar": [
            {
                "ad": "acik_siparisler",
                "aciklama": "Onaylanmis (acik) satis siparisleri: musteri, siparis no, "
                            "tutar, tarih, durum. 'Hangi siparisler acik / bekliyor' sorularinda kullan.",
                "girdi_semasi": {
                    "limit": {"tip": "sayi", "zorunlu": False,
                              "aciklama": "En fazla kac kayit (varsayilan 20, azami 100)"},
                    "musteri": {"tip": "metin", "zorunlu": False,
                                "aciklama": "Musteri adinda gecen metin (opsiyonel filtre)"},
                },
            },
            {
                "ad": "odenmemis_faturalar",
                "aciklama": "Odenmemis/kismen odenmis musteri faturalari: musteri, fatura no, "
                            "tutar, odenecek bakiye, vade tarihi. 'Kimin borcu var, tahsil "
                            "edilecek ne kadar, vadesi gecen fatura' sorularinda kullan.",
                "girdi_semasi": {
                    "limit": {"tip": "sayi", "zorunlu": False,
                              "aciklama": "En fazla kac kayit (varsayilan 20, azami 100)"},
                    "musteri": {"tip": "metin", "zorunlu": False,
                                "aciklama": "Musteri adinda gecen metin (opsiyonel filtre)"},
                    "yalniz_vadesi_gecen": {"tip": "mantiksal", "zorunlu": False,
                                "aciklama": "True ise yalniz vadesi gecmis faturalar"},
                },
            },
            {
                "ad": "kdv_ozeti",
                "aciklama": "Belirtilen ay icin KDV ozeti: hesaplanan KDV (satis), indirilecek "
                            "KDV (alis) ve odenecek net KDV. 'Bu ay KDV ne kadar, odenecek "
                            "vergi' sorularinda kullan.",
                "girdi_semasi": {
                    "yil": {"tip": "sayi", "zorunlu": False,
                            "aciklama": "Yil (varsayilan bu yil)"},
                    "ay": {"tip": "sayi", "zorunlu": False,
                           "aciklama": "Ay 1-12 (varsayilan bu ay)"},
                },
            },
        ],
        "belge_turleri": [],
    }


# ---------------------------------------------------------------------------
# Arac uygulamalari (SALT-OKUMA)
# ---------------------------------------------------------------------------
def _arac_acik_siparisler(girdi, obo):
    try:
        limit = int(girdi.get("limit") or 20)
    except (TypeError, ValueError):
        limit = 20
    limit = max(1, min(limit, 100))

    domain = [("state", "=", "sale")]
    musteri = (girdi.get("musteri") or "").strip()
    if musteri:
        domain.append(("partner_id.name", "ilike", musteri))

    Order = request.env["sale.order"].sudo()
    kayitlar = Order.search_read(
        domain,
        ["name", "partner_id", "date_order", "amount_total", "currency_id", "state"],
        limit=limit,
        order="date_order desc",
    )
    toplam = Order.search_count(domain)

    satirlar = []
    for r in kayitlar:
        satirlar.append({
            "siparis_no": r.get("name"),
            "musteri": (r["partner_id"][1] if r.get("partner_id") else ""),
            "tarih": (r["date_order"].strftime("%Y-%m-%d") if r.get("date_order") else ""),
            "tutar": r.get("amount_total") or 0.0,
            "para_birimi": (r["currency_id"][1] if r.get("currency_id") else ""),
            "durum": r.get("state"),
        })

    return {
        "ozet": "%d acik siparis (gosterilen %d)" % (toplam, len(satirlar)),
        "toplam": toplam,
        "siparisler": satirlar,
    }


def _arac_odenmemis_faturalar(girdi, obo):
    try:
        limit = int(girdi.get("limit") or 20)
    except (TypeError, ValueError):
        limit = 20
    limit = max(1, min(limit, 100))

    # Gonderilmis (posted) musteri faturalari, odenmemis/kismen odenmis
    domain = [
        ("move_type", "=", "out_invoice"),
        ("state", "=", "posted"),
        ("payment_state", "in", ["not_paid", "partial"]),
    ]
    musteri = (girdi.get("musteri") or "").strip()
    if musteri:
        domain.append(("partner_id.name", "ilike", musteri))
    if girdi.get("yalniz_vadesi_gecen"):
        from datetime import date
        domain.append(("invoice_date_due", "<", date.today().isoformat()))

    Move = request.env["account.move"].sudo()
    kayitlar = Move.search_read(
        domain,
        ["name", "partner_id", "invoice_date", "invoice_date_due",
         "amount_total", "amount_residual", "currency_id", "payment_state"],
        limit=limit,
        order="invoice_date_due asc",
    )
    toplam = Move.search_count(domain)
    toplam_bakiye = sum(r.get("amount_residual") or 0 for r in kayitlar)

    satirlar = []
    for r in kayitlar:
        satirlar.append({
            "fatura_no": r.get("name"),
            "musteri": (r["partner_id"][1] if r.get("partner_id") else ""),
            "fatura_tarihi": (r["invoice_date"].strftime("%Y-%m-%d") if r.get("invoice_date") else ""),
            "vade": (r["invoice_date_due"].strftime("%Y-%m-%d") if r.get("invoice_date_due") else ""),
            "tutar": r.get("amount_total") or 0.0,
            "odenecek_bakiye": r.get("amount_residual") or 0.0,
            "para_birimi": (r["currency_id"][1] if r.get("currency_id") else ""),
            "durum": r.get("payment_state"),
        })

    return {
        "ozet": "%d odenmemis fatura, toplam odenecek bakiye %.2f" % (toplam, toplam_bakiye),
        "toplam": toplam,
        "toplam_bakiye": round(toplam_bakiye, 2),
        "faturalar": satirlar,
    }


def _arac_kdv_ozeti(girdi, obo):
    from datetime import date
    bugun = date.today()
    try:
        yil = int(girdi.get("yil") or bugun.year)
    except (TypeError, ValueError):
        yil = bugun.year
    try:
        ay = int(girdi.get("ay") or bugun.month)
    except (TypeError, ValueError):
        ay = bugun.month
    ay = max(1, min(ay, 12))

    ay_basi = date(yil, ay, 1)
    ay_sonu = date(yil + (1 if ay == 12 else 0), 1 if ay == 12 else ay + 1, 1)

    Line = request.env["account.move.line"].sudo()
    # KDV satirlari = vergi satiri (tax_line_id dolu), gonderilmis faturalarda
    temel = [
        ("tax_line_id", "!=", False),
        ("parent_state", "=", "posted"),
        ("date", ">=", ay_basi.isoformat()),
        ("date", "<", ay_sonu.isoformat()),
    ]
    # Satis (hesaplanan KDV) = out_invoice/out_refund ; Alis (indirilecek) = in_invoice/in_refund
    satis = Line.search_read(
        temel + [("move_id.move_type", "in", ["out_invoice", "out_refund"])],
        ["balance"],
    )
    alis = Line.search_read(
        temel + [("move_id.move_type", "in", ["in_invoice", "in_refund"])],
        ["balance"],
    )
    # Satis KDV'si alacak (negatif balance) -> isareti cevir; alis KDV'si borc (pozitif)
    hesaplanan = round(-sum(l.get("balance") or 0 for l in satis), 2)
    indirilecek = round(sum(l.get("balance") or 0 for l in alis), 2)
    odenecek = round(hesaplanan - indirilecek, 2)

    return {
        "ozet": "%04d-%02d KDV: hesaplanan %.2f, indirilecek %.2f, odenecek net %.2f" % (
            yil, ay, hesaplanan, indirilecek, odenecek),
        "donem": "%04d-%02d" % (yil, ay),
        "hesaplanan_kdv": hesaplanan,
        "indirilecek_kdv": indirilecek,
        "odenecek_net_kdv": odenecek,
    }


_ARACLAR = {
    "acik_siparisler": _arac_acik_siparisler,
    "odenmemis_faturalar": _arac_odenmemis_faturalar,
    "kdv_ozeti": _arac_kdv_ozeti,
}


# ---------------------------------------------------------------------------
# HTTP uclari
# ---------------------------------------------------------------------------
class BuberkaAgentController(http.Controller):

    @http.route("/agent/v1/saglik", type="http", auth="none",
                methods=["GET"], csrf=False, save_session=False)
    def saglik(self, **kw):
        ok, hata = _dogrula()
        if not ok:
            return hata
        return _json({"ok": True, "durum": "ayakta", "kaynak": "odoo"})

    @http.route("/agent/v1/manifest", type="http", auth="none",
                methods=["GET"], csrf=False, save_session=False)
    def manifest(self, **kw):
        ok, hata = _dogrula()
        if not ok:
            return hata
        return _json(_manifest())

    @http.route("/agent/v1/tools/<string:ad>", type="http", auth="none",
                methods=["POST"], csrf=False, save_session=False)
    def tools(self, ad, **kw):
        ok, hata = _dogrula()
        if not ok:
            return hata

        fn = _ARACLAR.get(ad)
        if fn is None:
            return _json({"ok": False, "kod": "bilinmeyen_arac",
                         "hata": "Arac bulunamadi: %s" % ad}, status=404)

        try:
            body = request.httprequest.get_data(as_text=True) or "{}"
            istek = json.loads(body) if body.strip() else {}
        except ValueError:
            istek = {}
        girdi = (istek.get("girdi") or {}) if isinstance(istek, dict) else {}
        obo = _obo_coz()

        try:
            sonuc = fn(girdi, obo)
        except Exception as e:
            _logger.exception("Agent arac hatasi: %s", ad)
            return _json({"ok": False, "kod": "arac_hata",
                         "hata": "%s: %s" % (type(e).__name__, str(e))}, status=200)

        return _json({"ok": True, "sonuc": sonuc})

    # -----------------------------------------------------------------------
    # Odoo-ICI sohbet widget'i icin durum ucu (auth=user — oturum acik Odoo
    # kullanicisi). Giris yapmis kullanici icin kisa omurlu jeton uretir; JS bunu
    # BuberkaSmart iframe'ine postMessage ile verir. 'goster' kapaliysa JS hicbir
    # sey basmaz. Bu sayede her Odoo musterisinde addon kurulu + ayar acik olunca
    # widget otomatik calisir — ayri kod gerekmez.
    # -----------------------------------------------------------------------
    @http.route("/agent/v1/widget-durum", type="json", auth="user")
    def widget_durum(self, **kw):
        ICP = request.env["ir.config_parameter"].sudo()
        goster = str(ICP.get_param("buberka_agent.widget_goster", "True")).lower() not in ("false", "0", "")
        aktif = str(ICP.get_param("buberka_agent.aktif", "True")).lower() not in ("false", "0", "")
        tenant = ICP.get_param("buberka_agent.tenant", "")
        secret = ICP.get_param("buberka_agent.secret", "")
        merkez = ICP.get_param("buberka_agent.merkez_url", "https://buberkasmart.com").rstrip("/")
        if not (goster and aktif and tenant and secret):
            return {"goster": False}
        rol = _odoo_rol(request.env)
        kullanici = request.env.user.login or request.env.user.name or "odoo"
        jeton = _widget_jeton_uret(secret, tenant, kullanici, rol)
        return {
            "goster": True,
            "iframe_url": "%s/w/%s" % (merkez, tenant),
            "merkez_koken": merkez,
            "jeton": jeton,
            "sure_sn": 180,
        }
