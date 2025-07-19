{
    'name': 'Employee Birthday Wish',
    'version': '1.0',
    'summary': 'Create birthday wish activity for employees on their birthday',
    'category': 'Human Resources',
    'author': 'Thinzar Htun',
    'depends': ['hr', 'mail'],
    'data': [
        'views/birthday_activity_cron.xml',
    ],
    'installable': True,
    'application': False,
}
