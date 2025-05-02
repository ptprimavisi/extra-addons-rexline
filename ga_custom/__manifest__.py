{
    'name': 'Custom General Affair',
    'category': 'account',
    'description': 'odoo custom account',
    'depends': ['account', 'base', 'hr', 'purchase_custome'],
    'data': [
        "views/ga_request_view.xml",
        "security/security.xml",
    ],

    'installable': True,
    'auto_install': False,
    'application': True,
}