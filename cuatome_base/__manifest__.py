{
    'name': 'Custome Base',
    'category': 'Base',
    'description': 'odoo custome base module',
    'depends': ['base','multi_level_approval'],
    'data': [
        "views/res_user_views.xml",
    ],

    'installable': True,
    'auto_install': False,
    'application': True,
}