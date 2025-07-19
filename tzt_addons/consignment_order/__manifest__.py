{
    'name': 'Consignment Order',
    'version': '1.0',
    'depends': ['sale', 'stock', 'base'],
    'author': 'Thinzar Htun',
    'category': 'Sales',
    'description': 'Custom consignment order like sale order with picking type.',
    'data': [
        'security/ir.model.access.csv',
        'security/company_rule.xml',
        'views/consignment_order_views.xml',
        'views/res_config_settings_view.xml',
        'views/sale_order_view.xml',
        'report/report_consignment_order.xml',
        'report/report_consignment_order_template.xml',
        'report/consignment_report_template.xml',
        'views/consignment_report_menu.xml',
        'views/consignment_report_wizard_view.xml',
        'views/consignment_pivot_view.xml',

    ],
    'installable': True,
    'application': False,
}
