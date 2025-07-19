{
    'name': 'Sale Agreements',
    'version': '1.0',
    'summary': 'Manage sale agreements for customers',
    'category': 'Sales',
    'author': 'Thinzar Htun',
    'depends': ['base','sale','uom'],
    'data': [
        'security/sale_agreement_security.xml',
        'views/sale_agreement_views.xml',
        'views/sale_agreement_sequence.xml',
        'views/sale_order_view.xml',
        'report/sale_agreement_report.xml',
        'report/sale_agreement_report_templates.xml',
    ],
    'installable': True,
    'application': True,
}
