{
    'name': 'Purchase Custom',
    'category': 'Accounting',
    'description': 'odoo Purchase Custom',
    'depends': ['account', 'purchase', 'sale', 'base','sale_custome', 'hr','stock','mail', 'multi_level_approval'],
    'data': [
        "views/purchase_views.xml",
        'views/requisition_views.xml',
        "wizard/count_quotation_views.xml",
        "views/payment_request_views.xml",
        # "views/stock_picking_views.xml",
        "wizard/purchase_order_wizard.xml",
        "report/report.xml",
        "report/report_payment_request.xml",
        "wizard/report_budget_project.xml",
    ],

    'installable': True,
    'auto_install': False,
    'application': True,
}