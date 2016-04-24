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
import time
from openerp.osv import osv
from openerp.report import report_sxw
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import time
from openerp import pooler
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, DATETIME_FORMATS_MAP, float_compare
import openerp.addons.decimal_precision as dp
from openerp import netsvc
from openerp import tools

class account_invoice_report(report_sxw.rml_parse):
    _name = 'report.techsaga_crm.account.invoice.report'
    
    def __init__(self,cr,uid,name,context):
        super(account_invoice_report, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
                                'time':time,
                                'get_door_desc':self.get_door_desc,
                                'get_total':self.get_total
                                  })
        
    def get_door_desc(self,so):
        res = self.pool.get('sale.order').search(self.cr,self.uid,[('name','=',so)])
        res_so = self.pool.get('sale.order').browse(self.cr,self.uid,res[0])
        return res_so
    
    def get_total(self,amount_total,residual):
        val= amount_total - residual
        #print "+++++",val
        return val

class report_invoice(osv.AbstractModel):
    _name = 'report.techsaga_crm.report_invoice'
    _inherit = 'report.abstract_report'
    _template = 'techsaga_crm.report_invoice'
    _wrapped_report_class = account_invoice_report