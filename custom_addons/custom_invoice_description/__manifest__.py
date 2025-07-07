{
    'name': 'Custom Invoice Description Format',
    'version': '1.0',
    'category': 'Accounting',
    'summary': 'Hide internal reference and display multi-line, italic product descriptions in invoice report',
    'description': """
        This module customizes the invoice report:
        - Hides product internal reference.
        - Displays product descriptions line by line in italic.
    """,
    'depends': ['account'],
    'data': [
        'views/account_move_report_template.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
