{
    'name': 'Custome Tst',
    'category': 'account',
    'description': 'odoo custome Test',
    'depends': ['account', 'base', 'hr'],
    'data': [
        "views/formulir_views.xml",
    ],

    'installable': True,
    'auto_install': False,
    'application': True,
}