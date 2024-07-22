{
    'name': 'Surat Berharga',
    'category': 'Accounting',
    'description': 'Module custom Kasbon / Surat berharga',
    'depends': ['account', 'sale', 'base'],
    'data': [
        "views/surat_berharga_views.xml",
        "security/security.xml",
        "wizard/payment_views.xml"
    ],

    'installable': True,
    'auto_install': False,
    'application': True,
}