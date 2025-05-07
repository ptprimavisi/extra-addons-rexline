{
    'name': 'Custom General Affair',
    'category': 'account',
    'description': 'odoo custom GA',
    'depends': ['account', 'base', 'hr', 'purchase_custome'],
    'data': [
        "views/ga_request_view.xml",
        "views/ga_maintenance_view.xml",
        "views/travel_request_view.xml",
        "views/manpower_request_view.xml",
        "wizard/ga_maintenance_wizard.xml",
        "security/security.xml",
    ],

    'installable': True,
    'auto_install': False,
    'application': True,
}