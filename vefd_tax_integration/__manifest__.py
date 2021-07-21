# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'VEFD Tax Integration',
    'version': '14.0',
    'sequence': 230,
    'category': 'VEFD Tax Integration',
    'summary': 'VEFD Tax Integration',
    'author': "PPTS(India) Pvt Ltd",
    'website': "https://www.pptssolutions.com",
    'description': """
    VEFD Tax Integration
""",
    'depends': ['sale_management','account','point_of_sale','product','base'],
    'data': [
        'security/ir.model.access.csv',
        'views/account_tax_views.xml',
        'views/account_invoice_view.xml',
        'views/vefd_credentials.xml',
        'views/report_invoice.xml',
        'views/cron_data.xml',
        'views/pos_assets.xml',
        'views/pos_views.xml',
        'views/product.xml',
    ],
    'qweb': ['static/src/xml/pos.xml'],
    'installable': True,
    'auto_install': False,
    'application': True,
}
