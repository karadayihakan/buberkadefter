{
    'name': 'KDV Dashboard',
    'version': '18.0.1.0.0',
    'category': 'Accounting',
    'summary': 'KDV ozet karti - Dashboard',
    'description': 'Kontrol paneline KDV ozet bilgisi ekler',
    'depends': ['account', 'spreadsheet_dashboard'],
    'data': [
        'views/kdv_dashboard_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'kdv_dashboard/static/src/js/kdv_dashboard.js',
            'kdv_dashboard/static/src/xml/kdv_dashboard.xml',
            'kdv_dashboard/static/src/css/kdv_dashboard.css',
        ],
    },
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
