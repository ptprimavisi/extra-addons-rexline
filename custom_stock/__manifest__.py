{
    'name': 'Custom Stock',
    'category': 'Custom',
    'description': 'odoo custom stock',
    'depends': ['stock','sale_custome'],
    'data': [
        'report/report_waybill.xml',
        'report/report_delivery.xml',
        'report/report_packinglist.xml',
        'views/inherit_packinglist.xml',
    ],

    'web.assets_backend': [
        'custom_stock/static/src/img/company_logo.png',
        'custom_stock/static/src/img/header_waybill.png',
        'custom_stock/static/src/img/footer_waybill.jpg',
    ],

    'installable': True,
    'auto_install': False,
    'application': True,
}