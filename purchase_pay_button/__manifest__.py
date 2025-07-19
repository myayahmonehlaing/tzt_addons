{
    'name': 'Purchase Pay Button',
    'version': '1.0',
    'author': 'Thinzar Htun',
    'depends': ['purchase', 'account'],
    'data': [
        "security/ir.model.access.csv",
        'views/purchase_order_view.xml',
        'views/purchase_order_wizard.xml',
    ],
    'installable': True,
    'application': False,
}
