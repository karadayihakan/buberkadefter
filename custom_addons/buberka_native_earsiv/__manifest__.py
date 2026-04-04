{
    'name': 'Buberka GIB e-Arsiv Entegrasyonu',
    'version': '18.0.1.0.0',
    'category': 'Accounting',
    'summary': 'GIB e-Arsiv portali ile fatura gonderimi',
    'description': 'fatura kutuphanesi ile GIB e-Arsiv entegrasyonu',
    'depends': ['account'],
    'data': [
        'views/res_company_views.xml',
        'views/account_move_views.xml',
    ],
    'installable': True,
    'license': 'LGPL-3',
}
