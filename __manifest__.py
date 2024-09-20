{
    'name': 'Paiement Planteur',
    'version': '1.0',
    'sequence': '1',
    'summary': 'Summery',
    'description':"""
    Ce module facilite la gestion de la paie planteur dans Odoo
    - Lot de paie et calcule de faie de paie
    - Gestion des villages
    - Gestion de la paie par zone
    - Gestion des virements par zone
    - Rapport de suivi de paie
    - Generation automatique des ecritures comptables par periode paie
    - Configuration des journaux
    ====================================================
""",
    'category': 'Services/',
    'author': 'BEKOIN ETTIEN ETIENNE',
    'website': 'https://www.tds.ci',
    'depends': ['base','account','web'],
    'data': [
         'security/groups.xml',
        'security/ir.model.access.csv',
        'data/payroll_data.xml',
        'views/menu.xml',
        'wizard/import_bascule.xml',
        'wizard/plantation.xml',
        'views/config.xml',
        'views/partner.xml',
        'views/plantation.xml',
        'views/category.xml',
        'views/rule.xml',
        'views/payslip.xml',
        'views/virement.xml',
        'report/report_farmer.xml',
        'report/payment_report.xml',
        'report/reports.xml',
        'report/report_planting.xml',
        'report/report_payment.xml',
        'report/report_lot_de_paie.xml',
        'report/raport_detaille_prime.xml',
         'views/file_upload_view.xml',
    ],


    'installable': True,
    'application': True,
    'auto_install': False
}
