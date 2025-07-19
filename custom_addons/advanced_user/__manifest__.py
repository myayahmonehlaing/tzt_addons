{
    'name': 'Advanced Accounting User',
    'version': '1.0',
    'summary': 'Restrict advanced users to vendor bills only',
    'author': 'Thinzar Htun',
    'depends': ['base', 'account','accountant'],
    'data': [
        'security/advanced_user_security.xml',
        'security/ir.model.access.csv',
        'views/account_move_views.xml',
    ],
    'installable': True,
    'application': False,
}
