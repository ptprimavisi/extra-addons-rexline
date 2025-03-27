{
    'name' : 'Custom Report',
    'description': """
        Custom Report
    """,
    'category': 'Custom',
    'depends': ['hr','sale_management','stock','account', 'base', 'hr','sale_custome','sale', 'purchase'],
    'data': [
        'views/report_invoice.xml',
        'report/report_invoice.xml',
        'views/sale_order.xml',
        'report/report_so.xml',
        'report/report_quotation.xml',
        'report/mrf_report.xml',
        'report/requisition_report.xml',
        'report/inquiry_report.xml',
        'report/purchase_order.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'custom_report/static/src/img/invoice_rexline.png',
            # 'custom_report/static/src/xml/request_price_asset.xml',
            # 'custom_report/static/src/js/request_price_notif.js',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
}
