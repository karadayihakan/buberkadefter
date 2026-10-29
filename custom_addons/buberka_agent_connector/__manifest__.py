# -*- coding: utf-8 -*-
{
    'name': 'BuberkaSmart Agent Connector',
    'version': '18.0.1.0.0',
    'category': 'Productivity',
    'summary': 'BuberkaSmart AI veri ajani icin salt-okuma, HMAC imzali sozlesme ucu',
    'description': """
BuberkaSmart Agent Connector
============================

Mevcut Odoo'nuzu DEGISTIRMEDEN, veriniz tesisten CIKMADAN calisan BuberkaSmart
ERP-ustu yapay zeka veri ajanini Odoo'ya baglar.

- Dogal dilde soru-cevap: "Bugun hangi siparisler acik?", "Odenmemis faturalar?"
- SALT-OKUMA: hicbir sey yazmaz/silmez (KVKK guvencesi)
- HMAC imzali, guvenli sozlesme uclari
- Kurulum: Uygulamayi yukleyin, Ayarlar > BuberkaSmart Agent'tan baglanti
  anahtarinizi yapistirin. SSH/teknik bilgi GEREKMEZ.

Uclar: /agent/v1/saglik, /agent/v1/manifest, /agent/v1/tools/<ad>
""",
    'author': 'Buberka Yazilim',
    'website': 'https://buberkasmart.com',
    'category': 'Productivity',
    'depends': ['base', 'base_setup', 'sale'],
    'data': [
        'views/res_config_settings_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'buberka_agent_connector/static/src/js/buberka_widget.js',
        ],
    },
    'images': ['static/description/banner.png'],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
