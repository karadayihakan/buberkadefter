# -*- coding: utf-8 -*-
"""BuberkaSmart Agent ayarlari — Odoo Ayarlar sayfasina gomulu form.

Musteri SSH'siz, Ayarlar > BuberkaSmart Agent'tan:
  - Baglanti anahtarini (secret) yapistirir (BuberkaSmart panelinden kopyalar)
  - Tenant adini girer
  - Durumu gorur

Secret ir.config_parameter'da saklanir (anahtar: buberka_agent.secret).
"""
from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    buberka_agent_secret = fields.Char(
        string="Baglanti Anahtari",
        help="BuberkaSmart panelinden kopyaladiginiz gizli anahtar. Yalniz imza "
             "dogrulamasinda kullanilir, disari gitmez.",
        config_parameter="buberka_agent.secret",
    )
    buberka_agent_tenant = fields.Char(
        string="Tenant Kodu",
        help="BuberkaSmart'taki tenant kodunuz (orn. buberka).",
        config_parameter="buberka_agent.tenant",
    )
    buberka_agent_aktif = fields.Boolean(
        string="Agent Baglantisi Aktif",
        config_parameter="buberka_agent.aktif",
        default=True,
    )
    buberka_agent_widget_goster = fields.Boolean(
        string="Odoo Icinde Sohbet Widget'ini Goster",
        help="Acikken Odoo ekranlarinda sag altta sohbet balonu cikar. "
             "Kapatirsaniz baglanti acik kalir ama Odoo ici widget gorunmez "
             "(orn. yalniz PWA/mobil uygulamadan kullaniyorsaniz).",
        config_parameter="buberka_agent.widget_goster",
        default=True,
    )

    @api.model
    def buberka_agent_durum(self):
        """Basit durum: secret tanimli mi?"""
        p = self.env["ir.config_parameter"].sudo().get_param("buberka_agent.secret")
        return bool(p)
