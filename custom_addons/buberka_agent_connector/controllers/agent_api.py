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
import hashlib
import hmac
import json
import logging
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


_ARACLAR = {
    "acik_siparisler": _arac_acik_siparisler,
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
