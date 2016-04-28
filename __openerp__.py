# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################


{
    'name': 'Florida Iron Doors',
    'version': '1.0',
    'category': 'CRM',
    'description': """
Create crm line documents.
===========================

    """,
    'author': 'Techsaga Infosystems Pvt Ltd',
    'depends': ['base','crm','purchase','sale','account',],
    'data': [
             'security/security_view.xml',
             'security/ir.model.access.csv',
             'views/report_invoice.xml',
             'views/account_invoice_report.xml',
             'views/sale_quot_template_view.xml',
             'report_view.xml',
             'techsaga_crm_view.xml',
             'views/report_quote.xml',       
             'wizard/wizard_view.xml',
             ],
    
    'installable': True,
    'auto_install': False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
