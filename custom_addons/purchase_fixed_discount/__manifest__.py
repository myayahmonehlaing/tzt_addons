{
    'name': 'Purchase Fixed Discount',
    'version': '1.0',
    'summary': 'Add fixed discount on purchase order and vendor bill',
    'depends': ['purchase', 'account'],
    'data': [
        'views/purchase_order_views.xml',
        'views/account_move_views.xml',
    ],
    'installable': True,
    'application': False,
}
