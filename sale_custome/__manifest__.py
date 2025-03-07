{
    'name': 'Sales Custom',
    'category': 'Accounting',
    'description': 'odoo Sale Custom',
    'depends': ['base','account', 'sale', 'crm', 'mrp','web','mail', 'bi_crm_product_quotation', 'hr', 'stock', 'product'],
    'data': [
        "views/inquiry_views.xml",
        "security/security.xml",
        "security/ir.model.access.csv",
        "wizard/rfq_wizard.xml",
        "wizard/production_views.xml",
        "wizard/schedule_wizard_views.xml",
        "wizard/price_request_wizard.xml",
        "wizard/daily_report_production.xml",
        "wizard/maintenance_views.xml",
        "wizard/report_ar_views.xml",
        "report/daily_report_production.xml",
        "report/report_price_request.xml",
        'report/report.xml',
        'wizard/report_manpower.xml',
        # "views/rfq_views.xml",
        "views/crm_views.xml",
        "views/bom_views.xml",
        "views/stock_report_views.xml",
        "views/packing_list_views.xml",
        "views/cost_estimation_views.xml",
        "views/product_views.xml",
        "views/request_price_views.xml",
        "views/production_report_views.xml",
        "views/surat_kerja_views.xml",
        "views/inquiry_log_views.xml",
        "views/hr_employee_views.xml",
        "views/sale_order_views.xml",
        "views/maintenance_report_views.xml",
        "views/hr_surat_tugas_views.xml",
        'views/manajemen_assets.xml'
    ],
    'assets': {
        'web.assets_backend': [
            "sale_custome/static/src/js/notif.js",
            # "sale_custome/static/src/js/custom_css.js",
            # "/sale_custome/static/src/js/button.js",
            "sale_custome/static/src/xml/notif_views.xml",
            # "/sale_custome/static/src/xml/button_view.xml"
        ],
    },
    # 'web.assets_backend': [
    #     # "static/src/js/notif.js",
    #     # "static/src/xml/notif_views.xml"
    # ],


    'installable': True,
    'auto_install': False,
    'application': True,
}