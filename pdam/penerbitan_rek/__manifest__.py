{
    'name': 'Penerbitan Rekening Custom',
    'category': 'Accounting',
    'description': 'Module custom penerbitan dan pendapatan rekening',
    'depends': ['account', 'sale'],
    'data': [
        "views/invoice_custom_views.xml",
        "wizard/sale_order_wizard.xml"
    ],

    'installable': True,
    'auto_install': False,
    'application': True,
}