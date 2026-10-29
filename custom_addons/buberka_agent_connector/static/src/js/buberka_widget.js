/* BuberkaSmart Agent — Odoo-ici sohbet widget'i.
 * web.assets_backend'e eklenir: her Odoo musterisinde addon kuruluysa otomatik yuklenir.
 * Akis: /agent/v1/widget-durum'u cagir -> goster ise BuberkaSmart iframe'ini sag-alta bas.
 * iframe jeton ister (postMessage {tip:'jeton-iste'}) -> bu JS taze jeton verir.
 * Kontrol BuberkaSmart tenant ayarinda + Odoo Ayarlar > widget_goster.
 */
(function () {
    "use strict";
    if (window.__buberkaWidgetYuklendi) return;
    window.__buberkaWidgetYuklendi = true;

    function istek(url, veri) {
        return fetch(url, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ jsonrpc: "2.0", method: "call", params: veri || {} }),
        }).then(function (r) { return r.json(); }).then(function (d) { return d.result || {}; });
    }

    function tazeJeton() {
        return istek("/agent/v1/widget-durum").then(function (d) { return d || {}; });
    }

    function kur(durum) {
        if (!durum || !durum.goster || !durum.iframe_url) return;
        var koken = durum.merkez_koken;

        var iframe = document.createElement("iframe");
        iframe.src = durum.iframe_url;
        iframe.title = "BuberkaSmart AI";
        iframe.setAttribute("allow", "clipboard-write");
        iframe.style.cssText =
            "position:fixed;bottom:0;right:0;width:120px;height:120px;border:0;z-index:2147483000;" +
            "background:transparent;color-scheme:normal;transition:width .2s,height .2s;";
        document.body.appendChild(iframe);

        // iframe <-> Odoo kopru: jeton-iste gelince taze jeton gonder, boyut gelince iframe boyutla
        window.addEventListener("message", function (ev) {
            if (ev.origin !== koken || ev.source !== iframe.contentWindow) return;
            var m = ev.data || {};
            if (m.tip === "hazir" || m.tip === "jeton-iste") {
                tazeJeton().then(function (d) {
                    if (d && d.jeton) {
                        iframe.contentWindow.postMessage(
                            { tip: "jeton", jeton: d.jeton, sure_sn: d.sure_sn || 180 }, koken);
                    }
                });
            } else if (m.tip === "boyut") {
                iframe.style.width = (m.genislik || 120) + "px";
                iframe.style.height = (m.yukseklik || 120) + "px";
            }
        });
    }

    function basla() {
        tazeJeton().then(kur).catch(function () { /* sessiz: widget kapali/erisimsizse hic basma */ });
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", basla);
    } else {
        basla();
    }
})();
