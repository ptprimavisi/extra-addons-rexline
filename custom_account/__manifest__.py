{
    'name': 'Custome Account',
    'category': 'account',
    'description': 'odoo custome account',
    'depends': ['account', 'base', 'hr'],
    'data': [
        "views/permintaan_dana_views.xml",
        "views/realisai_dana_views.xml",
        "views/refund_views.xml",
    ],

    'installable': True,
    'auto_install': False,
    'application': True,
}