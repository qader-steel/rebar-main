{
    'name': 'Customer Statement Report',
    'version': '19.0.1.0.0',
    'category': 'Accounting',
    'summary': 'كشف حساب العميل مع تفاصيل المنتجات',
    'depends': ['account', 'sale'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/customer_statement_wizard_views.xml',
        'view/account_move_line_view.xml',
        'report/customer_statement_report.xml',
        'report/customer_statement_templates.xml',
    ],
    'assets': {
        'web.report_assets_common': [
            'your_module/static/src/css/statement_report.css',
        ],
    },
    'installable': True,
    'license': 'LGPL-3',
}