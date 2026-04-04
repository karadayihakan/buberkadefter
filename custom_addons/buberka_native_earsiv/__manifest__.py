{
    'name': 'Buberka GIB e-Arsiv Entegrasyonu',
    'version': '18.0.2.0.0',
    'category': 'Accounting',
    'summary': 'GIB e-Arsiv portali ile fatura gonderimi ve portal indirme',
    'description': 'eArsivPortal ile GIB entegrasyonu, portal Proforma/Fatura indirme',
    'depends': ['account', 'portal'],
    'data': [
        'views/res_company_views.xml',
        'views/account_move_views.xml',
        'views/portal_templates.xml',
    ],
    'installable': True,
    'license': 'LGPL-3',
}
